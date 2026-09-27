# -*- coding: utf-8 -*-
"""BongoCatPet 主入口：窗口管理 + 事件循环 + 合成呈现。"""
import math
import os
import subprocess
import sys
import time

import pygame

import config
import winutil
from inputs import GlobalInput
from cat import (DW, DH, MW, MH, SS, CatAnim, draw_cat, cat_hit,
                 load_face_surface)
from deco import draw_background, draw_handheld
from ui import (PANEL_W, CATEGORIES, LABELS, DressPanel, CtxMenu,
                InputModal, get_font, star4_pts, fit_text,
                FACE_DEFAULT, FACE_UPLOAD)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class Pet:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(config.APP_NAME)
        try:
            pygame.key.start_text_input()   # 启用文本输入事件（含中文输入法）
        except Exception:
            pass
        self.cfg = config.load_config()
        self.clock = pygame.time.Clock()
        self.screen = None

        self.win = winutil.LayeredWin()
        self.inputs = GlobalInput()
        self.anim = CatAnim(self.cfg.get("idle_yawn_seconds", 20.0))
        self.panel = DressPanel()
        self.menu = CtxMenu()
        self.modal = None
        self.toast = None          # (text, until_time)

        self.kb_left = 0
        self.kb_right = 0
        self.mouse_down = 0
        self.taps = 0            # 本次运行的敲击计数（每次启动/开机后从 0 开始）

        # 纹身：读 tattoos.json（由“纹身工坊”窗口写入，这里轮询应用）
        self.cfg["tattoos"] = config.load_tattoos()
        self._tattoos_last = config.tattoos_mtime_ns() or 0
        self._frame_no = 0
        self._editor_proc = None

        self.wx = self.wy = None   # 窗口屏幕坐标
        self.dragging = False
        self.drag_off = (0, 0)

        self.cat_canvas = pygame.Surface((MW, MH), pygame.SRCALPHA)
        self.master = pygame.Surface((MW, MH), pygame.SRCALPHA)

        self._load_face()
        self.rebuild()
        # 全局监听线程常驻；启用/停用由配置在 drain_global 中门控
        self.inputs.start(True, True)

    # ------------------------------------------------------------ 基础
    def _load_face(self):
        path = config.face_abs_path(self.cfg.get("face", ""))
        self.cfg["_face_surf"] = load_face_surface(path) if path else None

    def _load_face_surf(self, path):
        self.cfg["_face_surf"] = load_face_surface(path) if path else None

    def rebuild(self):
        """(重新)创建窗口：缩放或面板开关变化时调用。"""
        # 记住旧位置
        if self.wx is not None:
            old = self.win.rect()
            self.wx, self.wy = old[0], old[1]

        s = clamp(float(self.cfg.get("scale", 1.0)), 0.7, 1.5)
        self.cfg["scale"] = s
        self.scale = s
        self.scene_w = int(round(DW * s))
        self.scene_h = int(round(DH * s))
        self.panel_on = bool(self.cfg.get("panel_open", False))
        self.frame_w = self.scene_w + (PANEL_W if self.panel_on else 0)
        self.frame_h = self.scene_h
        self.px_per_design = s

        self.screen = pygame.display.set_mode((self.frame_w, self.frame_h),
                                              pygame.NOFRAME)
        hwnd = pygame.display.get_wm_info().get("window")
        self.win.attach(hwnd)
        self.win.set_size(self.frame_w, self.frame_h)

        vx, vy, vw, vh = winutil.virtual_screen()
        if self.wx is None:
            saved = self.cfg.get("window_pos")
            if saved:
                self.wx, self.wy = int(saved[0]), int(saved[1])
            else:
                self.wx = vx + vw - self.frame_w - 60
                self.wy = vy + vh - self.frame_h - 90
        self.wx, self.wy = self.win.place_in_screen(
            self.wx, self.wy, self.frame_w, self.frame_h)
        if self.modal:
            self.modal.resize(self.frame_w, self.frame_h)
        pygame.display.flip()

    def set_toast(self, text, secs=2.4):
        self.toast = (text, time.time() + secs)

    def shutdown(self):
        """保存配置并释放资源（正常退出 / Ctrl+C 中断都走这里）。"""
        try:
            if self.wx is not None:
                self.cfg["window_pos"] = [self.wx, self.wy]
            config.save_config(self.cfg)
        except Exception:
            pass
        try:
            self.inputs.stop()
        except Exception:
            pass
        try:
            self.win.detach()
        except Exception:
            pass
        try:
            pygame.quit()
        except Exception:
            pass

    def quit(self):
        self.shutdown()
        sys.exit(0)

    # ------------------------------------------------------------ 菜单内容
    def _menu_root(self):
        def zoom_items():
            return [
                {"type": "act", "label": "放大  +10%", "fn": lambda: self._zoom(0.1)},
                {"type": "act", "label": "缩小  -10%", "fn": lambda: self._zoom(-0.1)},
                {"type": "act", "label": "还原 100%", "fn": lambda: self._zoom(0, True)},
            ]

        def listen_items():
            return [
                {"type": "chk", "label": "键盘监听", "checked": lambda: self.cfg["keyboard"],
                 "fn": lambda: self._toggle_key()},
                {"type": "chk", "label": "鼠标监听", "checked": lambda: self.cfg["mouse"],
                 "fn": lambda: self._toggle_mouse()},
            ]

        rows = [
            {"type": "chk", "label": "换装面板", "checked": lambda: self.cfg["panel_open"],
             "fn": self._toggle_panel},
            {"type": "act", "label": "纹身工坊…", "fn": self._open_tattoo_editor},
            {"type": "sub", "label": "穿搭方案", "children": self._outfit_menu},
            {"type": "sub", "label": "监听设置", "children": listen_items},
            {"type": "act", "label": "上传照片…", "fn": self._upload_face},
            {"type": "act", "label": "恢复默认", "fn": self._restore_default},
            {"type": "sub", "label": "缩放调节", "children": zoom_items},
            {"type": "chk", "label": "开机自启", "checked": config.get_autostart,
             "fn": self._toggle_autostart},
            {"type": "sep", "label": "———"},
            {"type": "act", "label": "退出", "fn": self.quit},
        ]
        return rows

    def _outfit_menu(self):
        names = config.list_outfits()

        def fmt(n):
            """方案名后附上保存时的缩放与头像标记。"""
            rec = config.load_outfit_data(n)
            if not rec:
                return n
            parts = []
            if rec["scale"] is not None:
                parts.append(f"缩放 {int(round(rec['scale'] * 100))}%")
            if rec["face"]:
                parts.append("自定义头")
            elif rec["face"] == "":
                parts.append("原版头")
            return f"{n} · " + " · ".join(parts) if parts else n

        rows = [{"type": "act", "label": "保存当前为方案…", "fn": self._ask_save_outfit}]
        if names:
            rows.append({"type": "sep", "label": "———"})
            rows.append({"type": "title", "label": "— 加载 —"})
            for n in names:
                rows.append({"type": "act", "label": fmt(n),
                             "fn": lambda n=n: self._load_outfit(n)})
            rows.append({"type": "sep", "label": "———"})
            rows.append({"type": "title", "label": "— 删除 —"})
            for n in names:
                rows.append({"type": "act", "label": "删除  " + fmt(n),
                             "fn": lambda n=n: self._del_outfit(n)})
        return rows

    # ------------------------------------------------------------ 菜单动作
    def _toggle_panel(self):
        self.cfg["panel_open"] = not self.cfg["panel_open"]
        config.save_config(self.cfg)
        self.rebuild()

    # ------------------------------------------------------------ 纹身
    def poll_tattoos(self):
        """轮询 tattoos.json，纹身工坊改动后应用（约每 0.25 秒查一次 mtime）。"""
        self._frame_no += 1
        if self._frame_no % 15 != 0:
            return
        mtime = config.tattoos_mtime_ns()
        if mtime is not None and mtime != self._tattoos_last:
            self._tattoos_last = mtime
            self.cfg["tattoos"] = config.load_tattoos()

    def _open_tattoo_editor(self):
        proc = self._editor_proc
        if proc is not None and proc.poll() is None:
            self.set_toast("纹身工坊已经打开")
            return
        try:
            if config.is_frozen():
                cmd = [sys.executable, "--tattoo-editor"]
            else:
                here = os.path.dirname(os.path.abspath(__file__))
                cmd = [sys.executable, os.path.join(here, "tattoo_editor.py")]
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            self._editor_proc = subprocess.Popen(cmd, cwd=config.app_dir(),
                                                 creationflags=flags)
            self.set_toast("已打开纹身工坊（新窗口）")
        except Exception as e:
            self.set_toast(f"打开失败：{e}")

    def _toggle_key(self):
        self.cfg["keyboard"] = not self.cfg["keyboard"]
        if not self.cfg["keyboard"]:
            self.kb_left = self.kb_right = 0
        config.save_config(self.cfg)

    def _toggle_mouse(self):
        self.cfg["mouse"] = not self.cfg["mouse"]
        if not self.cfg["mouse"]:
            self.mouse_down = 0
            self.dragging = False
        config.save_config(self.cfg)

    def _toggle_autostart(self):
        on = not config.get_autostart()
        if config.set_autostart(on):
            self.set_toast("已开启开机自启" if on else "已关闭开机自启")
        else:
            self.set_toast("仅支持 Windows 开机自启")

    def _zoom(self, delta, reset=False):
        if reset:
            self.cfg["scale"] = 1.0
        else:
            self.cfg["scale"] = clamp(round(self.cfg["scale"] + delta, 2),
                                      0.7, 1.5)
        config.save_config(self.cfg)
        self.rebuild()

    def _restore_default(self):
        self.cfg["decorations"] = []
        self.cfg["face"] = ""
        self.cfg["scale"] = 1.0
        self.cfg["keyboard"] = True
        self.cfg["mouse"] = True
        self.cfg["panel_open"] = False
        self.cfg["tattoos"] = {}
        config.save_config(self.cfg)
        config.save_tattoos({})
        self._tattoos_last = 0
        self._load_face()
        self.rebuild()
        self.set_toast("已恢复默认外观（含纹身）")

    def _load_outfit(self, name):
        rec = config.load_outfit_data(name)
        if not rec:
            self.set_toast("未找到该方案")
            return
        self.cfg["decorations"] = rec["decorations"]
        if rec["scale"] is not None:
            self.cfg["scale"] = rec["scale"]
        if rec["face"] is not None:
            # '' = 原版默认猫头；照片路径 = 该方案保存的自定义头像
            self.cfg["face"] = rec["face"]
            self._load_face()
        config.save_config(self.cfg)
        if rec["scale"] is not None:
            self.rebuild()          # 缩放变化需要重建窗口
        tip = f"已加载「{name}」"
        notes = []
        if rec["scale"] is not None:
            notes.append(f"缩放 {int(round(rec['scale'] * 100))}%")
        if rec["face"] is not None:
            notes.append("自定义头像" if rec["face"] else "原版猫头")
        if notes:
            tip += "（" + " · ".join(notes) + "）"
        self.set_toast(tip)

    def _del_outfit(self, name):
        config.delete_outfit(name)
        self.set_toast(f"已删除「{name}」")

    def _ask_save_outfit(self):
        self.modal = InputModal("保存穿搭方案", "输入方案名称：")
        self.modal.resize(self.frame_w, self.frame_h)

    def _save_outfit_text(self, text):
        # 把“当时的缩放 + 头像(默认猫头或自定义照片)”一起写进方案
        name = config.save_outfit(text, self.cfg["decorations"],
                                  scale=self.cfg.get("scale", 1.0),
                                  face=self.cfg.get("face", ""))
        self.set_toast(f"方案已保存：{name}")

    def _upload_face(self):
        try:
            import tkinter as tk
            from tkinter import filedialog
        except Exception:
            self.set_toast("缺少 tkinter，无法打开文件对话框")
            return
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askopenfilename(
            title="选择一张照片作为猫脸",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.webp *.gif"),
                       ("所有文件", "*.*")])
        root.destroy()
        if not path:
            return
        try:
            from PIL import Image
            img = Image.open(path)
            img.load()
            self.cfg["face"] = config.save_face_image(img)
            config.save_config(self.cfg)
            self._load_face_surf(config.face_abs_path(self.cfg["face"]))
            self.set_toast("猫脸已更新（右键-恢复默认可还原）")
        except Exception as e:
            self.set_toast(f"图片读取失败: {e}")

    # ------------------------------------------------------------ 全局输入
    def drain_global(self):
        kb, mouse = self.cfg.get("keyboard", True), self.cfg.get("mouse", True)
        for ev in self.inputs.poll():
            kind = ev[0]
            if kind == "key":
                side, down = ev[1], ev[2]
                if not kb:
                    continue
                if down and side:
                    self.taps += 1
                if side == "left":
                    self.kb_left = max(0, self.kb_left + (1 if down else -1))
                elif side == "right":
                    self.kb_right = max(0, self.kb_right + (1 if down else -1))
                elif side == "both":
                    self.kb_left = max(0, self.kb_left + (1 if down else -1))
                    self.kb_right = max(0, self.kb_right + (1 if down else -1))
                self.anim.poke()
            elif kind == "mouse":
                name, pressed = ev[1], ev[2]
                if not mouse or pressed is None:
                    continue
                self.mouse_down = max(0, self.mouse_down + (1 if pressed else -1))
                if pressed:
                    self.taps += 1
                    self.anim.poke()
                elif self.mouse_down <= 0:
                    # 按钮在窗口外松开也能结束拖拽（靠全局监听兜底）
                    self.dragging = False

    def look_dir(self):
        """眼球注视方向（设计单位偏移）。"""
        if not self.cfg.get("mouse", True):
            return (0.0, 0.0)
        cur = winutil.cursor_pos()
        if cur is None:
            return (0.0, 0.0)
        hx = (self.wx or 0) + 150 * self.scale
        hy = (self.wy or 0) + 110 * self.scale
        dx, dy = cur[0] - hx, cur[1] - hy
        dist = math.hypot(dx, dy)
        if dist < 2:
            return (0.0, 0.0)
        off = min(6.0, dist * 0.35)
        return (dx / dist * off, dy / dist * off)

    # ------------------------------------------------------------ 敲击计数器
    def draw_counter(self, frame):
        """桌宠正下方的“本次运行敲击次数”（每次启动都从 0 开始）。"""
        label = f"敲击 {self.taps:,}"
        f = get_font(15)
        ts = f.render(label, True, (255, 255, 255))
        pad_x, h = 14, 26
        w = ts.get_width() + pad_x * 2
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (self.scene_w // 2, self.scene_h - h // 2 - 10)
        pygame.draw.rect(frame, (30, 27, 46, 205), rect, border_radius=h // 2)
        pygame.draw.rect(frame, (255, 255, 255, 70), rect, width=1,
                         border_radius=h // 2)
        # 小星花点缀在计数前
        pygame.draw.polygon(frame, (255, 208, 100),
                            star4_pts(rect.x + 13, rect.centery, 6))
        frame.blit(ts, (rect.x + pad_x + 9,
                        rect.centery - ts.get_height() // 2))

    # ------------------------------------------------------------ 事件
    def on_event(self, e):
        if e.type == pygame.QUIT:
            self.quit()

        elif e.type == pygame.MOUSEWHEEL:
            if self.menu.open_:
                self.menu.wheel(e.y)

        elif e.type == pygame.MOUSEBUTTONDOWN:
            pos = e.pos
            b = e.button
            if self.modal is not None:
                self.modal.click(pos)
                if self.modal.done:
                    kind, text = self.modal.done
                    self.modal = None
                    if kind == "ok":
                        self._save_outfit_text(text or "")
                return
            if self.menu.open_:
                if b == 1:
                    res = self.menu.click(pos)
                    if res == "outside":
                        self.menu.close()
                    elif res[0] == "run":
                        item = res[1]
                        fn = item.get("fn")
                        if fn:
                            fn()
                        if item["type"] == "act" or item["label"] == "换装面板":
                            self.menu.close()
                elif b == 3:
                    self.menu.close()
                return
            # 无菜单/弹窗
            if self.panel_on and pos[0] >= self.scene_w:
                if self.panel.close_rect and self.panel.close_rect.collidepoint(pos):
                    self._toggle_panel()
                    return
                cid = self.panel.cell_id_at(pos)
                if cid:
                    self._on_panel_cell(cid)
                    return
            if b == 1:
                # 在猫身上 → 开始拖拽
                dx, dy = pos[0] / self.px_per_design, pos[1] / self.px_per_design
                if pos[0] < self.scene_w and cat_hit(dx, dy, self.cfg):
                    cur = winutil.cursor_pos() or (self.wx or 0, self.wy or 0)
                    self.dragging = True
                    self.drag_off = (cur[0] - (self.wx or 0),
                                     cur[1] - (self.wy or 0))
            elif b == 3:
                # 右键小猫/窗口任意处 → 打开菜单
                dx, dy = pos[0] / self.px_per_design, pos[1] / self.px_per_design
                if pos[0] < self.scene_w and cat_hit(dx, dy, self.cfg):
                    self.menu.open(self._menu_root(), pos[0], pos[1],
                                   self.frame_w, self.frame_h)

        elif e.type == pygame.MOUSEBUTTONUP:
            if e.button == 1:
                self.dragging = False

        elif e.type == pygame.MOUSEMOTION:
            pass  # 拖拽由主循环逐帧用全局光标位置驱动，避免拖出窗口丢事件

        elif e.type == pygame.KEYDOWN:
            if self.modal is not None:
                if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.modal.key(enter=True)
                elif e.key == pygame.K_ESCAPE:
                    self.modal.key(esc=True)
                elif e.key == pygame.K_BACKSPACE:
                    self.modal.key(backspace=True)
            elif self.menu.open_ and e.key == pygame.K_ESCAPE:
                self.menu.close()
            if e.key == pygame.K_ESCAPE:
                self.dragging = False

        elif e.type == pygame.TEXTINPUT:
            if self.modal is not None:
                self.modal.key(unicode_char=e.text)

    def toggle_decor(self, cid):
        decos = self.cfg["decorations"]
        if cid in decos:
            decos.remove(cid)
        else:
            decos.append(cid)
        config.save_config(self.cfg)

    # ------------------------------------------------------------ 面板格子
    def _on_panel_cell(self, cid):
        """换装面板格子：普通装饰开/关；两个头像格子特殊处理。"""
        if cid == FACE_UPLOAD:
            self._upload_face()
        elif cid == FACE_DEFAULT:
            if self.cfg.get("face"):
                self.cfg["face"] = ""
                self._load_face()
                config.save_config(self.cfg)
                self.set_toast("已换回默认猫头")
        else:
            self.toggle_decor(cid)

    # ------------------------------------------------------------ 合成
    def render_frame(self, t):
        look = self.look_dir()
        self.master.fill((0, 0, 0, 0))
        draw_background(self.master, t, self.cfg)

        # 猫画布 + 呼吸缩放（以底部为锚点）
        self.cat_canvas.fill((0, 0, 0, 0))
        draw_cat(self.cat_canvas, self.cfg, self.anim, look)
        sq = self.anim.breath
        w, h = self.cat_canvas.get_size()
        sh = max(2, int(round(h * sq)))
        scaled = pygame.transform.smoothscale(self.cat_canvas, (w, sh))
        self.master.blit(scaled, (0, h - sh))

        draw_handheld(self.master, t, self.cfg)

        # 主场景缩放到窗口像素
        scene = pygame.transform.smoothscale(
            self.master, (self.scene_w, self.scene_h))
        alpha = self.win.ok
        if alpha:
            frame = pygame.Surface((self.frame_w, self.frame_h), pygame.SRCALPHA)
        else:
            frame = pygame.Surface((self.frame_w, self.frame_h))
            frame.fill((34, 32, 52))
        frame.blit(scene, (0, 0))

        # 敲击计数器（桌宠下方）
        self.draw_counter(frame)

        # 面板
        if self.panel_on:
            self.panel.draw(frame, self.cfg, self.frame_w, self.frame_h)

        # 菜单 / 弹窗 / 提示
        if self.menu.open_:
            mp = pygame.mouse.get_pos()
            self.menu.draw(frame, mp)
        if self.modal is not None:
            self.modal.draw(frame, t)
        if self.toast:
            text, until = self.toast
            if time.time() < until:
                # 窗口被缩小时自适应字号/截断，避免提示条超出窗口
                ts, _ = fit_text(text, 14, max(60, self.frame_w - 40),
                                 (255, 255, 255))
                pad = 12
                w0 = min(self.frame_w - 8, ts.get_width() + pad * 2)
                h0 = ts.get_height() + 10
                rect = (self.frame_w // 2 - w0 // 2, self.frame_h - h0 - 62,
                        w0, h0)
                pygame.draw.rect(frame, (30, 27, 46, 235), rect,
                                 border_radius=10)
                pygame.draw.rect(frame, (255, 255, 255, 60), rect, width=1,
                                 border_radius=10)
                frame.blit(ts, (rect[0] + max(4, (w0 - ts.get_width()) // 2),
                                rect[1] + 5))
            else:
                self.toast = None
        return frame

    # ------------------------------------------------------------ 主循环
    def run(self):
        running = True
        try:
            while running:
                dt = self.clock.tick(60) / 1000.0
                for e in pygame.event.get():
                    self.on_event(e)
                    if e.type == pygame.QUIT:
                        running = False
                if not running:
                    break
                self.drain_global()
                self.poll_tattoos()

                # 拖拽：逐帧跟随全局光标（即使拖出窗口仍能继续移动）
                if self.dragging:
                    cur = winutil.cursor_pos()
                    if cur:
                        self.wx = cur[0] - self.drag_off[0]
                        self.wy = cur[1] - self.drag_off[1]
                        self.wx, self.wy = self.win.place_in_screen(
                            self.wx, self.wy, self.frame_w, self.frame_h)

                self.anim.left = self.kb_left > 0
                self.anim.right = self.kb_right > 0
                self.anim.mouse = self.mouse_down > 0
                self.anim.update(dt)

                frame = self.render_frame(time.time())
                ok = self.win.present(frame)
                if not ok:
                    pygame.display.flip()
        except KeyboardInterrupt:
            # 控制台里按 Ctrl+C 结束：不打印堆栈，走干净退出流程
            print("\n已退出桌宠（Ctrl+C）")
        finally:
            self.shutdown()


def main():
    if not winutil.IS_WINDOWS:
        print("提示：完整透明窗口仅支持 Windows；其他平台为普通无边框窗口。")
    Pet().run()


if __name__ == "__main__":
    # “纹身工坊”是独立进程/新窗口：由桌宠以 --tattoo-editor 参数拉起
    if "--tattoo-editor" in sys.argv:
        from tattoo_editor import main as editor_main
        editor_main()
    else:
        main()
