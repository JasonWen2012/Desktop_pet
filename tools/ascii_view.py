# -*- coding: utf-8 -*-
"""开发用：把 QA PNG 转成彩色 ASCII 缩略图，便于文本目检造型。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image

PROTO = [
    ("R", (226, 70, 86)), ("O", (246, 162, 80)), ("Y", (250, 214, 88)),
    ("G", (120, 202, 130)), ("B", (104, 172, 226)), ("P", (150, 110, 210)),
    ("M", (236, 130, 168)), ("W", (252, 252, 252)), ("w", (238, 238, 238)),
    ("x", (150, 146, 158)), ("D", (46, 44, 60)), ("K", (22, 20, 34)),
    ("d", (96, 92, 116)), ("T", (250, 200, 120)),
]


def classify(px):
    best, bc = "?", 10 ** 9
    for ch, c in PROTO:
        dd = (px[0] - c[0]) ** 2 + (px[1] - c[1]) ** 2 + (px[2] - c[2]) ** 2
        if dd < bc:
            bc, best = dd, ch
    return best


def view(path, cols=110):
    img = Image.open(path).convert("RGBA")
    w, h = img.size
    rows = max(8, int(h / w * cols * 0.55))
    small = img.resize((cols, rows), Image.LANCZOS)
    # 合成到浅色底（模拟棋盘）
    print(f"== {os.path.basename(path)}  {w}x{h} ==")
    for y in range(rows):
        line = []
        for x in range(cols):
            r, g, b, a = small.getpixel((x, y))
            a = a / 255.0
            bg = (222, 213, 203) if (x // 4 + y // 3) % 2 == 0 else (205, 196, 187)
            px = (int(r * a + bg[0] * (1 - a)),
                  int(g * a + bg[1] * (1 - a)),
                  int(b * a + bg[2] * (1 - a)))
            line.append(classify(px))
        print("".join(line))
    print()


def sample(path, points):
    img = Image.open(path).convert("RGBA")
    print(f"== sample {os.path.basename(path)} ==")
    for name, (x, y) in points:
        print(f"  {name:14s} ({x:3d},{y:3d}) = {img.getpixel((x, y))[:3]}")


if __name__ == "__main__":
    qa = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "qa")
    names = sys.argv[1:] or ["1_default.png", "2_all.png"]
    for n in names:
        p = os.path.join(qa, n)
        if os.path.exists(p):
            view(p)
