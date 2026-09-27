# -*- coding: utf-8 -*-
"""
小猫本体绘制 + 动画状态（呼吸/眨眼/哈欠/敲击）。

几何都在“设计坐标系”里定义：DW x DH = 300 x 352。
cat.py 提供 draw_cat 画到调用方给的画布上（内部把坐标 *SS 放大）。
整个猫画布随后会被 main 纵向轻微缩放(呼吸)后贴到主画布。
"""
import math
import os
import random

import pygame

# ------------------------------------------------------------------ 常量
DW = 300                 # 设计宽
DH = 404                 # 设计高（底部留出区域给敲击计数器）
SS = 2                   # 超采样倍数
MW = DW * SS
MH = DH * SS

TAP_DIST = 9.0           # 敲击位移（设计单位）
YAWN_DUR = 3.4

# 配色
COL_BODY = (255, 255, 255)
COL_HEAD = (255, 255, 255)
COL_PAW = (255, 255, 255)
COL_EAR = (255, 250, 246)
COL_EAR_IN = (250, 176, 194)
COL_EYE = (46, 44, 60)
COL_PUPIL = (14, 12, 20)
COL_NOSE = (244, 130, 158)
COL_MOUTH = (62, 56, 74)
COL_WHISK = (92, 88, 100)

# 几何（设计单位）
BODY_RECT = (54, 88, 192, 216)          # 身体椭圆 (cx150,cy196,rx96,ry108)
HEAD_RECT = (80, 44, 140, 132)          # 头椭圆   (cx150,cy110,rx70,ry66)
EAR_L = [(100, 58), (70, 6), (138, 40)]
EAR_R = [(200, 58), (230, 6), (162, 40)]
EAR_IN_L = [(106, 46), (84, 18), (128, 40)]
EAR_IN_R = [(194, 46), (216, 18), (172, 40)]
EYE_L = (116, 96)
EYE_R = (184, 96)
EYE_RADIUS = 19
NOSE_POS = (150, 137)
NOSE_R = 7
MOUTH_Y = 152
FACE_PATCH = (95, 63, 110, 102)         # 照片贴脸区域 (cx150,cy114,rx55,ry51)
PAW_L_CX = 104
PAW_R_CX = 196
PAW_CY = 310
PAW_W = 72
PAW_H = 54


def _s(v):
    return int(round(v * SS))


def Rt(rect):
    x, y, w, h = rect
    return (_s(x), _s(y), _s(w), _s(h))


def Pt(pts):
    return [(_s(x), _s(y)) for x, y in pts]


def _ellipse(surface, rect, color):
    pygame.draw.ellipse(surface, color, Rt(rect))


def _poly(surface, pts, color):
    pygame.draw.polygon(surface, color, Pt(pts))


