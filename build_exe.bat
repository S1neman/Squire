@echo off
title Squire Builder

echo.

:: 1. Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Install Python 3.10-3.12 and add it to PATH.
    pause
    exit /b 1
)

:: 2. Creating venv
if not exist "venv" (
    echo Building venv...
    python -m venv venv
    if errorlevel 1 (
        echo Error creating venv
        pause
        exit /b 1
    )
)

:: 3. Activate venv and update pip
call venv\Scripts\activate
python -m pip install --upgrade pip

:: 4. Install requirements
if exist "requirements.txt" (
    echo Installing from requirements.txt...
    pip install -r requirements.txt
) else (
    echo Installing basic requirements...
    pip install customtkinter sounddevice numpy faster-whisper ollama torch requests pystray Pillow
)

:: 5. Ensure pyinstaller is installed (for build)
pip show pyinstaller >nul 2>&1 || pip install pyinstaller

:: 6. Delete old builds
echo Clearing...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "*.spec" del /q *.spec

:: 7. Check ffmpeg.exe
if exist "ffmpeg.exe" (
    echo Found ffmpeg.exe, adding in build.
    set FFMPEG_COPY=yes
) else (
    echo ffmpeg.exe not found. Download ffmpeg.exe and put it in root folder.
    echo Continue without ffmpeg.exe? ^(user has to install FFmpeg manually^)
    choice /C YN /N /M "Continue (Y/N)? "
    if errorlevel 2 exit /b 1
)

:: 8. Run PyInstaller
echo Building Squire.exe...
pyinstaller --onefile --noconsole --name Squire ^
    --icon="assets\icons\app_icon.ico" ^
    --add-data "ui;ui" ^
    --add-data "core;core" ^
    --add-data "assets;assets" ^
    main.py

if errorlevel 1 (
    echo Error on build!
    pause
    exit /b 1
)

:: 9. Copy files to dist
echo Copying files...
if exist "README.md" copy /y README.md dist\README.md
if exist "CHANGELOG.md" copy /y CHANGELOG.md dist\CHANGELOG.md
if "%FFMPEG_COPY%"=="yes" copy /y ffmpeg.exe dist\ffmpeg.exe

:: 10. Final message
echo.
echo DONE! Build in dist:
echo   - Squire.exe
if exist "dist\README.md" echo   - README.md
if exist "dist\CHANGELOG.md" echo   - CHANGELOG.md
if exist "dist\ffmpeg.exe" echo   - ffmpeg.exe
echo.
echo Build finished successfully.
pause