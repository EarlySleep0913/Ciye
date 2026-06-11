@echo off
chcp 65001 >nul
title CiYe 词页
cd /d "%~dp0"

:menu
cls
echo.
echo   ██████╗██╗   ██╗███████╗
echo  ██╔════╝╚██╗ ██╔╝██╔════╝
echo  ██║      ╚████╔╝ █████╗
echo  ██║       ╚██╔╝  ██╔══╝
echo  ╚██████╗   ██║   ███████╗
echo   ╚═════╝   ╚═╝   ╚══════╝
echo.
echo  [1] 启动服务
echo  [2] 停止服务
echo  [3] 重启服务
echo  [0] 退出
echo.
set /p choice=请选择操作:

if "%choice%"=="1" goto start
if "%choice%"=="2" goto stop
if "%choice%"=="3" goto restart
if "%choice%"=="0" exit
goto menu

:start
echo.
echo  正在启动...
start "CiYe-Backend" /min python run.py
timeout /t 2 /nobreak >nul
start "CiYe-Frontend" cmd /k "npm run dev"
timeout /t 3 /nobreak >nul
start http://127.0.0.1:5173
echo  ✅ 启动完成！浏览器已打开。
echo.
pause
goto menu

:stop
echo.
echo  正在停止...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM node.exe 2>nul
echo  ✅ 服务已停止。
echo.
pause
goto menu

:restart
echo.
echo  正在重启...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM node.exe 2>nul
timeout /t 1 /nobreak >nul
goto start
