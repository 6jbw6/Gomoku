@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==================================================
echo   五子棋天梯竞技平台桌面端
echo   正在启动原生客户端窗口...
echo ==================================================
where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 python 命令，请确认已安装 Python 并加入 PATH。
    pause
    exit /b 1
)
start "" python run.py