# ================================================================== 动画
class CatAnim:
    """集中管理呼吸/眨眼/哈欠/敲爪等动画状态。"""

    def __init__(self, idle_seconds=20.0):
        self.idle_seconds = max(5.0, idle_seconds)
        self.t = 0.0
        self.paw_l = 0.0        # 0..1 已缓动
        self.paw_r = 0.0
        self.left = False       # 左半区按键中
        self.right = False      # 右半区按键中
        self.mouse = False      # 鼠标按键中
        self.idle = 0.0
        self.blink = 0.0
        self._next_blink = random.uniform(2.2, 5.0)
        self.yawn_t = -1.0
        self.mouth = 0.0        # 嘴张开程度 0..1（哈欠动画用）
        self.breath = 1.0

    # ------------------------------------------------------------ 输入
    def poke(self):
        """任何用户操作都会重置空闲计时并打断哈欠。"""
        self.idle = 0.0
        if self.yawn_t >= 0:
            self.yawn_t = -1.0

    # ------------------------------------------------------------ 主更新
    def update(self, dt):
        dt = min(dt, 0.05)
        self.t += dt

        # 敲爪缓动
        k = 1.0 - math.exp(-dt * 16.0)
        tl = 1.0 if (self.left or self.mouse) else 0.0
        tr = 1.0 if (self.right or self.mouse) else 0.0
        self.paw_l += (tl - self.paw_l) * k
        self.paw_r += (tr - self.paw_r) * k

        # 空闲计时
        if self.left or self.right or self.mouse:
            self.idle = 0.0
        else:
            self.idle += dt

        # 眨眼（哈欠时不额外眨）
        if self.blink > 0:
            self.blink -= dt
            if self.blink <= 0:
                self.blink = 0.0
                self._next_blink = random.uniform(2.4, 6.0)
        elif self.yawn_t < 0:
            self._next_blink -= dt
            if self._next_blink <= 0:
                self.blink = 0.14
                self._next_blink = random.uniform(2.4, 6.0)

        # 哈欠状态机
        if self.yawn_t >= 0:
            self.yawn_t += dt
            if self.yawn_t >= YAWN_DUR:
                self.yawn_t = -1.0
        elif (self.idle >= self.idle_seconds and self.blink <= 0
              and not (self.left or self.right or self.mouse)):
            self.yawn_t = 0.0

        # 嘴：向目标缓动；哈欠被打断时快速合拢
        target = 0.0
        if self.yawn_t >= 0:
            tt = self.yawn_t
            if tt < 0.9:
                target = tt / 0.9
            elif tt < YAWN_DUR - 0.7:
                target = 1.0
            else:
                target = max(0.0, 1.0 - (tt - (YAWN_DUR - 0.7)) / 0.7)
        k2 = 1.0 - math.exp(-dt * (9.0 if self.yawn_t >= 0 else 14.0))
        self.mouth += (target - self.mouth) * k2

        # 呼吸起伏
        self.breath = 1.0 + 0.012 * math.sin(2.0 * math.pi * self.t / 3.4)

    @property
    def eyes_closed(self):
        return self.blink > 0.0 or self.mouth > 0.12


# ================================================================== 脸
def load_face_surface(path, size=None):
    """用 Pillow 读入照片并裁成猫脸贴片（椭圆蒙版），返回 pygame Surface。"""
    if not path or not os.path.exists(path):
        return None
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None
    w, h = (FACE_PATCH[2] * SS, FACE_PATCH[3] * SS) if size is None else size
    img = Image.open(path).convert("RGB")
    # 中心裁切 + 缩放铺满贴片区
    target_ar = w / h
    sw, sh = img.size
    ar = sw / sh
    if ar > target_ar:
        nw = int(sh * target_ar)
        x0 = (sw - nw) // 2
        img = img.crop((x0, 0, x0 + nw, sh))
    else:
        nh = int(sw / target_ar)
        y0 = (sh - nh) // 2
        img = img.crop((0, y0, sw, y0 + nh))
    img = img.resize((w, h), Image.LANCZOS)
    # 4x 抗锯齿椭圆蒙版
    mask = Image.new("L", (w * 4, h * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, w * 4 - 1, h * 4 - 1), fill=255)
    mask = mask.resize((w, h), Image.LANCZOS)
    img.putalpha(mask)
    return pygame.image.fromstring(img.tobytes(), (w, h), "RGBA")


# ================================================================== 贴纸素材（装饰）
def _draw_bow(surf, cx=99, cy=42, k=1.0):
    """蝴蝶结（戴在左耳）"""
    color = (216, 66, 88)
    dark = (168, 42, 66)
    _poly(surf, [(cx - 14 * k, cy + 4 * k), (cx - 34 * k, cy - 12 * k),
                 (cx - 10 * k, cy - 14 * k)], color)
    _poly(surf, [(cx - 16 * k, cy + 4 * k), (cx - 36 * k, cy + 22 * k),
                 (cx - 12 * k, cy + 16 * k)], color)
    _poly(surf, [(cx + 14 * k, cy + 4 * k), (cx + 34 * k, cy - 12 * k),
                 (cx + 10 * k, cy - 14 * k)], color)
    _poly(surf, [(cx + 16 * k, cy + 4 * k), (cx + 36 * k, cy + 22 * k),
                 (cx + 12 * k, cy + 16 * k)], color)
    pygame.draw.circle(surf, dark, (_s(cx), _s(cy)), _s(7 * k))
    pygame.draw.circle(surf, (240, 160, 170), (_s(cx - 2 * k), _s(cy - 2 * k)), _s(2.5 * k))


