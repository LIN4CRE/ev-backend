@echo off
setlocal
cd /d %~dp0\..
python scripts\doctor.py
endlocal
