@echo off
rem Seeded developer simulation of the learning and rare-event systems (headless). See tools\devsim.py.
cd /d "%~dp0"
python -c "import pygame,sys; sys.exit(0 if getattr(pygame,'IS_CE',False) else 1)" >nul 2>&1 || (python -m pip uninstall -y pygame >nul 2>&1 & python -m pip install -r requirements.txt)
python tools\devsim.py %*
pause
