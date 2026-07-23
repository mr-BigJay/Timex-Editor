@echo off
chcp 65001 >nul
cd /d "%~dp0\.."
title Timex Editor — ساخت فایل exe

echo.
echo  در حال ساخت TimexEditor.exe ...
echo.

where py >nul 2>&1
if %errorlevel%==0 (
    py -3 -m pip install -r requirements.txt pyinstaller -q
    py -3 -m PyInstaller build\timex_editor.spec --noconfirm --distpath dist --workpath build\pyinstaller
    goto :copy
)

where python >nul 2>&1
if %errorlevel%==0 (
    python -m pip install -r requirements.txt pyinstaller -q
    python -m PyInstaller build\timex_editor.spec --noconfirm --distpath dist --workpath build\pyinstaller
    goto :copy
)

echo  [خطا] Python یافت نشد!
pause
exit /b 1

:copy
if exist "dist\TimexEditor.exe" (
    copy /Y "dist\TimexEditor.exe" "TimexEditor.exe" >nul
    echo.
    echo  TimexEditor.exe در پوشهٔ اصلی ساخته شد.
    echo  برای اجرا روی TimexEditor.exe دوبار کلیک کنید.
    echo.
) else (
    echo  [خطا] ساخت exe ناموفق بود.
    pause
    exit /b 1
)
pause
exit /b 0
