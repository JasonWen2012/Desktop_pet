# -*- coding: utf-8 -*-
"""
Windows 下把 pygame 无边框窗口做成真正的“每像素透明 + 置顶”窗口。

原理：给窗口加 WS_EX_LAYERED，然后用 UpdateLayeredWindow 把一张
32 位(预乘 Alpha BGRA)位图直接合成到桌面。这样猫的边缘能干净地
半透明显示，而不是色键抠图。

依赖：仅标准库 ctypes（Windows）。非 Windows 平台自动降级为普通
无边框窗口（present 返回 False，由 main 自行处理）。
"""
import ctypes
import sys

IS_WINDOWS = (sys.platform == "win32")

if IS_WINDOWS:
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

    # 常量
    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    WS_EX_TOOLWINDOW = 0x00000080
    HWND_TOPMOST = -1
    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_NOACTIVATE = 0x0010
    ULW_ALPHA = 0x00000002
    AC_SRC_OVER = 0x00
    AC_SRC_ALPHA = 0x01
    DIB_RGB_COLORS = 0
    BI_RGB = 0

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                    ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

    class SIZE(ctypes.Structure):
        _fields_ = [("cx", ctypes.c_long), ("cy", ctypes.c_long)]

    class BLENDFUNCTION(ctypes.Structure):
        _fields_ = [("BlendOp", ctypes.c_ubyte),
                    ("BlendFlags", ctypes.c_ubyte),
                    ("SourceConstantAlpha", ctypes.c_ubyte),
                    ("AlphaFormat", ctypes.c_ubyte)]

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", ctypes.c_uint32),
                    ("biWidth", ctypes.c_int32),
                    ("biHeight", ctypes.c_int32),
                    ("biPlanes", ctypes.c_uint16),
                    ("biBitCount", ctypes.c_uint16),
                    ("biCompression", ctypes.c_uint32),
                    ("biSizeImage", ctypes.c_uint32),
                    ("biXPelsPerMeter", ctypes.c_int32),
                    ("biYPelsPerMeter", ctypes.c_int32),
                    ("biClrUsed", ctypes.c_uint32),
                    ("biClrImportant", ctypes.c_uint32)]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [("bmiHeader", BITMAPINFOHEADER),
                    ("bmiColors", ctypes.c_uint32 * 3)]

    _HWND = wintypes.HWND
    _HDC = wintypes.HDC

    user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.GetWindowLongPtrW.argtypes = [_HWND, ctypes.c_int]
    user32.SetWindowLongPtrW.argtypes = [_HWND, ctypes.c_int, ctypes.c_ssize_t]
    user32.GetDC.restype = _HDC
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.ReleaseDC.argtypes = [wintypes.HWND, _HDC]
    user32.GetWindowRect.argtypes = [_HWND, ctypes.POINTER(RECT)]
    user32.MoveWindow.argtypes = [_HWND, ctypes.c_int, ctypes.c_int,
                                  ctypes.c_int, ctypes.c_int, ctypes.c_int]
    user32.SetWindowPos.argtypes = [_HWND, _HWND, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
    user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    user32.UpdateLayeredWindow.argtypes = [
        _HWND, _HDC, ctypes.POINTER(POINT), ctypes.POINTER(SIZE), _HDC,
        ctypes.POINTER(POINT), wintypes.COLORREF, ctypes.POINTER(BLENDFUNCTION),
        wintypes.DWORD]
    gdi32.CreateCompatibleDC.restype = _HDC
    gdi32.CreateCompatibleDC.argtypes = [_HDC]
    gdi32.CreateDIBSection.restype = wintypes.HBITMAP
    gdi32.CreateDIBSection.argtypes = [_HDC, ctypes.POINTER(BITMAPINFO),
                                       ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p),
                                       wintypes.HANDLE, wintypes.DWORD]
    gdi32.SelectObject.restype = wintypes.HGDIOBJ
    gdi32.SelectObject.argtypes = [_HDC, wintypes.HGDIOBJ]
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteDC.argtypes = [_HDC]


def virtual_screen():
    if not IS_WINDOWS:
        return (0, 0, 1920, 1080)
    x = user32.GetSystemMetrics(76)   # SM_XVIRTUALSCREEN
    y = user32.GetSystemMetrics(77)   # SM_YVIRTUALSCREEN
    w = user32.GetSystemMetrics(78)   # SM_CXVIRTUALSCREEN
    h = user32.GetSystemMetrics(79)   # SM_CYVIRTUALSCREEN
    return (x, y, w, h)


def cursor_pos():
    if not IS_WINDOWS:
        return None
    p = POINT()
    if user32.GetCursorPos(ctypes.byref(p)):
        return (p.x, p.y)
    return None


