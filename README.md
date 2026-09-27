# BongoCatPet —— 桌面猫娘桌宠（Bongo Cat 风格）

用 Python + pygame 写的一只桌面小猫：
**透明、置顶、无边框、可拖拽**；按键盘/点鼠标时它会跟着“敲爪爪”，
眼睛一直追着你的鼠标看，发呆久了还会打哈欠。

支持上传自己的照片当猫脸；内置 头饰 / 眼镜 / 服装 / 手持物 / 背景
共 12 件装饰，可自由搭配并保存为多套“穿搭方案”。

---

## 目录结构

```
桌宠项目/
├─ main.py            # 入口：事件循环 / 菜单 / 合成 / 呈现
├─ cat.py             # 小猫本体绘制 + 呼吸/眨眼/哈欠/敲爪动画
├─ deco.py            # 背景(彩虹/星星) 与手持物(咖啡/吉他)
├─ tattoos.py         # 纹身样式贴图 / 部位定义 / 在猫身上绘制
├─ tattoo_editor.py   # 纹身工坊（独立进程的新窗口，捏脸式界面）
├─ ui.py              # 右键菜单 / 换装面板 / 输入弹窗（中文 UI）
├─ config.py          # config.json / outfits.json / tattoos.json / 开机自启(注册表)
├─ inputs.py          # pynput 全局键盘/鼠标监听，左右半区映射
├─ winutil.py         # Windows 每像素透明 + 置顶窗口（纯 ctypes）
├─ requirements.txt   # 依赖：pygame / pynput / pillow
├─ build.bat          # 一键 PyInstaller 打包脚本
└─ tools/             # 开发用工具（离屏渲染 QA、ASCII 预览、逻辑测试）
```

运行时生成（都放在程序所在目录）：

| 文件 | 说明 |
|---|---|
| `config.json`   | 当前外观/监听/缩放等配置 |
| `outfits.json`  | 保存的穿搭方案（JSON） |
| `tattoos.json`  | 纹身配置 `{部位: 纹身项}`（纹身工坊写入） |
| `tattoos/`      | 上传的自定义纹身图片（工坊自动存这里，跟着文件夹走） |
| `faces/`        | 上传的猫脸照片 |

`tattoos.json` 的两种写法（旧文件仍是字符串，会自动兼容升级）：

```jsonc
{
  // 旧写法：只用内置样式（大小默认 100%）
  "forehead": "succubus",
  // 新写法：样式 + 大小；图片项用 type/image
  "cheek_l":  { "type": "style", "ref": "heart",    "scale": 1.3 },
  "chest":    { "type": "image", "ref": "tattoos/tattoo_20260910_170333_263.png", "scale": 0.8 }
}
```

---

## 运行方式

