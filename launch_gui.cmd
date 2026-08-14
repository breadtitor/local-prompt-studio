@echo off
setlocal
cd /d "%~dp0"
py -3 -m local_prompt_studio.gui
if errorlevel 1 pause
