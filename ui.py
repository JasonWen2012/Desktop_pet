# -*- coding: utf-8 -*-
"""右键菜单 / 换装面板 / 输入弹窗（全部用 pygame 绘制，中文）。"""
import os

import pygame

# ---------------------------------------------------------------- 字体
_font_path = None
_font_cache = {}


def _find_font():
    global _font_path
    if _font_path is not None:
        return _font_path
    candidates = []
    if os.name == "nt":
        base = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
        candidates = [os.path.join(base, n) for n in
                      ("msyh.ttc", "msyhbd.ttc", "simhei.ttf", "simsun.ttc",
                       "Deng.ttf", "simfang.ttf", "simkai.ttf", "arial.ttf")]
    else:
        candidates = ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                      "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                      "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for p in candidates:
        if os.path.exists(p):
            _font_path = p
            return p
    _font_path = ""   # 空字符串 = 用 pygame 默认
    return _font_path


def get_font(size):
    key = size
    if key not in _font_cache:
        path = _find_font()
        if path:
            _font_cache[key] = pygame.font.Font(path, int(size))
        else:
            _font_cache[key] = pygame.font.SysFont(None, int(size))
    return _font_cache[key]


def reset_font_cache():
    """
    清空字体缓存。pygame.quit() 之后缓存的 Font 已失效，重新
    pygame.init() 后继续使用旧 Font 会导致崩溃，所以（重新）初始化
    显示前先调用一次。
    """
    _font_cache.clear()


# ---------------------------------------------------------------- 文本自适应
def fit_text(text, size, max_w, color=(240, 240, 246), ellipsis="…"):
    """
    在 max_w 宽度内渲染文本：先逐级缩小字号，仍放不下就截断并加省略号。
    返回 (surface, 实际显示的文本)。
    """
    max_w = max(12, int(max_w))
    for s in (size, size - 1, size - 2, max(9, size - 3)):
        f = get_font(s)
        if f.size(text)[0] <= max_w:
            return f.render(text, True, color), text
    f = get_font(max(9, size - 3))
    shown = text
    while shown and f.size(shown + ellipsis)[0] > max_w:
        shown = shown[:-1]
    out = (shown + ellipsis) if shown != text else text
    return f.render(out, True, color), out


def fit_text_tail(text, size, max_w, color=(240, 240, 246)):
    """
    单行输入框用：超宽时从左侧滚动（保留末尾，方便看正在输入的内容）。
    返回 (surface, 实际显示的文本)。
    """
    max_w = max(12, int(max_w))
    f = get_font(size)
    shown = text
    while shown and f.size(shown)[0] > max_w:
        shown = shown[1:]
    return f.render(shown, True, color), shown


# ---------------------------------------------------------------- 常量
PANEL_W = 236

# 换装面板里的两个“头像”特殊项（非装饰 id）
FACE_DEFAULT = "__face_default__"   # 换回默认卡通猫头
FACE_UPLOAD = "__face_upload__"     # 上传自定义头像

CATEGORIES = [
    ("头饰", ["bow", "crown", "headphones"]),
    ("眼镜", ["glasses", "sunglasses"]),
    ("服装", ["bowtie", "scarf", "cape"]),
    ("手持", ["coffee", "guitar"]),
    ("背景", ["rainbow", "stars"]),
]
LABELS = {
    "bow": "蝴蝶结", "crown": "王冠", "headphones": "耳机",
    "glasses": "圆框", "sunglasses": "墨镜",
    "bowtie": "领结", "scarf": "围巾", "cape": "披风",
    "coffee": "咖啡杯", "guitar": "吉他",
    "rainbow": "彩虹", "stars": "星星",
    FACE_DEFAULT: "卡通猫头", FACE_UPLOAD: "上传照片…",
}

BG_MENU = (36, 33, 50, 246)
BG_HOVER = (88, 82, 120, 255)
FG_TEXT = (240, 240, 246)
FG_DIM = (168, 165, 185)
FG_GOLD = (255, 208, 100)
ACCENT = (120, 150, 255)


def rounded(surface, color, rect, radius):
    pygame.draw.rect(surface, color, rect, border_radius=radius)


# ------------------------------------------------------------ 自绘符号
# 说明：微软雅黑等常见中文字体没有 ✓(U+2713)/✕(U+2715)/›/✨ 等字形，
# 会渲染成方框(豆腐块)。所以勾、叉、箭头、星花全部用 pygame 画线自绘。
def draw_tick(surface, cx, cy, color, s=7, w=2):
    """勾 ✓"""
    pygame.draw.line(surface, color, (cx - s, cy), (cx - s * 0.2, cy + s * 0.6), w)
    pygame.draw.line(surface, color, (cx - s * 0.2, cy + s * 0.6),
                     (cx + s, cy - s * 0.7), w)


