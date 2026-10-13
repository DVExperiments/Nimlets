@echo off
rem Builds Nimlets.exe (one file, no Python needed to play) into the dist folder.
rem Runs the tests first, draws the icon, builds with PyInstaller, then test-runs the result.
cd /d "%~dp0"
python --version >nul 2>&1 || (echo Python 3.11 or newer is needed to BUILD the game ^(players do not need it^). & echo Get it from python.org and tick "Add Python to PATH". & pause & exit /b 1)
echo Installing what the build needs (pygame-ce and PyInstaller)...
python -m pip install --quiet --upgrade -r requirements.txt pyinstaller
python tools\build_exe.py %*
if errorlevel 1 (echo. & echo The build did not finish - see the messages above. & pause & exit /b 1)
echo.
echo Done! Nimlets.exe and a release zip are in the dist folder.
explorer dist
pause