def _draw_crown(surf):
    pts = [(118, 72), (118, 58), (128, 24), (138, 52), (150, 16),
           (162, 52), (172, 24), (182, 58), (182, 72)]
    _poly(surf, pts, (255, 201, 76))
    _poly(surf, [(118, 58), (128, 24), (138, 52), (150, 16),
                 (162, 52), (172, 24), (182, 58)], (230, 160, 40))
    pygame.draw.rect(surf, (255, 222, 130), Rt((119, 60, 62, 12)), border_radius=_s(4))
    for jx, jy, c in [(128, 72, (255, 92, 96)), (150, 70, (120, 180, 255)),
                      (172, 72, (255, 92, 96))]:
        pygame.draw.circle(surf, c, (_s(jx), _s(jy)), _s(4))
        pygame.draw.circle(surf, (255, 255, 255), (_s(jx - 1), _s(jy - 1)), _s(1.5))


def _draw_headphones(surf):
    band_col = (232, 120, 160)
    cup_col = (244, 140, 176)
    cup_dark = (168, 74, 116)
    arc_rect = Rt((92, 6, 116, 84))
    # 顶带（上半圆）
    pygame.draw.arc(surf, band_col, arc_rect, 0.0, math.pi, _s(11))
    pygame.draw.arc(surf, (255, 205, 222), Rt((96, 12, 108, 72)),
                    0.0, math.pi, _s(3))
    # 耳罩
    for x0 in (76, 194):
        r = Rt((x0, 58, 34, 46))
        pygame.draw.rect(surf, cup_dark, r, border_radius=_s(16))
        r2 = Rt((x0 + 4, 62, 26, 38))
        pygame.draw.rect(surf, cup_col, r2, border_radius=_s(13))
        pygame.draw.ellipse(surf, (255, 205, 222), Rt((x0 + 8, 68, 18, 10)))


def _draw_glasses(surf):
    rim = (56, 52, 74)
    for cx in (EYE_L[0], EYE_R[0]):
        pygame.draw.circle(surf, rim, (_s(cx), _s(EYE_L[1])), _s(26), _s(4))
    # 镜片微光
    for cx in (EYE_L[0], EYE_R[0]):
        pygame.draw.ellipse(surf, (150, 200, 255, 40), Rt((cx - 24, EYE_L[1] - 24, 48, 48)))
    # 鼻梁 + 镜腿
    pygame.draw.line(surf, rim, (_s(140), _s(96)), (_s(160), _s(96)), _s(4))
    pygame.draw.line(surf, rim, (_s(90), _s(88)), (_s(66), _s(80)), _s(4))
    pygame.draw.line(surf, rim, (_s(210), _s(88)), (_s(234), _s(80)), _s(4))


def _draw_sunglasses(surf):
    fill = (38, 36, 52)
    for x0 in (86, 154):
        pygame.draw.rect(surf, fill, Rt((x0, 72, 60, 48)), border_radius=_s(18))
    pygame.draw.rect(surf, fill, Rt((132, 84, 36, 14)), border_radius=_s(6))
    # 高光
    for x0 in (96, 164):
        _poly(surf, [(x0 + 2, 84), (x0 + 22, 80), (x0 + 26, 88), (x0 + 8, 92)], (200, 210, 240, 110))


def _draw_scarf(surf):
    red = (224, 76, 88)
    dark = (168, 52, 66)
    # 颈圈
    pygame.draw.rect(surf, red, Rt((96, 168, 108, 24)), border_radius=_s(12))
    for i in range(4):
        x = 104 + i * 24
        pygame.draw.line(surf, dark, (_s(x), _s(172)), (_s(x), _s(188)), _s(3))
    # 垂尾
    pygame.draw.rect(surf, red, Rt((124, 188, 26, 78)), border_radius=_s(10))
    pygame.draw.line(surf, dark, (_s(137), _s(200)), (_s(137), _s(262)), _s(3))
    pygame.draw.line(surf, (150, 40, 56), (_s(128), _s(262)), (_s(133), _s(262)), _s(3))
    pygame.draw.line(surf, (150, 40, 56), (_s(137), _s(262)), (_s(142), _s(262)), _s(3))
    pygame.draw.line(surf, (150, 40, 56), (_s(146), _s(262)), (_s(151), _s(262)), _s(3))


