@echo off
chcp 65001 >nul
title 循证营养skill 离线服务
cd /d "%~dp0"

rem 端口已在服务中：直接打开报告目录
netstat -ano | findstr ":8321 " | findstr "LISTENING" >nul
if not errorlevel 1 goto :already

where python >nul 2>nul
if not errorlevel 1 goto :run_python
where py >nul 2>nul
if not errorlevel 1 goto :run_py
where powershell >nul 2>nul
if not errorlevel 1 goto :run_powershell

echo [错误] 未检测到 Python 或 Windows PowerShell，无法启动本地 HTTP 服务。
pause
exit /b 1

:run_python
start "webr-offline-server" /min python -m http.server 8321
goto :open

:run_py
start "webr-offline-server" /min py -m http.server 8321
goto :open

:run_powershell
start "webr-offline-server" /min powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\serve_offline_webr.ps1" -Port 8321 -Root "%~dp0"
goto :open

:open
timeout /t 2 /nobreak >nul
start "" "http://localhost:8321/webr-offline/reports/"
echo 离线服务已启动：http://localhost:8321/webr-offline/reports/
echo 浏览器已打开报告目录，点击报告文件即可运行。
echo 停止服务：关闭任务栏中最小化的 "webr-offline-server" 窗口。
exit /b 0

:already
echo 端口 8321 已有服务在运行，直接打开报告目录。
start "" "http://localhost:8321/webr-offline/reports/"
exit /b 0