要求：Windows（透明窗口 + 开机自启依赖 Windows）、Python 3.9+。

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行
python main.py
```

> 非 Windows 也能跑：退化为普通无边框窗口（背景不透明），其余功能不变。

---

## 玩法 / 功能对照

| 功能 | 说明 |
|---|---|
| 🖱️ 拖拽 | 按住猫身拖动，可移到屏幕任意位置（自动防止拖出屏幕） |
| ⌨️ 敲爪 | 键盘按**左半区**(QWERT/ASDFG/ZXCVB/1-5…)敲**左爪**，**右半区**(YUIOP/HJKL/NM/6-0…)敲**右爪**；**空格**=双爪齐敲；按住不松则一直按着，松开弹起 |
| 🖱️ 点击 | 任意鼠标键按下，双爪齐敲（全局监听，在别的窗口里点击也会反应） |
| 🔢 敲击计数 | 桌宠正下方的小胶囊实时显示本次运行的「敲击 N」（键盘按下 + 鼠标点击次数）；每次启动/开机都从 0 重新计，不写入配置 |
| 👀 眼睛 | 猫眼瞳孔跟随鼠标位置转动 |
| 😴 动画 | 空闲时身体一起一伏地呼吸；约 20 秒无操作会自动打哈欠 |
| 💉 纹身 | 右键菜单 → **纹身工坊…**：在独立新窗口中像“创建角色”一样，先选部位（额头/左颊/右颊/胸口/腹部/左爪/右爪），再挑纹样（爱心/星星/月牙/小花/蝴蝶/骷髅/十字/符文/**魅魔纹**）或**上传自己的图片**（建议透明 PNG，自动存进 `tattoos/`）；下方**大小滑块可把每个纹身单独调到 50%~200%**（拖拽/滚轮/±按钮/一键回 100%）——中央实时预览，改动即时应用到桌宠 |
| 📸 换脸 | 上传照片当猫脸（右键菜单 → 上传照片…，或在换装面板底部“上传照片…”）；想**换回原版猫头**：换装面板点“卡通猫头”，或恢复默认 |
| 🎀 换装 | 右键菜单 → 换装面板：蝴蝶结/王冠/耳机/圆框眼镜/墨镜/领结/围巾/披风/咖啡杯/吉他/彩虹/星星（每件独立开关），**面板最下方还有“卡通猫头 / 上传照片…”两个头像选项**，实时生效 |
| 📚 方案 | 穿搭方案 → 保存当前为方案…/加载/删除，存于 `outfits.json`，可保存多套；**每套方案记录：装饰 + 缩放倍率 + 当时的头像**（自定义照片或“原版猫头”），加载时一并恢复（菜单里标注，如“名称 · 缩放 110% · 自定义头”） |
| ⚙️ 设置 | 右键菜单可开关键盘/鼠标监听、放大/缩小/还原缩放、开机自启、退出 |
| ✨ 恢复默认 | 一键清空所有装饰、自定义猫脸与纹身 |

右键小猫本体即可弹出菜单；菜单与面板都可以用 Esc / 点击空白处关闭。

> 说明：
> - 头像字段在每套方案里：自定义照片路径或空串（=原版猫头）；**老方案没有该字段时，加载会保持当前头像不变**。
> - 纹身保存在独立的 `tattoos.json`，与“穿搭方案”相互独立——
>   切换方案不会抹掉纹身，它们一直跟着猫；爪部纹身会跟着敲击动作一起动。
> - 每个部位可单独设置纹身大小（50%~200%）与自定义图片；图片按“等比缩放完整显示”贴上去，
>   不会裁切，透明背景会保留。
> - 把桌宠调小（缩放 70% 等）时，命名弹窗、右键菜单、底部提示都会**自动适配窗口尺寸**：
>   字号先缩小、放不下再截断，输入框内容超宽会从左侧滚动，不会出现显示不全。

---

## 打包成 exe（PyInstaller）

本项目为 **单文件、无控制台** 打包做了兼容处理（配置/方案/照片存到 exe 旁边）。

### 方式一：双击运行 `build.bat`

脚本内容等价于：

```bat
pip install -r requirements.txt pyinstaller

pyinstaller --noconfirm --clean --onefile --windowed --name BongoCatPet ^
  --hidden-import pynput.keyboard._win32 ^
  --hidden-import pynput.mouse._win32 ^
  --hidden-import tattoos ^
  --hidden-import tattoo_editor ^
  main.py
```

打包成功后生成 `dist\BongoCatPet.exe`。

### 方式二：手动打包

```bash
python -m PyInstaller --noconfirm --clean --onefile --windowed --name BongoCatPet ^
  --hidden-import pynput.keyboard._win32 ^
  --hidden-import pynput.mouse._win32 ^
  --hidden-import tattoos ^
  --hidden-import tattoo_editor ^
  main.py
