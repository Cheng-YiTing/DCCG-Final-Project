@echo off
chcp 65001 >nul
setlocal

REM 1) 切換到 bat 所在資料夾，避免找不到 visualization.py / config.json
cd /d %~dp0

echo [INFO] Python executable:
py -3 -c "import sys; print(sys.executable)"

REM 2) 檢查 compas_viewer 是否已安裝
echo [INFO] Checking dependencies...
py -3 -m pip show compas_viewer >nul 2>nul
if errorlevel 1 (
    echo [INFO] compas_viewer not found. Installing requirements...
    py -3 -m pip install -r requirements.txt
) else (
    echo [INFO] Dependencies already installed. Skipping installation.
)

REM 3) 執行視覺化
echo [INFO] Running visualization.py ...
py -3 visualization.py

echo [INFO] Done.
pause