# -*- coding: utf-8 -*-
"""开发用无头逻辑测试。不属于运行依赖。"""
import os
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

pygame.init()

import config  # noqa: E402
import inputs  # noqa: E402
import winutil  # noqa: E402

ok = True


def check(name, cond):
    global ok
    ok = ok and bool(cond)
    print(("PASS " if cond else "FAIL ") + name)


# --- 配置/方案（重定向到临时目录，避免污染项目目录）---
tmp = tempfile.mkdtemp(prefix="pet_test_")
config.CONFIG_PATH = os.path.join(tmp, "config.json")
config.OUTFITS_PATH = os.path.join(tmp, "outfits.json")
config.TATTOOS_PATH = os.path.join(tmp, "tattoos.json")
config.FACES_DIR = os.path.join(tmp, "faces")

cfg = config.load_config()
check("默认配置", cfg["scale"] == 1.0 and cfg["decorations"] == [])

cfg["decorations"] = ["bow", "crown", "x_bad"]
cfg["scale"] = 3.0
config.save_config(cfg)
cfg2 = config.load_config()
check("非法项被过滤", cfg2["decorations"] == ["bow", "crown"])
check("缩放被限制", 0.7 <= cfg2["scale"] <= 1.5)

name = config.save_outfit("周末少女风", ["bow", "rainbow", "guitar"])
check("保存方案", name in config.list_outfits())
check("读取方案", config.load_outfit(name) == ["bow", "rainbow", "guitar"])
config.save_outfit("周末少女风", ["bow"])   # 重名自动改名
check("重名自动加序号", len(config.list_outfits()) == 2)
config.delete_outfit(name)
check("删除方案", name not in config.list_outfits())

# 方案携带缩放倍率
n_sc = config.save_outfit("带缩放", ["bow"], scale=1.35)
d_sc = config.load_outfit_data(n_sc)
check("方案记录缩放", d_sc is not None and abs(d_sc["scale"] - 1.35) < 1e-6
      and d_sc["decorations"] == ["bow"])
n_big = config.save_outfit("超限", ["crown"], scale=9.0)
check("方案缩放钳制", abs(config.load_outfit_data(n_big)["scale"] - 1.5) < 1e-6)
check("旧式读取仍可用", config.load_outfit(n_sc) == ["bow"])
config.delete_outfit(n_sc)
config.delete_outfit(n_big)
check("无缩放老方案scale=None",
      config.load_outfit_data(config.save_outfit("老方案", []))["scale"] is None)

# 方案携带头像（自定义照片 / 原版默认头）
n_f1 = config.save_outfit("照片头", ["star"], face=os.path.join(tmp, "faces", "me.png"))
check("方案记录自定义头像",
      config.load_outfit_data(n_f1)["face"].endswith("me.png"))
n_f2 = config.save_outfit("原版头", ["star"], face="")
check("方案记录原版头", config.load_outfit_data(n_f2)["face"] == "")
n_f3 = config.save_outfit("无头字段", ["star"])     # 老格式：不带 face
check("老方案face=None", config.load_outfit_data(n_f3)["face"] is None)
for _n in (n_f1, n_f2, n_f3):
    config.delete_outfit(_n)

# 面板头像特殊项
from ui import FACE_DEFAULT, FACE_UPLOAD, LABELS  # noqa: E402
check("面板含头像两项", FACE_DEFAULT in LABELS and FACE_UPLOAD in LABELS)

# --- 按键映射（用真实的 pynput Key / KeyCode）---
from pynput import keyboard as _kb

check("左手键 a", inputs.classify_key(_kb.KeyCode.from_char("a")) == "left")
check("右手键 j", inputs.classify_key(_kb.KeyCode.from_char("j")) == "right")
check("空格双爪", inputs.classify_key(_kb.Key.space) == "both")
check("左Shift", inputs.classify_key(_kb.Key.shift_l) == "left")
check("回车", inputs.classify_key(_kb.Key.enter) == "right")
check("音量键忽略", inputs.classify_key(_kb.Key.media_volume_up) is None)

# --- 动画 ---
from cat import CatAnim  # noqa: E402

anim = CatAnim(idle_seconds=0.2)
anim.left = True
for _ in range(10):
    anim.update(0.05)
