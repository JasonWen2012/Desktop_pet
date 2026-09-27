@echo off
chcp 65001 >nul
REM ============================================================
REM  BongoCatPet 一键打包脚本（PyInstaller）
REM  产物：dist\BongoCatPet.exe
REM ============================================================
cd /d "%~dp0"

echo [1/3] 安装依赖...
python -m pip install -r requirements.txt pyinstaller

echo [2/3] 开始打包（单文件、无控制台）...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name BongoCatPet ^
  --hidden-import pynput.keyboard._win32 ^
  --hidden-import pynput.mouse._win32 ^
  --hidden-import tattoos ^
  --hidden-import tattoo_editor ^
  main.py

echo [3/3] 完成！
echo.
echo 打包结果：dist\BongoCatPet.exe
echo 建议把 exe 复制到桌面等可写目录后双击运行。
pause
