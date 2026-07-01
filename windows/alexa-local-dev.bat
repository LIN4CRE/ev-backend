@echo off
setlocal
cd /d %~dp0\..
python scripts\alexa_local_dev.py
endlocal
