@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==================================================
echo   五子棋天梯竞技平台桌面端
echo   正在启动原生客户端窗口...
echo ==================================================
start "" "D:\miniconda\python.exe" run.py
