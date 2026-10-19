@echo off
chcp 65001 >nul
REM Rebuild the video from this package WITHOUT the voice API (audio is included) and without any key.
REM   rebuild_package.bat          full rebuild: assets -> EffectCraft scenes -> FilmCraft -> out\rebuilt.mp4
REM   rebuild_package.bat film     only re-assemble the included work\Scene1.mp4/Scene2.mp4 + audio in FilmCraft
REM The .ecproj/.fcproj files in projects\ keep the original absolute D:\ paths; they are rebuilt here with paths relative to this folder.
cd /d "%~dp0"
set AF_WORK=%CD%\work
if /i not "%1"=="film" (
  python tools\make_assets.py || goto :fail
  python tools\build_scenes.py || goto :fail
)
python tools\build_film.py --out "%CD%\out\rebuilt.mp4" || goto :fail
echo. & echo Done: %CD%\out\rebuilt.mp4
if not defined NOPAUSE pause
exit /b 0
:fail
echo. & echo *** FAILED - see messages above ***
if not defined NOPAUSE pause
exit /b 1