def _draw_bowtie(surf):
    a = (150, 202)
    _poly(surf, [a, (108, 186), (108, 218)], (206, 54, 84))
    _poly(surf, [a, (192, 186), (192, 218)], (206, 54, 84))
    _poly(surf, [a, (108, 186), (150, 196)], (240, 110, 140))
    _poly(surf, [a, (192, 186), (150, 196)], (240, 110, 140))
    pygame.draw.circle(surf, (150, 34, 60), (_s(150), _s(202)), _s(9))
    pygame.draw.circle(surf, (255, 210, 220), (_s(147), _s(199)), _s(3))


def _draw_cape(surf):
    pts = [(110, 150), (190, 150), (286, 288), (272, 302), (262, 296),
           (236, 320), (190, 330), (150, 336), (110, 330), (64, 320),
           (38, 296), (28, 302), (14, 288)]
    _poly(surf, pts, (150, 66, 110))
    # 内衬折光
    _poly(surf, [(112, 154), (188, 154), (270, 280), (30, 280)],
          (172, 88, 132, 255))
    # 领口金边
    pygame.draw.arc(surf, (255, 206, 96), Rt((92, 118, 116, 90)),
                    math.pi * 0.18, math.pi * 0.82, _s(5))


# ================================================================== 主绘制
def draw_cat(surface, cfg, anim, look=(0.0, 0.0)):
    """
    把整只猫（含服装/头饰/眼镜）画到 surface（应已清透明）。
    look: 眼球注视方向(设计单位偏移量)
    """
    decos = set(cfg.get("decorations", []) or [])

    def D(id_):
        return id_ in decos

    # ------------------------------------------------------------ 披风(最底)
    if D("cape"):
        _draw_cape(surface)

    # 身体
    _ellipse(surface, BODY_RECT, COL_BODY)

    # 耳朵（在头后面，先画）
    _poly(surface, EAR_L, COL_EAR)
    _poly(surface, EAR_R, COL_EAR)
    _poly(surface, EAR_IN_L, COL_EAR_IN)
    _poly(surface, EAR_IN_R, COL_EAR_IN)

    # 头
    _ellipse(surface, HEAD_RECT, COL_HEAD)

    # 围巾(在头/身体之间)
    if D("scarf"):
        _draw_scarf(surface)

    # ------------------------------------------------------------ 脸
    face_surf = cfg.get("_face_surf")
    if face_surf is not None:
        # 照片脸贴片（椭圆蒙版）
        surface.blit(face_surf, (_s(FACE_PATCH[0]), _s(FACE_PATCH[1])))
        # 头顶露出一点猫色边缘
    else:
        _draw_default_face(surface, anim, look)

    # 领结(胸前)
    if D("bowtie"):
        _draw_bowtie(surface)

    # ------------------------------------------------------------ 眼镜
    if D("glasses"):
        _draw_glasses(surface)
    if D("sunglasses"):
        _draw_sunglasses(surface)

    # ------------------------------------------------------------ 头饰
    if D("bow"):
        _draw_bow(surface)
    if D("crown"):
        _draw_crown(surface)
    if D("headphones"):
        _draw_headphones(surface)

    # ------------------------------------------------------------ 纹身(身体部位)
    tattoos = cfg.get("tattoos") or {}
    if tattoos:
        from tattoos import draw_body_tattoos
        draw_body_tattoos(surface, tattoos, anim)

    # ------------------------------------------------------------ 爪子(最前)
    _draw_paws(surface, anim)

    # 爪部纹身跟随爪子动画
    if tattoos:
        from tattoos import draw_paw_tattoos
        draw_paw_tattoos(surface, tattoos, anim)


