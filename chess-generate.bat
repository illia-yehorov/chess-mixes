@echo off
setlocal

set "MIX=%~1"
set "CONFIG="

if "%MIX%"=="1" set "CONFIG=1-basic"
if "%MIX%"=="2" set "CONFIG=2-deflection-attraction"
if "%MIX%"=="3" set "CONFIG=3-interference"
if "%MIX%"=="4" set "CONFIG=4-clearance"

if not defined CONFIG goto :usage

python "%~dp0chess\generate_mix.py" "%CONFIG%"
exit /b %errorlevel%

:usage
echo Usage: chess-generate ^<mix-number^>
echo.
echo Available mixes:
echo   1 - basic
echo   2 - deflection-attraction
echo   3 - interference
echo   4 - clearance
exit /b 1