class LayeredWin:
    """封装一个 pygame 窗口的透明化、置顶、移动等操作。"""

    def __init__(self):
        self.ok = IS_WINDOWS
        self.hwnd = None
        self._hdc_mem = None
        self._hbmp = None
        self._bits = None
        self.w = 0
        self.h = 0
        self.last_error = ""

    # ------------------------------------------------------------ 生命周期
    def attach(self, hwnd):
        """绑定 pygame 的窗口句柄并应用 WS_EX_LAYERED + 置顶。"""
        if not IS_WINDOWS or not hwnd:
            self.ok = False
            return False
        self.hwnd = hwnd
        style = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TOOLWINDOW)
        # 置顶
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        self.ok = True
        return True

    def set_size(self, w, h):
        """窗口/位图尺寸变化后重建内存 DC 与 DIB。"""
        if not self.ok:
            return
        self._cleanup_dib()
        self.w, self.h = int(w), int(h)
        screen_dc = user32.GetDC(0)
        try:
            self._hdc_mem = gdi32.CreateCompatibleDC(screen_dc)
            if not self._hdc_mem:
                self.ok = False
                return
            bmi = BITMAPINFO()
            bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.bmiHeader.biWidth = self.w
            bmi.bmiHeader.biHeight = -self.h   # 负数 = 自上而下，与 pygame 行序一致
            bmi.bmiHeader.biPlanes = 1
            bmi.bmiHeader.biBitCount = 32
            bmi.bmiHeader.biCompression = BI_RGB
            bits = ctypes.c_void_p()
            self._hbmp = gdi32.CreateDIBSection(
                self._hdc_mem, ctypes.byref(bmi), DIB_RGB_COLORS,
                ctypes.byref(bits), None, 0)
            if not self._hbmp or not bits.value:
                self.ok = False
                return
            gdi32.SelectObject(self._hdc_mem, self._hbmp)
            self._bits = ctypes.cast(bits, ctypes.POINTER(ctypes.c_ubyte))
        finally:
            user32.ReleaseDC(0, screen_dc)

    def _cleanup_dib(self):
        if self._hbmp:
            gdi32.DeleteObject(self._hbmp)
        if self._hdc_mem:
            gdi32.DeleteDC(self._hdc_mem)
        self._hbmp = None
        self._hdc_mem = None
        self._bits = None

    def detach(self):
        self._cleanup_dib()
        self.ok = False

    # ------------------------------------------------------------ 每帧呈现
    def present(self, rgba_surface) -> bool:
        """把一张 RGBA 的 pygame surface 合成为窗口内容。"""
        if not self.ok or self.hwnd is None:
            return False
        w, h = rgba_surface.get_size()
        if (w, h) != (self.w, self.h):
            self.set_size(w, h)
        if not self.ok:
            return False

        import pygame
        from PIL import Image, ImageChops
        raw = pygame.image.tostring(rgba_surface, "RGBA")
        img = Image.frombytes("RGBA", (w, h), raw)
        r, g, b, a = img.split()
        # 预乘 Alpha；把通道顺序摆成 B,G,R,A 供 DIB 使用
        pr = ImageChops.multiply(r, a)
        pg = ImageChops.multiply(g, a)
        pb = ImageChops.multiply(b, a)
        buf = Image.merge("RGBA", (pb, pg, pr, a)).tobytes()

        n = len(buf)
        if self._bits:
            ctypes.memmove(self._bits, buf, n)

        blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)
        psize = SIZE(w, h)
        pzero = POINT(0, 0)
        hdc_screen = user32.GetDC(0)
        try:
            res = user32.UpdateLayeredWindow(
                self.hwnd, hdc_screen, None, ctypes.byref(psize),
                self._hdc_mem, ctypes.byref(pzero), 0,
                ctypes.byref(blend), ULW_ALPHA)
        finally:
            user32.ReleaseDC(0, hdc_screen)
        if not res:
            self.last_error = ctypes.get_last_error()
        return bool(res)

    # ------------------------------------------------------------ 位置操作
    def rect(self):
        if not self.ok or not self.hwnd:
            return (0, 0, self.w, self.h)
        rc = RECT()
        if user32.GetWindowRect(self.hwnd, ctypes.byref(rc)):
            return (rc.left, rc.top, rc.right - rc.left, rc.bottom - rc.top)
        return (0, 0, self.w, self.h)

    def move(self, x, y):
        if not self.ok or not self.hwnd:
            return
        user32.MoveWindow(self.hwnd, int(x), int(y), self.w, self.h, True)

    def place_in_screen(self, x, y, w, h):
        """把窗口挪进虚拟屏幕内（拖动 / 启动时防丢窗口）。"""
        vx, vy, vw, vh = virtual_screen()
        if x < vx - w + 40:
            x = vx
        if y < vy:
            y = vy
        if x + w > vx + vw - 8:
            x = vx + vw - w - 8
        if y + h > vy + vh - 8:
            y = vy + vh - h - 8
        self.move(x, y)
        return (x, y)
