@echo off
setlocal

set "MIX=%~1"
set "CONFIG="

if "%MIX%"=="1" set "CONFIG=basic"
if "%MIX%"=="2" set "CONFIG=deflection-attraction"
if "%MIX%"=="3" set "CONFIG=mix3"

if not defined CONFIG goto :usage

python "%~dp0chess\generate_mix.py" "%CONFIG%"
exit /b %errorlevel%

:usage
echo Usage: chess-generate ^<mix-number^>
echo.
echo Available mixes:
echo   1 - basic
echo   2 - deflection-attraction
echo   3 - Mix 3 (interference)
exit /b 1