check("左爪按下动画", anim.paw_l > 0.5)
anim.left = False
for _ in range(30):
    anim.update(0.05)
check("松爪回弹", anim.paw_l < 0.2)
check("呼吸在1附近", 0.98 < anim.breath < 1.02)

anim2 = CatAnim(idle_seconds=5.0)
for _ in range(125):   # dt 内部会被钳到 0.05，共模拟约 6.25 秒
    anim2.update(0.1)
check("长时间空闲会打哈欠", anim2.yawn_t >= 0 and anim2.mouth > 0.3)
anim2.poke()
anim2.update(0.02)
check("poke 打断哈欠", anim2.yawn_t < 0)

# --- 照片脸 ---
from cat import load_face_surface  # noqa: E402

from PIL import Image  # noqa: E402
fpath = os.path.join(tmp, "face.png")
Image.new("RGB", (200, 200), (200, 120, 90)).save(fpath)
surf = load_face_surface(fpath)
check("照片脸生成 Surface", surf is not None and surf.get_size() == (220, 204))
check("无路径返回None", load_face_surface("") is None)

# --- 字体与 UI ---
from ui import get_font, CtxMenu, InputModal, fit_text, fit_text_tail  # noqa: E402

f15 = get_font(15)
ts = f15.render("换装面板 / 键盘监听", True, (255, 255, 255))
check("中文字体渲染", ts.get_width() > 10)

menu = CtxMenu()
rows = [
    {"type": "chk", "label": "换装面板", "checked": lambda: True},
    {"type": "act", "label": "上传照片…"},
    {"type": "sub", "label": "穿搭方案", "children": lambda: [
        {"type": "act", "label": "保存当前为方案…"}]},
]
menu.open(rows, 10, 10, 300, 352)
r = menu.click((34, 34))
check("点击第一行返回run", r[0] == "run" and r[1]["label"] == "换装面板")
r2 = menu.click((300, 300))
check("点击外部关闭", r2 == "outside")
menu.close()
check("菜单已关闭", not menu.open_)

modal = InputModal("保存穿搭方案", "名称")
modal.resize(300, 352)
modal.key(unicode_char="星")
modal.key(backspace=True)
modal.key(unicode_char="夜")
modal.key(enter=True)
check("弹窗回车保存", modal.done == ("ok", "夜"))

# --- 缩小 scale 后的小窗口适配（弹窗/提示/菜单不能超出窗口）---
modal2 = InputModal("保存穿搭方案", "输入方案名称：")
modal2.resize(210, 283)                     # scale=0.7 时桌宠窗口大小
check("窄窗口弹窗不越界",
      modal2._rect.left >= 0 and modal2._rect.right <= 210
      and modal2._rect.bottom <= 283
      and modal2._ok_rect.right <= 210 and modal2._cancel_rect.left >= 0)
modal2.key(unicode_char="很长的方案名字测试")
small_screen = pygame.Surface((210, 283), pygame.SRCALPHA)
modal2.draw(small_screen, 0.0)              # 绘制不崩溃
check("窄窗口弹窗可绘制", True)
check("弹窗点击按钮仍有效",
      (modal2.click(modal2._ok_rect.center) or modal2.done ==
       ("ok", "很长的方案名字测试")))

st, shown = fit_text("一个非常非常长的方案名称文本", 15, 60)
check("文本自适应截断", st.get_width() <= 60 and shown)
st2, shown2 = fit_text_tail("0123456789abcdef", 13, 40)
check("输入框左侧滚动", st2.get_width() <= 40 and shown2.endswith("f")
      and len(shown2) < 16)

tiny = pygame.Surface((180, 220), pygame.SRCALPHA)
menu2 = CtxMenu()
menu2.open([{"type": "act", "label": "一个很长的菜单项名称用于测试截断"}],
           8, 8, 180, 220)
menu2.draw(tiny, (10, 10))
check("窄窗口菜单不越界", menu2.size[0] <= 180 - 12 and menu2.size[1] <= 220)
menu2.close()

