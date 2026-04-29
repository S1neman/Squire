@echo off
setlocal enabledelayedexpansion

if "%1"=="" (
    echo Usage: publish_version.bat 0.1.4
    exit /b 1
)

set VERSION=%1
set ARCHIVE_DIR=F:\projects\squire-builds\%VERSION%

echo === Publishing Squire %VERSION% ===

:: 1. Copy source files
if not exist "%ARCHIVE_DIR%" mkdir "%ARCHIVE_DIR%"
echo Copying files...
xcopy /E /Y /Q "F:\projects\squire-lite\*" "%ARCHIVE_DIR%"

:: 2. Clean archive from garbage
echo Cleaning archive...
for %%d in (venv build dist logs __pycache__ .git .vscode .idea) do (
    if exist "%ARCHIVE_DIR%\%%d" rmdir /s /q "%ARCHIVE_DIR%\%%d"
)
del /q "%ARCHIVE_DIR%\*.spec" 2>nul
del /q "%ARCHIVE_DIR%\publish_version.bat" 2>nul

:: 3. Git: commit and tag
cd /d "F:\projects\squire-lite"
git add .
git status --porcelain | findstr . >nul
if %errorlevel% equ 0 (
    echo Committing changes...
    git commit -m "Squire %VERSION%: preparing release"
) else (
    echo No changes to commit.
)

echo Creating tag v%VERSION%...
git tag -a "v%VERSION%" -m "Squire %VERSION%"
git push origin main --tags

:: 4. Build .exe
echo Building Squire.exe...
call build_exe.bat

if not exist "dist\Squire.exe" (
    echo Error: could not build Squire.exe
    exit /b 1
)

:: 5. Copy .exe to archive
copy /Y "dist\Squire.exe" "%ARCHIVE_DIR%\Squire_%VERSION%.exe"

:: 6. Create GitHub release
echo Creating release...
gh release create "v%VERSION%" --title "Squire %VERSION%" --notes "See CHANGELOG.md" "dist\Squire.exe#Squire_%VERSION%.exe"

echo Done! Release created: https://github.com/S1neman/Squire/releases/tag/v%VERSION%
pause