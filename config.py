# -*- coding: utf-8 -*-
"""配置、穿搭方案(JSON)与开机自启管理。"""
import json
import os
import sys
import datetime
from pathlib import Path

APP_NAME = "BongoCatPet"

DEFAULT_DECOR = ["bow", "crown", "headphones", "glasses", "sunglasses",
                 "bowtie", "scarf", "cape", "coffee", "guitar", "rainbow", "stars"]


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """exe/脚本所在目录，所有数据文件都放在这里。"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


CONFIG_PATH = app_dir() / "config.json"
OUTFITS_PATH = app_dir() / "outfits.json"
TATTOOS_PATH = app_dir() / "tattoos.json"
FACES_DIR = app_dir() / "faces"

DEFAULT_CONFIG = {
    "decorations": [],            # 已启用的装饰 id 列表
    "face": "",                   # 猫脸照片路径（空 = 默认卡通脸）
    "scale": 1.0,                 # 缩放
    "keyboard": True,             # 全局键盘监听
    "mouse": True,                # 全局鼠标监听
    "idle_yawn_seconds": 20.0,    # 空闲多久打哈欠
    "panel_open": False,          # 换装面板是否打开
    "window_pos": None,           # [x, y]，退出时保存
}


def _read_json(path: Path, fallback):
    try:
        path = Path(path)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return fallback


def _write_json(path: Path, data) -> None:
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as e:
        print("[config] 保存失败:", e)


# ---------------------------------------------------------------- 主配置
def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    data = _read_json(CONFIG_PATH, {})
    for k, v in data.items():
        if k in cfg:
            cfg[k] = v
    # 合法化
    if not isinstance(cfg["decorations"], list):
        cfg["decorations"] = []
    cfg["decorations"] = [d for d in cfg["decorations"] if d in DEFAULT_DECOR]
    try:
        cfg["scale"] = float(cfg["scale"])
    except Exception:
        cfg["scale"] = 1.0
    cfg["scale"] = min(1.5, max(0.7, cfg["scale"]))
    for k in ("keyboard", "mouse", "panel_open"):
        cfg[k] = bool(cfg.get(k, DEFAULT_CONFIG[k]))
    return cfg


def save_config(cfg: dict) -> None:
    data = {k: cfg.get(k) for k in DEFAULT_CONFIG}
    _write_json(CONFIG_PATH, data)


# ---------------------------------------------------------------- 穿搭方案
def list_outfits() -> list:
    data = _read_json(OUTFITS_PATH, {})
    return sorted([k for k in data.keys() if isinstance(k, str)])


def save_outfit(name: str, decorations: list, scale=None, face=None) -> str:
    """
    保存一套方案。
    scale: 保存当时的窗口缩放(0.7~1.5)，None 表示不记录(老版本格式)
    face:  保存当时的头像照片路径；'' 表示默认猫头；None 表示不记录
    """
    data = _read_json(OUTFITS_PATH, {})
    name = name.strip() or ("穿搭方案 " + datetime.datetime.now().strftime("%m-%d %H:%M"))
    base, i = name, 1
    while name in data:
        i += 1
        name = f"{base} ({i})"
    rec = {
        "decorations": list(decorations),
        "created": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    if scale is not None:
        try:
            rec["scale"] = min(1.5, max(0.7, float(scale)))
        except (TypeError, ValueError):
            pass
    if face is not None:
        rec["face"] = str(face)
    data[name] = rec
    _write_json(OUTFITS_PATH, data)
    return name


def load_outfit_data(name: str):
    """
    返回 {'decorations':[...], 'scale': float|None, 'face': str|None}；
    face == '' 表示原版默认猫头；face is None 表示旧方案未记录头像(保持当前)。
    方案不存在返回 None。
    """
    data = _read_json(OUTFITS_PATH, {})
    rec = data.get(name)
    if not rec:
        return None
    decos = rec.get("decorations", [])
    decos = [d for d in decos if d in DEFAULT_DECOR]
    scale = rec.get("scale")
    try:
        scale = min(1.5, max(0.7, float(scale))) if scale is not None else None
    except (TypeError, ValueError):
        scale = None
    face = rec.get("face")
    if not isinstance(face, str):
        face = None
    return {"decorations": decos, "scale": scale, "face": face}


def load_outfit(name: str):
    """仅取装饰列表（兼容旧代码）。"""
    d = load_outfit_data(name)
    return d["decorations"] if d else []


def delete_outfit(name: str) -> None:
    data = _read_json(OUTFITS_PATH, {})
    if name in data:
        del data[name]
        _write_json(OUTFITS_PATH, data)


# ---------------------------------------------------------------- 纹身(独立于 config.json)
def load_tattoos() -> dict:
    """读取 tattoos.json（{部位: 样式}），由纹身工坊写入、桌宠轮询应用。"""
    data = _read_json(TATTOOS_PATH, {})
    if isinstance(data, dict):
        return data
    return {}


def save_tattoos(mapping: dict) -> None:
    _write_json(TATTOOS_PATH, mapping)


def tattoos_mtime_ns():
    """tattoos.json 的修改时间(纳秒)；文件不存在返回 None。"""
    try:
        return Path(TATTOOS_PATH).stat().st_mtime_ns
    except OSError:
        return None


# ---------------------------------------------------------------- 猫脸照片
def save_face_image(pil_image) -> str:
    """把上传的照片复制进本地 faces 目录，返回相对路径字符串。"""
    FACES_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = FACES_DIR / f"face_{stamp}.png"
    pil_image.convert("RGBA").save(path, "PNG")
    return str(path)


def face_abs_path(rel: str):
    if not rel:
        return None
    p = Path(rel)
    if not p.is_absolute():
        p = app_dir() / p
    return p if p.exists() else None


# ---------------------------------------------------------------- 自定义纹身图片
def tattoos_dir() -> Path:
    d = app_dir() / "tattoos"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_tattoo_image(pil_image) -> str:
    """
    把上传的纹身图片存进 tattoos 目录，返回可写进 tattoos.json 的路径
    （尽量用相对路径，方便整个文件夹搬走）。
    """
    img = pil_image.convert("RGBA")
    try:
        from PIL import Image
        img.thumbnail((512, 512), Image.LANCZOS)   # 限制尺寸，避免文件过大
    except Exception:
        pass
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    path = tattoos_dir() / f"tattoo_{stamp}.png"
    img.save(path, "PNG")
    try:
        return str(path.relative_to(app_dir())).replace("\\", "/")
    except ValueError:
        return str(path)


def resolve_tattoo_image(ref: str):
    """把 tattoos.json 里的 ref 解析成本机存在的绝对路径；不存在返回 None。"""
    if not ref or not isinstance(ref, str):
        return None
    p = Path(ref)
    if not p.is_absolute():
        p = app_dir() / p
    return p if p.exists() else None


# ---------------------------------------------------------------- 开机自启
def get_autostart() -> bool:
    if os.name != "nt":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Run") as k:
            winreg.QueryValueEx(k, APP_NAME)
            return True
    except OSError:
        return False


def _autostart_command() -> str:
    exe = sys.executable
    if is_frozen():
        return f'"{exe}"'
    entry = os.path.abspath(sys.argv[0])
    return f'"{exe}" "{entry}"'


def set_autostart(on: bool) -> bool:
    """Windows HKCU Run。返回是否成功。"""
    if os.name != "nt":
        return False
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_SET_VALUE)
        try:
            if on:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _autostart_command())
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
        finally:
            key.Close()
        return True
    except Exception as e:
        print("[autostart] 设置失败:", e)
        return False