def draw_cross(surface, cx, cy, color, s=6, w=2):
    """叉 ✕"""
    pygame.draw.line(surface, color, (cx - s, cy - s), (cx + s, cy + s), w)
    pygame.draw.line(surface, color, (cx + s, cy - s), (cx - s, cy + s), w)


def draw_chev(surface, cx, cy, color, direction=1, s=5, w=2):
    """箭头 ›(1) / ‹(-1)"""
    a = cx + direction * s
    pygame.draw.line(surface, color, (cx - direction * s, cy - s), (a, cy), w)
    pygame.draw.line(surface, color, (a, cy), (cx - direction * s, cy + s), w)


def star4_pts(cx, cy, r):
    """四角星花（8 个顶点，内外交替）"""
    import math
    pts = []
    for k in range(8):
        ang = math.pi / 2 + k * math.pi / 4
        rr = r if k % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(ang), cy - rr * math.sin(ang)))
    return pts


# ================================================================ 换装面板
class DressPanel:
    """右侧的换装开关面板（两列网格）。坐标均为窗口像素。"""

    _ORDER = ["bow", "crown", "headphones", "glasses", "sunglasses",
              "bowtie", "scarf", "cape", "coffee", "guitar",
              "rainbow", "stars", FACE_DEFAULT, FACE_UPLOAD]

    def __init__(self):
        self.cells = {}       # id -> pygame.Rect
        self.close_rect = None

    def region(self, win_w, win_h):
        return pygame.Rect(win_w - PANEL_W, 0, PANEL_W, win_h)

    def draw(self, surface, cfg, win_w, win_h):
        decos = set(cfg.get("decorations", []) or [])
        self.cells.clear()
        region = self.region(win_w, win_h)

        # 背景
        rounded(surface, (30, 27, 46, 232), region, 18)
        pygame.draw.rect(surface, (255, 255, 255, 26), region, width=1,
                         border_radius=18)

        # 标题(星花自绘) + 关闭
        sx, sy = region.x + 30, region.y + 22
        pygame.draw.polygon(surface, FG_GOLD, star4_pts(sx, sy, 9))
        pygame.draw.polygon(surface, (255, 236, 170), star4_pts(sx, sy, 4))
        title = get_font(16).render("换 装", True, FG_GOLD)
        surface.blit(title, (region.x + 42, region.y + 12))
        self.close_rect = pygame.Rect(region.right - 38, region.y + 10, 26, 26)
        rounded(surface, (90, 84, 120, 255), self.close_rect, 8)
        draw_cross(surface, self.close_rect.centerx, self.close_rect.centery,
                   (255, 255, 255), s=6, w=2)

        # 两列网格
        x0, y0 = region.x + 14, region.y + 48
        gap, cw = 8, (PANEL_W - 28 - 8) // 2
        cell_f = get_font(14)
        for i, id_ in enumerate(self._ORDER):
            col, row = i % 2, i // 2
            rect = pygame.Rect(x0 + col * (cw + gap), y0 + row * 26, cw, 22)
            self.cells[id_] = rect
            # 特殊项：头像开关（默认猫头 / 上传照片）
            if id_ == FACE_DEFAULT:
                on = not cfg.get("face")
            elif id_ == FACE_UPLOAD:
                on = bool(cfg.get("face"))
            else:
                on = id_ in decos
            if on:
                rounded(surface, (118, 96, 210, 255), rect, 7)
            else:
                rounded(surface, (58, 54, 82, 255), rect, 7)
            pygame.draw.rect(surface, (255, 255, 255, 40), rect, width=1,
                             border_radius=7)
            # 复选框
            box = pygame.Rect(rect.x + 6, rect.y + 5, 12, 12)
            pygame.draw.rect(surface, (20, 18, 32), box, border_radius=3)
            if on:
                pygame.draw.line(surface, FG_GOLD, (box.x + 2, box.y + 6),
                                 (box.x + 5, box.y + 9), 2)
                pygame.draw.line(surface, FG_GOLD, (box.x + 5, box.y + 9),
                                 (box.x + 11, box.y + 2), 2)
            c = FG_TEXT if on else FG_DIM
            tx = cell_f.render(LABELS[id_], True, c)
            surface.blit(tx, (rect.x + 23, rect.y + 3))
        # 提示
        hint = get_font(12).render("右键小猫 / 更多设置", True, FG_DIM)
        surface.blit(hint, (region.x + 18, region.bottom - 24))

    def cell_id_at(self, pos):
        for id_, r in self.cells.items():
            if r.collidepoint(pos):
                return id_
        return None


