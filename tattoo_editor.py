# -*- coding: utf-8 -*-
"""
纹身工坊 —— 独立的“创建角色”式窗口（子进程运行，pygame 单窗口）。

布局（类游戏捏脸界面）：
    左栏：可纹身部位列表（额头/左颊/右颊/胸口/腹部/左爪/右爪，显示当前纹样与大小）
    中央：带底座的猫咪实时预览（改动即时可见），高亮当前部位
    右栏：纹身样式画廊（9 款矢量样式 + “上传图片…”自定义图）
          下方 大小滑块（50%~200%，可拖拽/滚轮/±按钮/一键回 100%）
          再下方 清除该部位 / 全部清除

所有改动即时写入 tattoos.json，桌宠主进程轮询后立即应用。
运行方式：由桌宠右键菜单「纹身工坊…」拉起；也可单独：
    python tattoo_editor.py
"""
import os
import sys

import pygame

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config  # noqa: E402
from cat import (CatAnim, DW, DH, MW, MH, PAW_CY, PAW_L_CX,  # noqa: E402
                 PAW_R_CX, draw_cat)
from tattoos import (BODY_BOXES, PAW_HALF, REGIONS, REGION_NAMES,  # noqa: E402
                     STYLE_NAMES, STYLES, clamp_scale, clean_mapping,
                     clear_caches, custom_image, style_sprite)
from ui import get_font, reset_font_cache  # noqa: E402

W, H = 980, 640

BG = (24, 22, 34)
PANEL = (34, 31, 50)
FG = (240, 240, 246)
DIM = (162, 158, 182)
GOLD = (255, 208, 100)
ACCENT = (120, 150, 255)
ACCENT2 = (255, 120, 170)

CUSTOM_TILE = "__custom_image__"     # 画廊里的“上传图片…”格子

SIZE_LO, SIZE_HI = 0.5, 2.0          # 滑块范围（百分比 50% ~ 200%）

# 左侧布局
LX, LW = 20, 210
# 右侧布局
RX, RW = W - 232, 212
# 中央预览
PV_W = 280
PV_X = LX + LW + 24


def rounded(surface, color, rect, radius):
    pygame.draw.rect(surface, color, rect, border_radius=radius)


def text(surface, s, size, color, pos, center=False):
    t = get_font(size).render(s, True, color)
    r = t.get_rect()
    if center:
        r.center = pos
    else:
        r.topleft = pos
    surface.blit(t, r)
    return r


