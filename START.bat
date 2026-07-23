@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Timex Editor

echo.
echo  Timex Editor — در حال اجرا...
echo.

where pyw >nul 2>&1
if %errorlevel%==0 (
    pyw "%~dp0attendance_app.pyw"
    if %errorlevel%==0 goto :done
)

where pythonw >nul 2>&1
if %errorlevel%==0 (
    pythonw "%~dp0attendance_app.pyw"
    if %errorlevel%==0 goto :done
)

where py >nul 2>&1
if %errorlevel%==0 (
    py -3w "%~dp0attendance_app.pyw"
    if %errorlevel%==0 goto :done
)

where python >nul 2>&1
if %errorlevel%==0 (
    python "%~dp0attendance_app.pyw"
    if %errorlevel%==0 goto :done
)

echo.
echo  [خطا] Python یافت نشد!
echo.
echo  لطفاً Python را از https://python.org نصب کنید
echo  و هنگام نصب گزینه "Add Python to PATH" را فعال کنید.
echo.
pause
exit /b 1

:done
exit /b 0
