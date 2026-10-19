@echo off
chcp 65001 >nul
REM AnimationFactory local UI. Open the URL printed below in a browser (only this computer can reach it).
cd /d "%~dp0"
python server.py --port 8765
pause
