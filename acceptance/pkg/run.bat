@echo off
chcp 65001 >nul
REM Animation Factory - one-click run. Options are passed through, e.g.:
REM   run.bat --shirt "#2E86DE" --point-speed 0.3 --out-dir D:\Videos --name demo.mp4
cd /d "%~dp0"
python tools\run_all.py %*
if errorlevel 1 ( echo. & echo *** FAILED - see messages above *** ) else ( echo. & echo Done. Open the OUTPUT path shown above. )
if not defined NOPAUSE pause
