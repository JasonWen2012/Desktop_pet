# -*- coding: utf-8 -*-
"""
纹身系统：样式贴图 + 自定义图片 + 部位/大小映射 + 在猫身上绘制。

数据格式（tattoos.json，向后兼容两种写法）：
    旧: {"forehead": "succubus"}
    新: {"forehead": {"type": "style", "ref": "succubus", "scale": 1.2},
         "chest":    {"type": "image", "ref": "tattoos/mine.png", "scale": 0.8}}
内部统一归一化成后者（normalize_entry / clean_mapping）。

样式先绘制成正方形 RGBA 贴图（2x 超采样抗锯齿）；自定义图片用 Pillow
读入并缓存。绘制时按“部位框 × 大小”缩放到猫画布（cat.py 的超采样画布，
坐标需乘 SS）。
"""
import math
import os

import pygame

import config
from cat import SS, TAP_DIST, PAW_CY, PAW_L_CX, PAW_R_CX

# ------------------------------------------------------------------ 常量
REGIONS = [
    ("forehead", "额头"),
    ("cheek_l", "左颊"),
    ("cheek_r", "右颊"),
    ("chest", "胸口"),
    ("belly", "腹部"),
    ("paw_l", "左爪"),
    ("paw_r", "右爪"),
]
REGION_NAMES = dict(REGIONS)

# 非爪部位的基准绘制框（设计坐标 x,y,w,h）；实际大小 = 基准 × scale
BODY_BOXES = {
    "forehead": (120, 52, 60, 36),
    "cheek_l": (88, 120, 38, 34),
    "cheek_r": (174, 120, 38, 34),
    "chest": (122, 222, 56, 42),
    "belly": (134, 268, 34, 34),
}
PAW_HALF = (17, 13)

# 大小范围（1.0 = 基准）
SCALE_MIN, SCALE_MAX = 0.4, 2.5

STYLES = [
    ("heart", "爱心"),
    ("star", "星星"),
    ("moon", "月牙"),
    ("flower", "小花"),
    ("butterfly", "蝴蝶"),
    ("skull", "骷髅"),
    ("cross", "十字"),
    ("rune", "符文"),
    ("succubus", "魅魔纹"),
]
STYLE_NAMES = {sid: name for sid, name in STYLES}
STYLE_IDS = [sid for sid, _ in STYLES]

SPRITE_SRC = 256      # 构建贴图的原始分辨率（2x）
SPRITE_DST = 128      # 缓存贴图分辨率
_sprite_cache = {}
_image_cache = {}


# ================================================================== 数据归一化
def valid_region(r):
    return r in REGION_NAMES


def valid_style(s):
    return s in STYLE_NAMES


