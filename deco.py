# -*- coding: utf-8 -*-
"""
背景装饰（彩虹/星星）与手持物（咖啡杯/吉他）。
画在主画布（超采样 SS）上：背景先于猫，手持物后于猫。
"""
import math

import pygame

from cat import SS, _s

# 背景
_RAINBOW_COLORS = [(240, 84, 96), (248, 158, 76), (252, 214, 88),
                   (150, 202, 120), (104, 186, 224), (122, 126, 226),
                   (206, 110, 214)]
_RAINBOW_R = [330, 320, 310, 300, 290, 280, 270]

# 星星固定位置 (x, y, 半径, 相位)
_STARS = [(44, 66, 7, 0.0), (256, 42, 6, 1.7), (40, 158, 5, 3.1),
          (262, 166, 8, 4.4), (28, 306, 5, 2.2), (270, 272, 6, 5.3),
          (152, 20, 5, 0.9), (74, 250, 4, 5.8), (230, 240, 4, 1.2)]

_guitar_cache = None


def _decos(cfg):
    return set(cfg.get("decorations", []) or [])


def _star_pts(cx, cy, r):
    pts = []
    for k in range(8):
        ang = math.pi / 2 + k * math.pi / 4
        rr = r if k % 2 == 0 else r * 0.42
        pts.append((cx + rr * math.cos(ang), cy - rr * math.sin(ang)))
    return [(int(x * SS), int(y * SS)) for x, y in pts]


# ================================================================== 背景
def draw_background(surface, t, cfg):
    decos = _decos(cfg)

    # 脚下的柔和影子（始终有）
    pygame.draw.ellipse(surface, (40, 40, 60, 70), (_s(52), _s(330), _s(196), _s(16)))

    if "rainbow" in decos:
        cx, cy = 150.0, 360.0
        for col, r in zip(_RAINBOW_COLORS, _RAINBOW_R):
            rect = (_s(cx - r), _s(cy - r), _s(2 * r), _s(2 * r))
            pygame.draw.arc(surface, col, rect, 0.0, math.pi, _s(11))

    if "stars" in decos:
        for sx, sy, r, ph in _STARS:
            a = int(95 + 150 * (0.5 + 0.5 * math.sin(t * 2.3 + ph)) ** 2)
            pygame.draw.polygon(surface, (255, 246, 205, a), _star_pts(sx, sy, r))
            pygame.draw.circle(surface, (255, 250, 220, min(255, a + 40)),
                               (_s(sx), _s(sy)), _s(1.5))


# ================================================================== 咖啡杯
def draw_coffee(surface, t):
    # 杯身
    pygame.draw.rect(surface, (255, 255, 255), (_s(116), _s(272), _s(68), _s(54)),
                     border_radius=_s(12))
    pygame.draw.rect(surface, (224, 210, 190), (_s(116), _s(272), _s(68), _s(54)),
                     width=_s(2), border_radius=_s(12))
    # 杯口深色饮料
    pygame.draw.ellipse(surface, (150, 105, 60), (_s(116), _s(266), _s(68), _s(12)))
    # 把手（右侧开口环）
    pygame.draw.arc(surface, (255, 255, 255), (_s(182), _s(284), _s(34), _s(38)),
                    -1.05, 1.05, _s(8))
    # 小爱心
    pygame.draw.circle(surface, (240, 92, 116), (_s(150), _s(294)), _s(5))
    pygame.draw.polygon(surface, (240, 92, 116),
                        [(_s(145), _s(295)), (_s(155), _s(295)), (_s(150), _s(304))])
    # 上升的蒸汽
    for i, dx in enumerate((-16, 10)):
        ph = (t * 0.35 + i * 0.5) % 1.0
        y = 258 - 34 * ph
        a = int(150 * (1.0 - ph))
        if a > 8:
            pygame.draw.ellipse(surface, (255, 255, 255, a),
                                (_s(148 + dx), _s(y), _s(9), _s(12)))


# ================================================================== 吉他
def _build_guitar():
    """竖版吉他原图（本地坐标 64x250，放大 SS），再整体倾斜。"""
    w, h = 64, 250
    big = pygame.Surface((w * SS, h * SS), pygame.SRCALPHA)
    wood = (216, 150, 98)
    wood_d = (152, 100, 60)
    neck = (154, 106, 68)
    dark = (58, 40, 30)
    # 琴头
    pygame.draw.rect(big, wood_d, (_s(20), _s(6), _s(24), _s(34)), border_radius=_s(7))
    for i in range(3):
        pygame.draw.circle(big, (232, 232, 210), (_s(26 + i * 6), _s(12)), _s(1))
    # 琴颈
    pygame.draw.rect(big, neck, (_s(26), _s(38), _s(12), _s(152)))
    pygame.draw.rect(big, wood_d, (_s(24), _s(38), _s(16), _s(152)), width=_s(1))
    # 品丝
    for fy in range(52, 182, 14):
        pygame.draw.line(big, (92, 72, 48), (_s(25), _s(fy)), (_s(39), _s(fy)), 1)
    # 琴身
    pygame.draw.ellipse(big, wood, (_s(2), _s(176), _s(60), _s(72)))
    pygame.draw.ellipse(big, wood_d, (_s(2), _s(176), _s(60), _s(72)), width=_s(2))
    # 音孔
    pygame.draw.circle(big, dark, (_s(32), _s(210)), _s(13))
    pygame.draw.circle(big, (100, 66, 44), (_s(32), _s(210)), _s(17), width=_s(2))
    # 琴码
    pygame.draw.rect(big, dark, (_s(23), _s(238), _s(18), _s(7)), border_radius=_s(2))
    # 琴弦
    for i in range(6):
        sx = 28 + i * 1.6
        pygame.draw.line(big, (235, 228, 200), (_s(sx), _s(44)),
                         (_s(sx), _s(237)), 1)
    rot = pygame.transform.rotate(big, 17)  # 顶部向左倾
    return rot


_GUITAR_CENTER = (246.0, 250.0)   # 设计坐标：让旋转后精灵中心落在这


def draw_guitar(surface, t):
    global _guitar_cache
    if _guitar_cache is None:
        _guitar_cache = _build_guitar()
    rw, rh = _guitar_cache.get_size()
    cx, cy = _GUITAR_CENTER
    ox = int(round(cx * SS - rw / 2))
    oy = int(round(cy * SS - rh / 2))
    surface.blit(_guitar_cache, (ox, oy))


# ================================================================== 入口
def draw_handheld(surface, t, cfg):
    decos = _decos(cfg)
    if "coffee" in decos:
        draw_coffee(surface, t)
    if "guitar" in decos:
        draw_guitar(surface, t)
