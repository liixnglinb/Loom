@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title ModelFlow 智模流水线 · 启动器

echo ============================================
echo   ModelFlow 智模流水线
echo   正在启动，请稍候...
echo ============================================
echo.

rem ---- 定位 Python 解释器 ----
set "PY="
for /f "delims=" %%i in ('where python 2^>nul') do if not defined PY set "PY=%%i"
if not defined PY (
  if exist "C:\Users\李星历\AppData\Local\Programs\Python\Python312\python.exe" (
    set "PY=C:\Users\李星历\AppData\Local\Programs\Python\Python312\python.exe"
  )
)
if not defined PY (
  echo [错误] 未找到 Python，请先安装 Python 3.10+ 后重试。
  pause
  exit /b 1
)
echo [1/3] 使用 Python: %PY%

rem ---- 切换到工作目录 ----
cd /d "%~dp0"

rem ---- 检查端口占用 ----
netstat -ano | findstr ":8000 .*LISTENING" >nul 2>&1
if not errorlevel 1 (
  echo [提示] 本机 8000 端口已有服务在运行。
  echo        若这是旧版 ModelFlow，请先关闭它再启动。
  choice /c YN /n /m "是否强制结束占用进程后重启？[Y=是/N=否]"
  if errorlevel 2 (
    echo [提示] 检测你正在浏览器访问 http://127.0.0.1:8000
    start "" "http://127.0.0.1:8000"
    pause
    exit /b 0
  )
  for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000 .*LISTENING"') do (
    taskkill /f /pid %%p >nul 2>&1
  )
  echo [提示] 已结束占用进程，3 秒后启动新服务...
  timeout /t 3 /nobreak >nul
)

echo [2/3] 启动后端服务...
start "ModelFlow-后端" "%PY%" "%~dp0run.py"

rem ---- 等待端口就绪 ----
echo [3/3] 等待服务就绪...
set "READY="
for /l %%i in (1,1,30) do (
  timeout /t 1 /nobreak >nul
  netstat -ano | findstr ":8000 .*LISTENING" >nul 2>&1
  if not errorlevel 1 set "READY=1"
  if defined READY goto ready
)
echo [警告] 30 秒内未检测到服务启动，可能启动失败，请查看后端窗口日志。
pause
exit /b 1

:ready
echo.
echo ============================================
echo   启动完成！
echo   浏览器将自动打开，地址: http://127.0.0.1:8000
echo --------------------------------------------------
echo   MODELFLOW 服务窗口请勿关闭，关闭即停止服务。
echo   停止方式：直接关闭"ModelFlow-后端"黑色窗口即可。
echo ============================================
echo.
start "" "http://127.0.0.1:8000"

rem ---- 等待后端窗口结束，保持本窗口存在 ----
:wait
tasklist /fi "imagename eq python.exe" 2>nul | findstr /i "python" >nul 2>&1
if errorlevel 1 goto end
timeout /t 5 /nobreak >nul
goto wait

:end
echo.
echo 服务已停止，退出启动器。
timeout /t 2 /nobreak >nul
exit /b 0