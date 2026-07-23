@echo off
REM اجرا بدون پنجرهٔ CMD — از run.vbs استفاده می‌کند
cd /d "%~dp0"
wscript //nologo "%~dp0run.vbs"
exit /b 0