class Editor:
    def __init__(self):
        pygame.init()
        # 若本进程之前跑过 pygame（例如同进程内启动过桌宠），
        # 旧的 Font / 贴图缓存已随 pygame.quit() 失效，必须先清掉
        reset_font_cache()
        clear_caches()
        pygame.display.set_caption("纹身工坊")
        self.screen = pygame.display.set_mode((W, H))
        self.clock = pygame.time.Clock()

        self.mapping = clean_mapping(config.load_tattoos())
        self.region = REGIONS[0][0]          # 当前选中的部位
        self.size_pending = 1.0              # 还没有纹身时，滑块记住的“下次大小”
        self.drag_size = False
        self.toast = ""
        self.toast_t = 0.0

        # 预览相关
        self.pv_scale = PV_W / DW
        self.pv_h = int(round(DH * self.pv_scale))
        self.pv_pos = (PV_X, (H - self.pv_h) // 2 - 10)
        self.anim = CatAnim(idle_seconds=3600)

        self.region_rows = []     # (rect, id)
        self.style_cells = []     # (rect, id)
        self.clear_btn = None
        self.clear_all_btn = None
        self.slider_track = None
        self.size_minus = None
        self.size_plus = None
        self.size_reset = None

    # ------------------------------------------------------------ 数据
    def save(self):
        config.save_tattoos(self.mapping)

    def current_entry(self):
        return self.mapping.get(self.region)

    def current_scale(self):
        e = self.current_entry()
        return clamp_scale(e["scale"]) if e else self.size_pending

    def set_scale(self, value, save=True):
        v = clamp_scale(value)
        e = self.current_entry()
        if e:
            e["scale"] = v
            if save:
                self.save()
        else:
            self.size_pending = v
        return v

    def flash(self, msg):
        self.toast = msg
        self.toast_t = 2.4

    # ------------------------------------------------------------ 操作
    def apply_style(self, style_id):
        self.mapping[self.region] = {"type": "style", "ref": style_id,
                                     "scale": self.current_scale()}
        self.save()
        self.flash(f"已纹上 {STYLE_NAMES[style_id]}")

    def apply_custom_image(self, path):
        """从本地图片文件生成自定义纹身并应用（也供测试直接调用）。"""
        try:
            from PIL import Image
            img = Image.open(path)
            img.load()
            ref = config.save_tattoo_image(img)
        except Exception as e:
            self.flash(f"图片读取失败：{e}")
            return False
        clear_caches()
        self.mapping[self.region] = {"type": "image", "ref": ref,
                                     "scale": self.current_scale()}
        self.save()
        self.flash("已应用自定义纹身图")
        return True

    def pick_image(self):
        try:
            import tkinter as tk
            from tkinter import filedialog
        except Exception:
            self.flash("缺少 tkinter，无法打开文件对话框")
            return
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askopenfilename(
            title="选择纹身图片（建议透明 PNG）",
            initialdir=str(config.tattoos_dir()),
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.webp *.gif"),
                       ("所有文件", "*.*")])
        root.destroy()
        if path:
            self.apply_custom_image(path)

    def clear_region(self):
        if self.region in self.mapping:
            self.size_pending = self.current_scale()
            self.mapping.pop(self.region, None)
            self.save()
            self.flash("已清除该部位")

    def clear_all(self):
        self.mapping = {}
        self.save()
        self.flash("已清除全部纹身")

    # ------------------------------------------------------------ 布局几何
    def layout(self):
        # 左栏：部位列表
        self.region_rows = []
        y = 78
        for rid, rname in REGIONS:
            rect = pygame.Rect(LX, y, LW, 52)
            self.region_rows.append((rect, rid))
            y += 60
        # 右栏：样式卡片(两列) + 自定义图片格子
        self.style_cells = []
        gw, gh, gap = 100, 70, 6
        x0, y0 = RX, 76
        tiles = [(sid, sname) for sid, sname in STYLES]
        tiles.append((CUSTOM_TILE, "上传图片…"))
        for i, (sid, sname) in enumerate(tiles):
            col, row = i % 2, i // 2
            rect = pygame.Rect(x0 + col * (gw + gap), y0 + row * (gh + gap),
                               gw, gh)
            self.style_cells.append((rect, sid))
        # 大小滑块
        self.size_minus = pygame.Rect(RX, 474, 26, 26)
        self.slider_track = pygame.Rect(RX + 32, 482, 108, 8)
        self.size_plus = pygame.Rect(RX + 146, 474, 26, 26)
        self.size_reset = pygame.Rect(RX + 178, 474, 34, 26)
        # 底部按钮
        self.clear_btn = pygame.Rect(RX, 514, RW, 32)
        self.clear_all_btn = pygame.Rect(RX, 552, RW, 32)

    # ------------------------------------------------------------ 滑块换算
    def _t_from_scale(self, scale):
        s = (clamp_scale(scale) - SIZE_LO) / (SIZE_HI - SIZE_LO)
        return min(1.0, max(0.0, s))

    def _scale_from_x(self, x):
        t = (x - self.slider_track.x) / max(1, self.slider_track.w)
        t = min(1.0, max(0.0, t))
        return round(SIZE_LO + t * (SIZE_HI - SIZE_LO), 2)

    # ------------------------------------------------------------ 绘制
    def draw(self, dt, t):
        scr = self.screen
        scr.fill(BG)

        # 中央背景光晕 + 底座（角色创建氛围）
        cx = PV_X + PV_W // 2
        glow_c = pygame.Rect(0, 0, 470, 470)
        glow_c.center = (cx, self.pv_pos[1] + self.pv_h // 2 + 30)
        pygame.draw.ellipse(scr, (52, 44, 84), glow_c)
        pygame.draw.ellipse(scr, (72, 62, 112), glow_c.inflate(-90, -90))
        base = pygame.Rect(0, 0, 360, 56)
        base.center = (cx, self.pv_pos[1] + self.pv_h - 8)
        pygame.draw.ellipse(scr, (0, 0, 0, 90), base)
        pygame.draw.ellipse(scr, (150, 120, 200), base.inflate(-10, -10), 2)

        # 中央：猫咪实时预览
        preview = self.render_cat(dt)
        scr.blit(preview, self.pv_pos)

        # 标题
        text(scr, "纹身工坊", 24, GOLD, (W // 2, 26), center=True)
        text(scr, "选择部位 · 样式或自定义图片 · 拖动滑块调大小 · 即时生效", 13, DIM,
             (W // 2, 52), center=True)

        self.draw_left()
        self.draw_right()

        # 底部提示条
        tip = f"{REGION_NAMES[self.region]}：" + self.region_summary()
        if self.toast and self.toast_t > 0:
            tip = self.toast
        text(scr, tip, 15, ACCENT2, (26, H - 30))
        text(scr, "关闭本窗口后回到桌宠查看效果 · 右键小猫可再次打开", 13, DIM,
             (W - 24, H - 30), center=False)

        if self.toast:
            self.toast_t -= dt

    def region_summary(self):
        e = self.current_entry()
        if not e:
            return "未纹身"
        name = "自定义图" if e["type"] == "image" else STYLE_NAMES.get(e["ref"], "?")
        return f"{name} · {int(round(clamp_scale(e['scale']) * 100))}%"

    def render_cat(self, dt):
        cfg = {"decorations": [], "_face_surf": None, "tattoos": self.mapping}
        canvas = pygame.Surface((MW, MH), pygame.SRCALPHA)
        self.anim.update(dt)
        draw_cat(canvas, cfg, self.anim, (0, 0))
        pv = pygame.transform.smoothscale(
            canvas, (PV_W, int(round(DH * PV_W / DW))))
        # 高亮当前部位
        box = self.region_design_box(self.region)
        if box:
            rect = pygame.Rect(box[0] * self.pv_scale, box[1] * self.pv_scale,
                               box[2] * self.pv_scale, box[3] * self.pv_scale)
            rect.inflate_ip(6, 6)
            pygame.draw.rect(pv, (255, 120, 170, 130), rect, width=2,
                             border_radius=8)
        return pv

    def region_design_box(self, region):
        if region in BODY_BOXES:
            return BODY_BOXES[region]
        if region in ("paw_l", "paw_r"):
            cx = PAW_L_CX if region == "paw_l" else PAW_R_CX
            cy0 = PAW_CY
            hw, hh = PAW_HALF
            return (cx - hw - 6, cy0 - hh - 4, hw * 2 + 12, hh * 2 + 10)
        return None

    def draw_left(self):
        rounded(self.screen, PANEL, (LX - 8, 54, LW + 16, H - 100), 14)
        text(self.screen, "部 位", 16, GOLD, (LX + 8, 62))
        for rect, rid in self.region_rows:
            on = rid == self.region
            col = (70, 62, 104) if on else (44, 41, 64)
            rounded(self.screen, col, rect, 10)
            if on:
                pygame.draw.rect(self.screen, ACCENT2, rect, width=2,
                                 border_radius=10)
            text(self.screen, REGION_NAMES[rid], 16,
                 FG if on else DIM, (rect.x + 14, rect.y + 7))
            e = self.mapping.get(rid)
            if e:
                name = ("自定义图" if e["type"] == "image"
                        else STYLE_NAMES.get(e["ref"], "?"))
                sub = f"{name} · {int(round(clamp_scale(e['scale']) * 100))}%"
                scol = GOLD
            else:
                sub, scol = "未纹身", DIM
            text(self.screen, sub, 12, scol, (rect.x + 14, rect.y + 30))

    def draw_right(self):
        rounded(self.screen, PANEL, (RX - 10, 54, RW + 20, H - 100), 14)
        text(self.screen, "纹身样式", 16, GOLD, (RX + 2, 62))
        entry = self.current_entry()
        cur_style = entry["ref"] if (entry and entry["type"] == "style") else None
        is_image = bool(entry and entry["type"] == "image")

        for rect, sid in self.style_cells:
            on = is_image if sid == CUSTOM_TILE else (cur_style == sid)
            col = (70, 62, 104) if on else (44, 41, 64)
            rounded(self.screen, col, rect, 10)
            if on:
                pygame.draw.rect(self.screen, GOLD, rect, width=2,
                                 border_radius=10)
            if sid == CUSTOM_TILE:
                thumb = None
                if is_image and entry:
                    img = custom_image(entry["ref"])
                    if img is not None:
                        thumb = pygame.transform.smoothscale(img, (40, 40))
                thr = pygame.Rect(rect.centerx - 20, rect.y + 10, 40, 40)
                if thumb is not None:
                    self.screen.blit(thumb, thr)
                else:   # 虚线占位 + 加号
                    pygame.draw.rect(self.screen, DIM, thr, width=1,
                                     border_radius=6)
                    pygame.draw.line(self.screen, DIM,
                                     (thr.centerx - 8, thr.centery),
                                     (thr.centerx + 8, thr.centery), 2)
                    pygame.draw.line(self.screen, DIM,
                                     (thr.centerx, thr.centery - 8),
                                     (thr.centerx, thr.centery + 8), 2)
                text(self.screen, "上传图片…", 12, FG if on else DIM,
                     (rect.x + 6, rect.y + 52))
            else:
                sprite = style_sprite(sid)
                thumb = pygame.transform.smoothscale(sprite, (40, 40))
                self.screen.blit(thumb, (rect.centerx - 20, rect.y + 10))
                text(self.screen, STYLE_NAMES[sid], 13, FG,
                     (rect.x + 6, rect.y + 52))
                if sid == "succubus":
                    text(self.screen, "★", 11, ACCENT2, (rect.right - 14, rect.y + 2))

        # 大小滑块
        scale = self.current_scale()
        text(self.screen, "大小", 15, FG, (RX, 456))
        text(self.screen, f"{int(round(scale * 100))}%", 14, GOLD,
             (RX + 148, 457))
        for btn, label in ((self.size_minus, "−"), (self.size_plus, "+")):
            rounded(self.screen, (74, 68, 104), btn, 7)
            text(self.screen, label, 16, FG, btn.center, center=True)
        rounded(self.screen, (48, 44, 70), self.size_reset, 7)
        text(self.screen, "100", 12, DIM, self.size_reset.center, center=True)
        tr = self.slider_track
        rounded(self.screen, (50, 46, 72), tr, 4)
        kx = tr.x + int(self._t_from_scale(scale) * tr.w)
        if kx > tr.x + 2:
            rounded(self.screen, ACCENT,
                    (tr.x, tr.y, max(2, kx - tr.x), tr.h), 4)
        pygame.draw.circle(self.screen, GOLD, (kx, tr.centery), 9)
        pygame.draw.circle(self.screen, (30, 27, 46), (kx, tr.centery), 3)
        text(self.screen, "50%", 10, DIM, (tr.x, tr.bottom + 2))
        text(self.screen, "200%", 10, DIM, (tr.right - 22, tr.bottom + 2))

        # 底部按钮
        for btn, label, col in ((self.clear_btn, "清除该部位", (150, 60, 80)),
                                (self.clear_all_btn, "全部清除", (90, 84, 120))):
            rounded(self.screen, col, btn, 9)
            text(self.screen, label, 14, FG, (btn.x + 8, btn.y + 6))

    # ------------------------------------------------------------ 输入
    def on_click(self, pos):
        for rect, rid in self.region_rows:
            if rect.collidepoint(pos):
                self.region = rid
                return
        for rect, sid in self.style_cells:
            if rect.collidepoint(pos):
                if sid == CUSTOM_TILE:
                    self.pick_image()
                else:
                    self.apply_style(sid)
                return
        # 滑块与按钮
        if self.slider_track.inflate(10, 16).collidepoint(pos):
            self.drag_size = True
            self.set_scale(self._scale_from_x(pos[0]))
            return
        if self.size_minus.collidepoint(pos):
            self.set_scale(self.current_scale() - 0.05)
            return
        if self.size_plus.collidepoint(pos):
            self.set_scale(self.current_scale() + 0.05)
            return
        if self.size_reset.collidepoint(pos):
            self.set_scale(1.0)
            return
        if self.clear_btn.collidepoint(pos):
            self.clear_region()
            return
        if self.clear_all_btn.collidepoint(pos):
            self.clear_all()

    def on_wheel(self, dy, pos):
        """滚轮在右栏滑块区域时微调大小。"""
        if pos[0] >= RX - 10 and pos[1] > 450:
            self.set_scale(self.current_scale() + (0.05 if dy > 0 else -0.05))

    # ------------------------------------------------------------ 主循环
    def run(self):
        self.layout()
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    self.on_click(e.pos)
                elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                    self.drag_size = False
                elif e.type == pygame.MOUSEMOTION and self.drag_size:
                    self.set_scale(self._scale_from_x(e.pos[0]))
                elif e.type == pygame.MOUSEWHEEL:
                    self.on_wheel(e.y, pygame.mouse.get_pos())
            self.draw(dt, pygame.time.get_ticks() / 1000.0)
            pygame.display.flip()
        pygame.quit()


def main():
    Editor().run()


if __name__ == "__main__":
    main()
