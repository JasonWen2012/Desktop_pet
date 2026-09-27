# -*- coding: utf-8 -*-
"""开发用离屏渲染 QA：输出若干 PNG 供目检造型。不属于运行依赖。"""
import os
import sys
import math

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

pygame.init()

from cat import (DW, DH, SS, CatAnim, draw_cat, load_face_surface)  # noqa: E402
from deco import draw_background, draw_handheld  # noqa: E402
from ui import DressPanel, CtxMenu, get_font  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "qa")
os.makedirs(OUT, exist_ok=True)


def checker(w, h, s=10):
    surf = pygame.Surface((w, h))
    for y in range(0, h, s):
        for x in range(0, w, s):
            c = (235, 226, 216) if ((x // s) + (y // s)) % 2 == 0 else (214, 205, 196)
            surf.fill(c, (x, y, s, s))
    return surf


def scene(cfg, anim=None, look=(0, 0), bg=True):
    anim = anim or CatAnim()
    master = pygame.Surface((DW * SS, DH * SS), pygame.SRCALPHA)
    if bg:
        draw_background(master, 0.3, cfg)
    canvas = pygame.Surface((DW * SS, DH * SS), pygame.SRCALPHA)
    draw_cat(canvas, cfg, anim, look)
    sq = anim.breath
    w, h = canvas.get_size()
    sh = max(2, int(round(h * sq)))
    master.blit(pygame.transform.smoothscale(canvas, (w, sh)), (0, h - sh))
    draw_handheld(master, 1.0, cfg)
    out = pygame.transform.smoothscale(master, (DW, DH))
    return out


def save(name, surf):
    path = os.path.join(OUT, name)
    pygame.image.save(surf, path)
    print("saved", path)


def to_preview(scene_surf):
    pre = checker(DW, DH)
    pre.blit(scene_surf, (0, 0))
    return pre


def main():
    # 1 默认猫
    save("1_default.png", to_preview(scene({"decorations": []})))
    # 2 全部装饰
    all_d = {"decorations": ["bow", "crown", "headphones", "glasses",
                              "sunglasses", "bowtie", "scarf", "cape",
                              "coffee", "guitar", "rainbow", "stars"]}
    save("2_all.png", to_preview(scene(all_d)))
    # 3 敲击左爪 + 眼睛看向左下
    anim = CatAnim()
    anim.left = True
    anim.update(0.2)
    save("3_tap_left.png", to_preview(scene({"decorations": ["coffee"]},
                                            anim, look=(-5, 4))))
    # 4 哈欠
    anim = CatAnim()
    anim.yawn_t = 1.5
    anim.update(0.0)
    anim.mouth = 1.0
    save("4_yawn.png", to_preview(scene({"decorations": []}, anim)))
    # 5 眨眼
    anim = CatAnim()
    anim.blink = 0.1
    save("5_blink.png", to_preview(scene({"decorations": []}, anim)))
    # 6 背景单独（彩虹方向检查）
    save("6_rainbow.png", to_preview(scene({"decorations": ["rainbow", "stars"]},
                                           CatAnim(), bg=True)))
    # 10 纯背景
    m = pygame.Surface((DW * SS, DH * SS), pygame.SRCALPHA)
    draw_background(m, 0.3, {"decorations": ["rainbow", "stars"]})
    save("10_bg_only.png", to_preview(pygame.transform.smoothscale(m, (DW, DH))))
    # 11 纯吉他
    m = pygame.Surface((DW * SS, DH * SS), pygame.SRCALPHA)
    draw_handheld(m, 0.5, {"decorations": ["guitar"]})
    save("11_guitar.png", to_preview(pygame.transform.smoothscale(m, (DW, DH))))
    # 12 纯咖啡
    m = pygame.Surface((DW * SS, DH * SS), pygame.SRCALPHA)
    draw_handheld(m, 0.3, {"decorations": ["coffee"]})
    save("12_coffee.png", to_preview(pygame.transform.smoothscale(m, (DW, DH))))
    # 7 照片脸
    face_path = os.path.join(OUT, "face_sample.png")
    make_sample_face(face_path)
    cfg = {"decorations": ["bow"], "face": face_path}
    cfg["_face_surf"] = load_face_surface(face_path)
    save("7_face.png", to_preview(scene(cfg)))
    # 8 面板
    fw = DW + 236
    frame = pygame.Surface((fw, DH), pygame.SRCALPHA)
    frame.blit(to_preview(scene({"decorations": ["bow", "coffee", "rainbow"]})), (0, 0))
    panel = DressPanel()
    cfgp = {"decorations": ["bow", "coffee", "rainbow"], "panel_open": True}
    panel.draw(frame, cfgp, fw, DH)
    save("8_panel.png", frame)
    # 9 菜单
    frame = to_preview(scene({"decorations": ["crown", "rainbow"]}))
    menu = CtxMenu()
    rows = [
        {"type": "chk", "label": "换装面板", "checked": lambda: False},
        {"type": "sub", "label": "穿搭方案"},
        {"type": "sub", "label": "监听设置"},
        {"type": "act", "label": "上传照片…"},
        {"type": "act", "label": "恢复默认"},
        {"type": "sub", "label": "缩放调节"},
        {"type": "chk", "label": "开机自启", "checked": lambda: True},
        {"type": "sep", "label": "———"},
        {"type": "act", "label": "退出"},
    ]
    menu.open(rows, 20, 14, DW, DH)
    menu.draw(frame, (30, 60))
    save("9_menu.png", frame)


def make_sample_face(path):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (400, 400), (120, 180, 240))
    d = ImageDraw.Draw(img)
    d.ellipse((60, 60, 340, 340), fill=(240, 200, 170))
    d.ellipse((150, 140, 220, 210), fill=(40, 40, 60))
    d.ellipse((180, 140, 250, 210), fill=(40, 40, 60))
    d.arc((160, 180, 240, 260), 20, 160, fill=(140, 60, 70), width=8)
    d.rectangle((0, 300, 400, 400), fill=(80, 130, 90))
    img.save(path)


if __name__ == "__main__":
    main()
