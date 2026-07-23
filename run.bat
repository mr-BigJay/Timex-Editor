@echo off
cd /d "%~dp0"
start "" wscript.exe //nologo "%~dp0run.vbs"
exit /b 0