# --- winutil（真 Windows 上验证 ctypes 符号存在性）---
check("winutil 导入", True)
if winutil.IS_WINDOWS:
    pos = winutil.cursor_pos()
    check("GetCursorPos 可用", isinstance(pos, tuple) and len(pos) == 2)
    w = winutil.LayeredWin()
    check("未attach不可用", w.ok is True and w.hwnd is None)

# --- 合成一帧（含面板），确保整条渲染管线无异常 ---
import cat as catmod  # noqa: E402
from deco import draw_background, draw_handheld  # noqa: E402
from ui import DressPanel  # noqa: E402

master = pygame.Surface((catmod.MW, catmod.MH), pygame.SRCALPHA)
ccfg = {"decorations": ["bow", "sunglasses", "cape", "coffee", "rainbow"], "_face_surf": None}
anim3 = CatAnim()
draw_background(master, 0.5, ccfg)
cv = pygame.Surface((catmod.MW, catmod.MH), pygame.SRCALPHA)
catmod.draw_cat(cv, ccfg, anim3, (3, -2))
sq = anim3.breath
sh = max(2, int(cv.get_height() * sq))
master.blit(pygame.transform.smoothscale(cv, (cv.get_width(), sh)),
            (0, cv.get_height() - sh))
draw_handheld(master, 0.5, ccfg)
frame = pygame.Surface((catmod.DW + 236, catmod.DH), pygame.SRCALPHA)
frame.blit(pygame.transform.smoothscale(master, (catmod.DW, catmod.DH)), (0, 0))
DressPanel().draw(frame, ccfg, catmod.DW + 236, catmod.DH)
check("整帧合成OK", frame.get_size() == (catmod.DW + 236, catmod.DH))

# --- 纹身系统 ---
import tattoos as _tt  # noqa: E402

check("部位共7个含双爪", len(_tt.REGIONS) == 7
      and _tt.REGION_NAMES.get("paw_r") == "右爪")
check("样式含魅魔纹", "succubus" in _tt.STYLE_NAMES and len(_tt.STYLES) >= 8)

config.save_tattoos({"forehead": "succubus", "paw_l": "heart", "坏key": "x"})
raw = config.load_tattoos()
clean = _tt.clean_mapping(raw)
check("纹身文件与过滤(旧格式)", clean == {
    "forehead": {"type": "style", "ref": "succubus", "scale": 1.0},
    "paw_l": {"type": "style", "ref": "heart", "scale": 1.0}})

# 归一化：新格式 / 大小 / 非法值
check("归一化新格式", _tt.normalize_entry(
    {"type": "style", "ref": "moon", "scale": 1.4})
    == {"type": "style", "ref": "moon", "scale": 1.4})
check("归一化图片项", _tt.normalize_entry(
    {"image": "tattoos/a.png", "scale": 0.8})
    == {"type": "image", "ref": "tattoos/a.png", "scale": 0.8})
check("大小钳制", _tt.clamp_scale(9) == _tt.SCALE_MAX
      and _tt.clamp_scale(0.01) == _tt.SCALE_MIN)
check("非法项丢弃", _tt.normalize_entry("不存在") is None
      and _tt.normalize_entry({"ref": ""}) is None)

spr = _tt.style_sprite("succubus")
check("样式贴图128", spr.get_size() == (128, 128))
for sid, _ in _tt.STYLES:
    _tt.style_sprite(sid)
check("全部样式可生成", True)

# 全部位/全样式绘制到猫画布（轮流分配，不崩溃且额头区域有内容）
bigmap = {rid: _tt.STYLE_IDS[i % len(_tt.STYLE_IDS)]
          for i, rid in enumerate(dict(_tt.REGIONS))}
canvas2 = pygame.Surface((catmod.MW, catmod.MH), pygame.SRCALPHA)
animT = CatAnim()
catmod.draw_cat(canvas2, {"decorations": [], "_face_surf": None,
                          "tattoos": bigmap}, animT)
box = _tt.BODY_BOXES["forehead"]
filled = 0
for xx in range(box[0] * 2, (box[0] + box[2]) * 2, 3):
    for yy in range(box[1] * 2, (box[1] + box[3]) * 2, 3):
        if canvas2.get_at((xx, yy)).a > 40:
            filled += 1
check("额头纹身已上猫", filled > 5)

