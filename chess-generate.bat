@echo off
setlocal

set "MIX=%~1"
set "CONFIG="

if "%MIX%"=="" goto :all
if "%MIX%"=="1" set "CONFIG=1-basic"
if "%MIX%"=="2" set "CONFIG=2-deflection-attraction"
if "%MIX%"=="3" set "CONFIG=3-interference"
if "%MIX%"=="4" set "CONFIG=4-clearance"

if not defined CONFIG goto :usage

python "%~dp0chess\generate_mix.py" "%CONFIG%"
exit /b %errorlevel%

:all
rem Generate every TOML config in filename order; abort on the first failure.
for /f "delims=" %%F in ('dir /b /a-d /on "%~dp0chess\configs\*.toml" 2^>nul') do (
    if /I not "%%~nF"=="0-defaults" (
        echo.
        echo === Generating %%~nF ===
        python "%~dp0chess\generate_mix.py" "%%~nF"
        if errorlevel 1 exit /b 1
    )
)
exit /b 0

:usage
echo Usage: chess-generate [mix-number]
echo.
echo Available mixes:
echo   (no argument) - all mixes (in config filename order)
echo   1 - basic
echo   2 - deflection-attraction
echo   3 - interference
echo   4 - clearance
exit /b 1
