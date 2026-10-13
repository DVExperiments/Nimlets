@echo off
rem Testing mode: time runs 600x faster (1 real second = 10 game minutes). Press T to change speed.
cd /d "%~dp0"
python -c "import pygame,sys; sys.exit(0 if getattr(pygame,'IS_CE',False) else 1)" >nul 2>&1 || (python -m pip uninstall -y pygame >nul 2>&1 & python -m pip install -r requirements.txt)
python main.py --speed 600 --save saves\test_save.json %*
if errorlevel 1 pause