# ================================================================ 右键菜单
class CtxMenu:
    """通用右键菜单：支持 act / chk / sub / sep。"""

    ROW_H = 30
    PAD = 8

    def __init__(self):
        self.open_ = False
        self.stack = []
        self.rows = []
        self.rects = []
        self.origin = (0, 0)
        self.size = (0, 0)
        self.scroll = 0
        self.hover = -1

    # ------------------------------------------------------------ 打开
    def open(self, items, x, y, win_w, win_h):
        self.stack = [list(items)]
        self.rows = self.stack[0]
        self._win_w, self._win_h = win_w, win_h
        self.open_ = True
        self.scroll = 0
        self._layout(x, y, win_w, win_h)

    @staticmethod
    def _with_back(rows):
        return rows  # back 只在子菜单里出现

    def _subrows(self, children):
        out = [{"type": "back", "label": "返回"}]
        out += list(children)
        return out

    # ------------------------------------------------------------ 布局
    def _layout(self, x, y, win_w, win_h):
        f = get_font(15)
        max_w = 120
        for it in self.rows:
            w = f.size(it.get("label", ""))[0]
            w += 90 if it["type"] in ("sub", "chk") else 60
            max_w = max(max_w, w)
        w = min(max_w + 2 * self.PAD, win_w - 12)
        max_h = min(win_h - 16, len(self.rows) * self.ROW_H + 2 * self.PAD)
        h = len(self.rows) * self.ROW_H + 2 * self.PAD
        if x + w > win_w - 4:
            x = win_w - w - 4
        if y + min(h, max_h) > win_h - 4:
            y = win_h - min(h, max_h) - 4
        x = max(4, x)
        y = max(4, y)
        self.origin = (x, y)
        self.size = (w, min(h, max_h))
        # 需要滚动的行数
        visible = max(1, (self.size[1] - 2 * self.PAD) // self.ROW_H)
        self.visible = visible
        self.max_scroll = max(0, len(self.rows) - visible)

    def rects_now(self):
        x, y = self.origin
        out = []
        for i in range(self.visible):
            idx = i + self.scroll
            if idx >= len(self.rows):
                break
            r = pygame.Rect(x + self.PAD, y + self.PAD + i * self.ROW_H,
                            self.size[0] - 2 * self.PAD, self.ROW_H - 4)
            out.append((idx, r))
        return out

    def hit(self, pos):
        for idx, r in self.rects_now():
            if r.collidepoint(pos):
                return idx
        return None

    # ------------------------------------------------------------ 交互
    def click(self, pos):
        """返回 ('run', item) / 'sub' / 'outside'；'outside' 需要关菜单。"""
        if not self.open_:
            return "outside"
        idx = self.hit(pos)
        if idx is None:
            return "outside"
        item = self.rows[idx]
        t = item["type"]
        if t == "back":
            self.stack.pop()
            self._enter()
            return "sub"
        if t == "sub":
            children = item["children"]() if callable(item["children"]) else item["children"]
            self.stack.append(self._subrows(children))
            self._enter()
            return "sub"
        if t in ("act", "chk"):
            return ("run", item)
        return "sub"   # sep

    def _enter(self):
        self.rows = self.stack[-1]
        self.scroll = 0
        self.hover = -1
        x, y = self.origin
        self._layout(x, y, self._win_w, self._win_h)

    def wheel(self, dy):
        if not self.open_:
            return
        self.scroll = max(0, min(self.max_scroll, self.scroll - dy))

    def close(self):
        self.open_ = False
        self.stack.clear()
        self.rows = []

    # ------------------------------------------------------------ 绘制
    def draw(self, surface, mouse_pos):
        if not self.open_ or not self.rows:
            return
        x, y = self.origin
        w, h = self.size
        rounded(surface, BG_MENU, (x, y, w, h), 12)
        pygame.draw.rect(surface, (255, 255, 255, 40), (x, y, w, h),
                         width=1, border_radius=12)
        f = get_font(15)
        self.hover = -1
        hit = self.hit(mouse_pos)
        if hit is not None:
            self.hover = hit
        for idx, r in self.rects_now():
            item = self.rows[idx]
            if idx == self.hover:
                rounded(surface, BG_HOVER, r, 8)
            label = item.get("label", "")
            t = item["type"]
            col = FG_TEXT
            cy = r.centery
            text_x = r.x + 12
            if t == "chk":
                # 自绘小勾选框，避免字体缺 ✓ 字形
                ck = item.get("checked")
                if ck is None:
                    val = (item.get("state", lambda: False))()
                elif callable(ck):
                    val = ck()
                else:
                    val = bool(ck)
                bx = r.x + 10
                pygame.draw.rect(surface, (20, 18, 32),
                                 (bx, cy - 7, 14, 14), border_radius=3)
                if val:
                    pygame.draw.rect(surface, FG_GOLD,
                                     (bx, cy - 7, 14, 14), width=1, border_radius=3)
                    draw_tick(surface, bx + 7, cy, FG_GOLD, s=5, w=2)
                    col = FG_GOLD
                text_x = bx + 22
            elif t == "back":
                draw_chev(surface, r.x + 18, cy, FG_DIM, direction=-1, s=5, w=2)
                text_x = r.x + 30
                col = FG_DIM
            elif t in ("sep", "title"):
                col = FG_DIM
            # 窄窗口下长标签按可用宽度截断，避免溢出菜单/窗口
            avail = r.w - (text_x - r.x) - (22 if t == "sub" else 8)
            txt, _ = fit_text(label, 15, avail, col)
            surface.blit(txt, (text_x, cy - txt.get_height() // 2 - 1))
            if t == "sub":
                draw_chev(surface, r.right - 16, cy, FG_DIM, direction=1,
                          s=5, w=2)
        # 滚动指示
        if self.max_scroll > 0:
            pygame.draw.polygon(surface, FG_DIM,
                                [(x + w // 2 - 4, y + h - 6),
                                 (x + w // 2 + 4, y + h - 6),
                                 (x + w // 2, y + h - 2)])


# ================================================================ 输入弹窗
class InputModal:
    """方案命名弹窗。"""

    def __init__(self, title, prompt, initial=""):
        self.title = title
        self.prompt = prompt
        self.text = initial
        self.done = None        # None 进行中 / ('ok',text) / ('cancel',None)
        self.win_w = 0
        self.win_h = 0
        self._rect = None
        self._ok_rect = None
        self._cancel_rect = None

    def resize(self, win_w, win_h):
        """按窗口大小自适应：窗口被缩小(scale 调小)时弹窗也跟着变小，不被裁切。"""
        self.win_w, self.win_h = win_w, win_h
        w = max(150, min(300, win_w - 16))
        h = max(112, min(158, win_h - 16))
        self._rect = pygame.Rect((win_w - w) // 2, (win_h - h) // 2, w, h)
        self._small = w < 250
        bw = max(54, min(72, (w - 40) // 2))
        by = self._rect.bottom - 34
        self._ok_rect = pygame.Rect(self._rect.right - 12 - bw * 2 - 8, by, bw, 26)
        self._cancel_rect = pygame.Rect(self._rect.right - 12 - bw, by, bw, 26)

    def click(self, pos):
        if self._ok_rect and self._ok_rect.collidepoint(pos):
            self.done = ("ok", self.text.strip())
        elif self._cancel_rect and self._cancel_rect.collidepoint(pos):
            self.done = ("cancel", None)
        elif self._rect and not self._rect.collidepoint(pos):
            self.done = ("cancel", None)

    def key(self, unicode_char=None, backspace=False, enter=False, esc=False):
        if backspace:
            self.text = self.text[:-1]
        elif enter:
            self.done = ("ok", self.text.strip())
        elif esc:
            self.done = ("cancel", None)
        elif unicode_char and len(self.text) < 20:
            self.text += unicode_char

    def draw(self, surface, t):
        if self._rect is None:
            return
        ov = pygame.Surface((self.win_w, self.win_h), pygame.SRCALPHA)
        ov.fill((10, 10, 18, 150))
        surface.blit(ov, (0, 0))
        r = self._rect
        small = getattr(self, "_small", False)
        rounded(surface, (46, 43, 64, 255), r, 14)
        pygame.draw.rect(surface, (255, 255, 255, 50), r, width=1, border_radius=14)

        title_s, _ = fit_text(self.title, 15 if small else 16, r.w - 24, FG_GOLD)
        surface.blit(title_s, (r.x + 12, r.y + 8))
        prom, _ = fit_text(self.prompt, 12 if small else 14, r.w - 24, FG_DIM)
        surface.blit(prom, (r.x + 12, r.y + (30 if small else 40)))

        box = pygame.Rect(r.x + 12, r.y + (50 if small else 62), r.w - 24,
                          26 if small else 30)
        rounded(surface, (20, 18, 32), box, 8)
        pygame.draw.rect(surface, ACCENT, box, width=1, border_radius=8)
        tx, shown = fit_text_tail(self.text, 13 if small else 15,
                                  box.w - 16, FG_TEXT)
        surface.blit(tx, (box.x + 8, box.centery - tx.get_height() // 2))
        if int(t * 2) % 2 == 0:
            cx = box.x + 8 + tx.get_width() + 2
            pygame.draw.line(surface, FG_GOLD, (cx, box.y + 5),
                             (cx, box.bottom - 5), 2)
        # 按钮
        for rect, label, colr in ((self._ok_rect, "保 存", ACCENT),
                                  (self._cancel_rect, "取 消", (80, 76, 104))):
            rounded(surface, colr, rect, 8)
            b, _ = fit_text(label, 13 if small else 14, rect.w - 8,
                            (255, 255, 255))
            surface.blit(b, b.get_rect(center=rect.center))
