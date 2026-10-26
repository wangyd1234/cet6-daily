@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem 本地手动跑一次（可用于测试或补发）
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 scripts\daily.py %*
) else (
  python scripts\daily.py %*
)
echo.
pause