def clamp_scale(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        v = 1.0
    if v != v:          # NaN
        v = 1.0
    return min(SCALE_MAX, max(SCALE_MIN, v))


def normalize_entry(value):
    """把一项纹身数据统一成 {'type':'style'|'image','ref':str,'scale':float}。"""
    if isinstance(value, str):
        if not valid_style(value):
            return None
        return {"type": "style", "ref": value, "scale": 1.0}
    if isinstance(value, dict):
        ref = value.get("ref") or value.get("style") or value.get("image")
        if not isinstance(ref, str) or not ref.strip():
            return None
        typ = "image" if (value.get("type") == "image"
                          or value.get("image")) else "style"
        if typ == "style" and not valid_style(ref):
            return None
        return {"type": typ, "ref": ref, "scale": clamp_scale(value.get("scale", 1.0))}
    return None


def clean_mapping(mapping):
    """{部位: 项}，过滤非法部位/数据并归一化。"""
    out = {}
    if isinstance(mapping, dict):
        for r, v in mapping.items():
            if not valid_region(r):
                continue
            e = normalize_entry(v)
            if e:
                out[r] = e
    return out


def entry_scale(entry):
    return clamp_scale((entry or {}).get("scale", 1.0))


def entry_label(entry):
    if not entry:
        return "未纹身"
    if entry.get("type") == "image":
        name = os.path.basename(entry.get("ref", "")) or "自定义图"
        return f"自定义图 {name}"
    return STYLE_NAMES.get(entry.get("ref"), "未纹身")


# ================================================================== 自定义图片
def custom_image(ref):
    """按 tattoos.json 里的 ref 载入自定义纹身图（带缓存）；失败返回 None。"""
    path = config.resolve_tattoo_image(ref)
    if not path:
        return None
    key = str(path)
    if key not in _image_cache:
        surf = None
        try:
            from PIL import Image
            img = Image.open(key).convert("RGBA")
            surf = pygame.image.fromstring(img.tobytes(), img.size, "RGBA")
        except Exception:
            surf = None
        _image_cache[key] = surf
    return _image_cache[key]


def clear_image_cache():
    _image_cache.clear()


def clear_caches():
    """清空样式贴图与自定义图缓存（pygame 重新初始化后必须清理）。"""
    _sprite_cache.clear()
    _image_cache.clear()


# ================================================================== 样式绘制
def _pent_pts(cx, cy, r, n=5, rot=-math.pi / 2):
    pts = []
    for i in range(n):
        a = rot + i * 2 * math.pi / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _pentagram_pts(cx, cy, r, rot=-math.pi / 2):
    """按相隔一个顶点连接，构成五角星(可旋转)"""
    base = _pent_pts(cx, cy, r, 5, rot)
    return [base[i % 5] for i in (0, 2, 4, 1, 3)]


def _heart_pts(cx, cy, u):
    pts = []
    for i in range(49):
        t = i / 48 * 2 * math.pi
        x = 16 * math.sin(t) ** 3
        y = (13 * math.cos(t) - 5 * math.cos(2 * t)
             - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((cx + x * u / 16, cy - y * u / 16))
    return pts


def _build_style(sid):
    """在 256x256 画布绘制某样式，返回 128x128 RGBA 贴图。"""
    surf = pygame.Surface((SPRITE_SRC, SPRITE_SRC), pygame.SRCALPHA)
    cx = cy = SPRITE_SRC // 2
    u = 78  # 单位半径
    w2 = 3

    def P(pts):
        return [(int(x), int(y)) for x, y in pts]

    if sid == "heart":
        pygame.draw.polygon(surf, (238, 70, 105), P(_heart_pts(cx, cy, u)))
        pygame.draw.circle(surf, (255, 150, 175), (cx, cy - int(u * 0.28)),
                           int(u * 0.16))
    elif sid == "star":
        pygame.draw.polygon(surf, (255, 205, 80),
                            P(_pentagram_pts(cx, cy, u * 0.98)))
        pygame.draw.polygon(surf, (255, 236, 150),
                            P(_pentagram_pts(cx, cy, u * 0.42)))
    elif sid == "moon":
        pygame.draw.circle(surf, (225, 236, 255), (cx, cy), int(u * 0.88))
        # 用 alpha=0 的圆“挖”出月牙
        pygame.draw.circle(surf, (0, 0, 0, 0),
                           (cx + int(u * 0.16), cy - int(u * 0.10)),
                           int(u * 0.72))
        pygame.draw.circle(surf, (180, 200, 235), (cx, cy), int(u * 0.88), w2)
    elif sid == "flower":
        petal = (245, 118, 176)
        for i in range(5):
            a = math.pi / 2 + i * 2 * math.pi / 5
            px = cx + u * 0.55 * math.cos(a)
            py = cy - u * 0.55 * math.sin(a)
            pygame.draw.circle(surf, petal, (int(px), int(py)), int(u * 0.38))
        pygame.draw.circle(surf, (255, 224, 130), (cx, cy), int(u * 0.34))
        pygame.draw.circle(surf, (240, 150, 60), (cx, cy), int(u * 0.16))
    elif sid == "butterfly":
        up = (168, 104, 224)
        low = (206, 140, 240)
        pygame.draw.circle(surf, up, (cx - int(u * 0.52), cy - int(u * 0.16)),
                           int(u * 0.52))
        pygame.draw.circle(surf, up, (cx + int(u * 0.52), cy - int(u * 0.16)),
                           int(u * 0.52))
        pygame.draw.circle(surf, low, (cx - int(u * 0.34), cy + int(u * 0.30)),
                           int(u * 0.30))
        pygame.draw.circle(surf, low, (cx + int(u * 0.34), cy + int(u * 0.30)),
                           int(u * 0.30))
        # 身体 + 触角
        pygame.draw.ellipse(surf, (90, 60, 130),
                            (cx - int(u * 0.07), cy - int(u * 0.36),
                             int(u * 0.14), int(u * 0.8)))
        pygame.draw.line(surf, (90, 60, 130), (cx, cy - int(u * 0.30)),
                         (cx - int(u * 0.3), cy - int(u * 0.78)), w2)
        pygame.draw.line(surf, (90, 60, 130), (cx, cy - int(u * 0.30)),
                         (cx + int(u * 0.3), cy - int(u * 0.78)), w2)
        for px, py in ((cx - int(u * 0.32), cy - int(u * 0.84)),
                       (cx + int(u * 0.32), cy - int(u * 0.84))):
            pygame.draw.circle(surf, (140, 80, 190), (px, py), int(u * 0.05))
        # 翅斑
        for sx, sy, rr in ((-48, -44, 10), (48, -44, 10), (-34, 26, 6), (34, 26, 6)):
            pygame.draw.circle(surf, (250, 240, 255),
                               (cx + sx, cy + sy), int(u * rr / 78))
    elif sid == "skull":
        pygame.draw.circle(surf, (226, 226, 234), (cx, cy), int(u * 0.66))
        pygame.draw.rect(surf, (226, 226, 234),
                         (cx - int(u * 0.42), cy - int(u * 0.2),
                          int(u * 0.84), int(u * 0.34)))
        pygame.draw.circle(surf, (40, 36, 52),
                           (cx - int(u * 0.28), cy - int(u * 0.1)), int(u * 0.14))
        pygame.draw.circle(surf, (40, 36, 52),
                           (cx + int(u * 0.28), cy - int(u * 0.1)), int(u * 0.14))
        pygame.draw.polygon(surf, (40, 36, 52),
                            P([(cx - 10, cy + 26), (cx + 10, cy + 26), (cx, cy + 44)]))
        for i in (-1, 0, 1):
            x0 = cx + i * int(u * 0.18)
            pygame.draw.line(surf, (40, 36, 52),
                             (x0, cy + int(u * 0.28)),
                             (x0, cy + int(u * 0.5)), w2)
        pygame.draw.circle(surf, (255, 255, 255), (cx - int(u * 0.3), cy - int(u * 0.44)),
                           int(u * 0.07))
        pygame.draw.circle(surf, (255, 255, 255), (cx + int(u * 0.22), cy - int(u * 0.44)),
                           int(u * 0.05))
    elif sid == "cross":
        col = (178, 46, 70)
        bw = int(u * 0.30)
        pygame.draw.rect(surf, col,
                         (cx - bw // 2, cy - int(u * 0.88), bw, int(u * 1.76)),
                         border_radius=bw // 2)
        pygame.draw.rect(surf, col,
                         (cx - int(u * 0.62), cy - int(u * 0.28),
                          int(u * 1.24), bw), border_radius=bw // 2)
        pygame.draw.rect(surf, (120, 30, 52),
                         (cx - bw // 2, cy - int(u * 0.88), bw, int(u * 1.76)),
                         width=w2, border_radius=bw // 2)
    elif sid == "rune":
        col = (96, 205, 255)
        pygame.draw.circle(surf, col, (cx, cy), int(u * 0.9), w2)
        tri = _pent_pts(cx, cy, u * 0.52, 3, -math.pi / 2)
        pygame.draw.polygon(surf, col, P(tri), w2)
        pygame.draw.line(surf, col, (cx, cy - int(u * 0.52)),
                         (cx, cy + int(u * 0.52)), w2)
        pygame.draw.line(surf, col, (cx - int(u * 0.45), cy),
                         (cx + int(u * 0.45), cy), w2)
        pygame.draw.circle(surf, col, (cx, cy), int(u * 0.12))
        pygame.draw.circle(surf, (60, 160, 255), (cx, cy), int(u * 0.98), w2)
    elif sid == "succubus":
        # 魅魔纹：上端两只小魔翼 + 圆环倒五芒星 + 底部小桃心
        wing = (120, 30, 90)
        pygame.draw.polygon(surf, wing, P([
            (cx - int(u * 0.62), cy - int(u * 0.34)),
            (cx - int(u * 1.02), cy - int(u * 0.72)),
            (cx - int(u * 0.86), cy - int(u * 0.24)),
            (cx - int(u * 0.42), cy - int(u * 0.05))]))
        pygame.draw.polygon(surf, wing, P([
            (cx + int(u * 0.62), cy - int(u * 0.34)),
            (cx + int(u * 1.02), cy - int(u * 0.72)),
            (cx + int(u * 0.86), cy - int(u * 0.24)),
            (cx + int(u * 0.42), cy - int(u * 0.05))]))
        ring = (226, 80, 130)
        pygame.draw.circle(surf, ring, (cx, cy + int(u * 0.05)),
                           int(u * 0.88), w2)
        # 倒五芒星(顶点朝下)
        pts = _pentagram_pts(cx, cy + int(u * 0.05), u * 0.66, rot=math.pi / 2)
        pygame.draw.polygon(surf, ring, P(pts), w2)
        pygame.draw.polygon(surf, (255, 150, 190), P(pts), 1)
        # 底部小桃心
        pygame.draw.polygon(surf, ring, P(_heart_pts(cx, cy + int(u * 0.62),
                                                     u * 0.30)))
    return pygame.transform.smoothscale(surf, (SPRITE_DST, SPRITE_DST))


def style_sprite(sid):
    if sid not in _sprite_cache:
        _sprite_cache[sid] = _build_style(sid)
    return _sprite_cache[sid]


# ================================================================== 绘制到猫
def _blit_entry(surface, entry, box_design):
    """按 部位框 × scale 把纹身（矢量样式或自定义图）画到猫画布(SS)。"""
    x, y, w, h = box_design
    sc = entry_scale(entry)
    cx, cy = (x + w / 2) * SS, (y + h / 2) * SS
    tw, th = max(2, int(round(w * sc * SS))), max(2, int(round(h * sc * SS)))
    if entry.get("type") == "image":
        img = custom_image(entry.get("ref"))
        if img is None:
            return
        iw, ih = img.get_size()
        k = min(tw / iw, th / ih)          # 等比缩放，完整显示不裁切
        nw, nh = max(2, int(iw * k)), max(2, int(ih * k))
        sprite = pygame.transform.smoothscale(img, (nw, nh))
        surface.blit(sprite, (int(cx - nw / 2), int(cy - nh / 2)))
    else:
        sprite = style_sprite(entry.get("ref"))
        if (tw, th) != sprite.get_size():
            sprite = pygame.transform.smoothscale(sprite, (tw, th))
        surface.blit(sprite, (int(cx - tw / 2), int(cy - th / 2)))


def draw_body_tattoos(surface, mapping, anim=None):
    """额头/脸颊/胸口/腹部（在服饰与头饰之上、双爪之前绘制）"""
    for region, entry in clean_mapping(mapping).items():
        box = BODY_BOXES.get(region)
        if box:
            _blit_entry(surface, entry, box)


def draw_paw_tattoos(surface, mapping, anim):
    """左右爪纹身：跟着敲击动画一起上下移动。"""
    anim = anim or _IdleAnim()
    for region, entry in clean_mapping(mapping).items():
        if region == "paw_l":
            cx, off = PAW_L_CX, anim.paw_l
        elif region == "paw_r":
            cx, off = PAW_R_CX, anim.paw_r
        else:
            continue
        cy = PAW_CY + TAP_DIST * off
        hw, hh = PAW_HALF
        _blit_entry(surface, entry, (cx - hw, cy - hh, hw * 2, hh * 2))


class _IdleAnim:
    paw_l = 0.0
    paw_r = 0.0
