@echo off
REM CSBS Fire Animation - LAN Sync Server (NO internet needed, Python only)
REM Double-click this ONCE on the main laptop. Then open the shown address on every desktop.
cd /d "%~dp0"
python sync-server.py
if errorlevel 1 py sync-server.py
pause
