@echo off
cd /d "%~dp0"
rem Pocket Pal uses pygame-ce. If classic pygame is installed instead, it is swapped (both use the name "pygame").
python -c "import pygame,sys; sys.exit(0 if getattr(pygame,'IS_CE',False) else 1)" >nul 2>&1 || (python -m pip uninstall -y pygame >nul 2>&1 & python -m pip install -r requirements.txt)
python main.py %*
if errorlevel 1 pause