```

参数说明：

- `--onefile` 打成单个 exe（约 30~40MB）；若被杀毒软件误报，
  可去掉 `--onefile` 改用默认 `--onedir`（dist 文件夹形式），
  或加 `--exclude-module numpy` 缩小体积。
- `--windowed` 不弹黑控制台。
- `--hidden-import pynput.keyboard._win32 / pynput.mouse._win32`
  是 pynput 在 Windows 上的底层后端，不写可能打包后“全局监听无效”。
- `tattoos` 与 `tattoo_editor` 是“纹身工坊”需要的模块（部分在函数内
  懒加载），务必保留 hidden-import，否则 exe 里打不开纹身工坊。
- 纹身工坊以**同一 exe** 的 `--tattoo-editor` 参数拉起，
  无需额外文件，打包后仍是一个单文件。

### 使用 exe 的注意点

1. 首次运行时若 Windows 提示“Windows 已保护你的电脑”，选 **仍要运行**
   （无签名单文件程序常见提示，也可自行用签名工具解决）。
2. 双击 exe 后桌宠出现在**屏幕右下角**；右键小猫可退出。
3. 配置与方案会写在 **exe 所在文件夹**（不要放 C:\Program Files 等
   无写权限目录，建议放桌面或自建文件夹）。
4. 建议把 exe 加入杀毒软件信任区，避免开机自启被拦截。

---

## 常见问题

**Q1：窗口不是透明的 / 是黑色方块？**
透明窗口目前只在 Windows 上实现（每像素 Alpha 合成）。
若你的 Windows 关闭了“桌面合成/毛玻璃”或显卡驱动过旧，请更新显卡驱动。
其它系统会退化为普通窗口，属预期行为。

**Q2：全局键盘没反应？**
- 确认没有以“管理员身份”运行其它程序抢占低级键盘钩子；
- 部分杀软会拦截 pynput 的全局钩子，请加入信任；
- 若打包后失效，多半是漏了上面的两个 `--hidden-import`，请重新打包。

**Q3：爪子乱敲 / 没在敲？**
左右半区按物理键盘分界（T/G/B 及左侧属于左爪，Y/H/N 及右侧属于右爪，
数字键 1-5 左、6-0 右）。方向键/回车/退格等在右爪。
空格 = 双爪齐敲。若不想让某只手受某类输入影响，可在
右键菜单 → 监听设置 里关掉键盘或鼠标监听。

**Q4：可以自己调哈欠等待时间吗？**
改 `config.json` 里的 `idle_yawn_seconds`（秒）。

**Q5：眼睛为什么不转了？**
关闭“鼠标监听”后眼睛会停止跟随（属预期）；开启后恢复。

---

## 配置说明（config.json 可手改）

```jsonc
{
  "decorations": ["bow", "crown"],   // 已开启的装饰 id 列表
  "face": "",                        // 猫脸照片路径（留空=默认脸）
  "scale": 1.0,                      // 0.7 ~ 1.5
  "keyboard": true,                  // 全局键盘监听
  "mouse": true,                     // 全局鼠标监听
  "idle_yawn_seconds": 20.0,         // 空闲多少秒打哈欠
  "panel_open": false,               // 是否显示换装面板
  "window_pos": [x, y]               // 上次退出时的窗口位置
}
```

装饰 id：`bow 蝴蝶结 / crown 王冠 / headphones 耳机 / glasses 圆框 /
sunglasses 墨镜 / bowtie 领结 / scarf 围巾 / cape 披风 /
coffee 咖啡杯 / guitar 吉他 / rainbow 彩虹 / stars 星星`

---

## 技术要点（简短）

- 绘制：先在 2x 超采样画布上画小猫 → 平滑缩放，边缘干净；
  画布整体按“脚底为锚点”做纵向 ±1.2% 呼吸缩放。
- 透明：`pygame.display.set_mode(..., NOFRAME)` + Win32
  `UpdateLayeredWindow` 每像素 Alpha 合成（`winutil.py`），
  鼠标仍可点中猫身用于拖拽。
- 输入：pynput 键盘/鼠标监听线程把事件压队列，主循环每帧消费，
  与 pygame 自身的鼠标事件互不干扰。
- 数据：装饰开关、照片路径、缩放、监听开关存 `config.json`；
  穿搭方案存 `outfits.json`；开机自启写 HKCU\...\Run 注册表。
