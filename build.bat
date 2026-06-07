@echo off
echo Building WebP Crunchr...
pyinstaller ^
    --onefile ^
    --noconsole ^
    --name "WebP Crunchr" ^
    --add-data "ui;ui" ^
    --add-data "core;core" ^
    --add-binary "vendor\cwebp.exe;." ^
    --add-data "vendor\LIBWEBP_LICENSE.txt;." ^
    main.py
echo.
echo Build complete. Executable is in dist\
pause