def _draw_paws(surface, anim):
    for cx in (PAW_L_CX, PAW_R_CX):
        e = anim.paw_l if cx == PAW_L_CX else anim.paw_r
        cy = PAW_CY + TAP_DIST * e
        w = PAW_W + 10 * e
        h = PAW_H - 12 * e
        rect = (cx - w / 2, cy - h / 2, w, h)
        pygame.draw.ellipse(surface, (235, 232, 230), Rt(rect))
        inner = (cx - w / 2 + 4, cy - h / 2 + 4, w - 8, h - 10)
        pygame.draw.ellipse(surface, COL_PAW, Rt(inner))
        pygame.draw.ellipse(surface, (150, 148, 158, 90), Rt(rect), _s(2))


def _draw_default_face(surface, anim, look):
    closed = anim.eyes_closed
    lx, ly = look

    # 胡须
    whisk_col = COL_WHISK
    whisk_w = _s(2)
    for x0, x1s in [(100, [(44, 136), (40, 150), (46, 162)]),
                    (200, [(256, 136), (260, 150), (254, 162)])]:
        for tx, ty in x1s:
            pygame.draw.line(surface, whisk_col, (_s(x0), _s(152)),
                             (_s(tx), _s(ty)), whisk_w)
    # 眼睛
    for ex, ey in (EYE_L, EYE_R):
        if closed:
            # 闭眼：一条向下弯的线（画成圆润椭圆线）
            pygame.draw.ellipse(surface, COL_EYE, Rt((ex - 16, ey - 3, 32, 7)))
        else:
            pygame.draw.circle(surface, COL_EYE, (_s(ex), _s(ey)), _s(EYE_RADIUS))
            pygame.draw.circle(surface, COL_PUPIL,
                               (_s(ex + lx), _s(ey + ly)), _s(8))
            pygame.draw.circle(surface, (255, 255, 255),
                               (_s(ex + lx - 6), _s(ey + ly - 6)), _s(4))
            pygame.draw.circle(surface, (255, 255, 255),
                               (_s(ex + lx + 6), _s(ey + ly + 4)), _s(2))

    # 鼻子
    pygame.draw.circle(surface, COL_NOSE, (_s(NOSE_POS[0]), _s(NOSE_POS[1])),
                       _s(NOSE_R))
    pygame.draw.circle(surface, (255, 230, 236),
                       (_s(NOSE_POS[0] - 2), _s(NOSE_POS[1] - 2)), _s(2))

    # 嘴
    if anim.mouth > 0.05:
        mo = anim.mouth
        mw = 14 + 34 * mo
        mh = 8 + 30 * mo
        rect = (150 - mw / 2, 158 - mh / 2, mw, mh)
        _ellipse(surface, rect, (88, 34, 50))
        # 舌头
        _ellipse(surface, (150 - mw / 2 + mw * 0.18, 158 - mh / 2 + mh * 0.5,
                           mw * 0.64, mh * 0.46), (238, 130, 152))
    else:
        # 波状小嘴 ω
        pts = [(141, 149), (147, 155), (150, 150), (153, 155), (159, 149)]
        pygame.draw.lines(surface, COL_MOUTH, False, Pt(pts), _s(2))


# ================================================================== 命中检测
def cat_hit(x, y, cfg=None):
    """设计坐标点是否落在猫身上（用于拖拽窗口）。"""
    ex, ey = x, y
    if _in_ellipse(ex, ey, 150, 110, 70, 66):   # 头
        return True
    if _in_ellipse(ex, ey, 150, 196, 96, 108):  # 身体
        return True
    # 爪子（休息态与按下态并集）
    for cx in (PAW_L_CX, PAW_R_CX):
        for dy in (0, TAP_DIST):
            cy = PAW_CY + dy
            if _in_ellipse(ex, ey, cx, cy, PAW_W / 2 + 5, PAW_H / 2 + 5):
                return True
    return False


def _in_ellipse(x, y, cx, cy, rx, ry):
    dx = (x - cx) / rx
    dy = (y - cy) / ry
    return dx * dx + dy * dy <= 1.0