# 自定义大小：同样式，缩放越大覆盖像素越多（在空白画布上只统计纹身本身）
def chest_pixels(scale):
    m = {"chest": {"type": "style", "ref": "star", "scale": scale}}
    cv = pygame.Surface((catmod.MW, catmod.MH), pygame.SRCALPHA)
    _tt.draw_body_tattoos(cv, m, CatAnim())
    bx, by, bw, bh = _tt.BODY_BOXES["chest"]
    n = 0
    for xx in range(max(0, (bx - 30) * 2), min(catmod.MW, (bx + bw + 30) * 2), 2):
        for yy in range(max(0, (by - 30) * 2), min(catmod.MH, (by + bh + 30) * 2), 2):
            if cv.get_at((xx, yy)).a > 40:
                n += 1
    return n

small, big = chest_pixels(0.6), chest_pixels(1.8)
check("纹身大小生效", small > 0 and big > small * 1.5)

# 自定义纹身图片：保存相对路径 + 能画到猫身上
from PIL import Image as _Image  # noqa: E402
src_img = os.path.join(tmp, "my_tattoo.png")
_Image.new("RGBA", (120, 90), (10, 220, 120, 255)).save(src_img)
ref = config.save_tattoo_image(_Image.open(src_img))
check("自定义图存相对路径", ref.startswith("tattoos/")
      and config.resolve_tattoo_image(ref) is not None)
_tt.clear_image_cache()
img_surf = _tt.custom_image(ref)
check("自定义图可载入", img_surf is not None and img_surf.get_size() == (120, 90))
m_img = {"chest": {"type": "image", "ref": ref, "scale": 1.0}}
cv2 = pygame.Surface((catmod.MW, catmod.MH), pygame.SRCALPHA)
catmod.draw_cat(cv2, {"decorations": [], "_face_surf": None,
                      "tattoos": m_img}, CatAnim())
bx, by, bw, bh = _tt.BODY_BOXES["chest"]
check("自定义图画上猫",
      cv2.get_at(((bx + bw // 2) * 2, (by + bh // 2) * 2)).a > 40)

# --- 纹身工坊（无头自检：布局 + 样式/大小/自定义图 + 绘制一帧）---
from tattoo_editor import Editor, CUSTOM_TILE  # noqa: E402

ed = Editor()
ed.layout()
ed.on_click(ed.region_rows[0][0].center)          # 选额头
sc0 = ed.style_cells[0][0]
ed.on_click(sc0.center)                            # 点第一款样式
check("编辑器点击应用",
      (ed.mapping.get("forehead") or {}).get("ref") == _tt.STYLE_IDS[0])

# 滑块 / 按钮调大小
ed.size_plus.inflate_ip(0, 0)
for _ in range(4):
    ed.on_click(ed.size_plus.center)               # +20%
check("编辑器加号调大小", abs(ed.current_scale() - 1.2) < 1e-6)
ed.on_click(ed.size_reset.center)
check("编辑器重置大小", abs(ed.current_scale() - 1.0) < 1e-6)
ed.set_scale(1.5)
check("编辑器大小写回方案", ed.mapping["forehead"]["scale"] == 1.5)

# 自定义图片格子
ed.on_click(ed.clear_btn.center)
check("编辑器清除部位", "forehead" not in ed.mapping)
succ_rect = next(r for r, sid in ed.style_cells if sid == "succubus")
ed.on_click(succ_rect.center)
check("编辑器应用魅魔纹",
      (ed.mapping.get("forehead") or {}).get("ref") == "succubus")
custom_rect = next(r for r, sid in ed.style_cells if sid == CUSTOM_TILE)
ed.set_scale(0.9)
ok_custom = ed.apply_custom_image(src_img)         # 等价于点“上传图片…”选文件
check("编辑器应用自定义图", ok_custom
      and ed.mapping["forehead"]["type"] == "image"
      and ed.mapping["forehead"]["scale"] == 0.9)
ed.draw(1 / 30, 0.0)                               # 渲染一帧不崩溃
check("编辑器绘制一帧", ed.mapping["forehead"]["type"] == "image")
check("自定义图格子存在", custom_rect is not None)
ed.mapping = {}
ed.save()
pygame.quit()

print("----")
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
