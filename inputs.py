# -*- coding: utf-8 -*-
"""
全局键盘/鼠标监听封装（pynput）。
键盘按物理左右半区映射左右爪：空格 = 双爪齐敲；鼠标任意键按下 = 双爪敲。
"""
import collections
import threading

try:
    from pynput import keyboard, mouse
    HAVE_PYNPUT = True
except Exception:  # 允许在没有 pynput 的环境下仅跑绘图调试
    HAVE_PYNPUT = False

# 左右半区按键（用小写名/字符）
_LEFT = set("qwertasdfgzxcvb12345`")
_RIGHT = set("yuiophjklnm67890-=[]\\;',./")
_LEFT |= {"tab", "caps_lock", "left_shift", "left_ctrl", "left_alt",
          "shift", "ctrl", "alt", "cmd", "cmd_l", "win", "win_l",
          "escape", "f1", "f2", "f3", "f4", "f5", "f6"}
_RIGHT |= {"right_shift", "right_ctrl", "right_alt", "cmd_r", "win_r",
           "menu", "enter", "return", "backspace", "insert", "delete",
           "home", "end", "page_up", "page_down", "print_screen",
           "scroll_lock", "pause", "f7", "f8", "f9", "f10", "f11", "f12",
           "up", "down", "left", "right", "num_lock", "num_enter",
           "num_plus", "num_minus", "num_multiply", "num_divide",
           "num_decimal"}
_RIGHT |= {f"num_{i}" for i in range(10)}
_BOTH = {"space"}
_MOUSE_BUTTONS = {"left", "right", "middle"}


def classify_key(key):
    """返回 'left' / 'right' / 'both' / None。"""
    if isinstance(key, keyboard.Key):
        name = key.name
    else:
        ch = getattr(key, "char", None)
        if ch is None:
            return None
        name = ch.lower()
    if name in _BOTH:
        return "both"
    if name in _LEFT:
        return "left"
    if name in _RIGHT:
        return "right"
    return None  # 未识别按键不触发（避免乱动）


class GlobalInput:
    """后台线程监听全局键盘/鼠标，把解析后的事件压入队列。"""

    def __init__(self):
        self.events = collections.deque(maxlen=1024)
        self._lock = threading.Lock()
        self._kb = None
        self._mouse = None
        self.threads = []
        self.running = False

    # ------------------------------------------------------------ 线程回调
    def _push(self, item):
        with self._lock:
            self.events.append(item)

    def _on_press(self, key):
        self._push(("key", classify_key(key), True))

    def _on_release(self, key):
        self._push(("key", classify_key(key), False))

    def _on_click(self, x, y, button, pressed):
        try:
            name = button.name if hasattr(button, "name") else str(button)
        except Exception:
            name = "left"
        if name in _MOUSE_BUTTONS:
            self._push(("mouse", name, pressed, x, y))
        else:  # 滚轮等
            self._push(("mouse", name, None, x, y))

    # ------------------------------------------------------------ 启停
    def start(self, keyboard_on=True, mouse_on=True):
        if not HAVE_PYNPUT:
            print("[inputs] 未安装 pynput，全局监听不可用")
            return
        self.running = True
        if keyboard_on:
            self._kb = keyboard.Listener(on_press=self._on_press,
                                         on_release=self._on_release)
            self._kb.start()
            self.threads.append(self._kb)
        if mouse_on:
            self._mouse = mouse.Listener(on_click=self._on_click)
            self._mouse.start()
            self.threads.append(self._mouse)

    def stop(self):
        self.running = False
        for t in self.threads:
            try:
                t.stop()
            except Exception:
                pass
        self.threads.clear()

    def poll(self):
        """取出本帧事件列表。"""
        with self._lock:
            out = list(self.events)
            self.events.clear()
        return out
