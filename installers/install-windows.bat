@echo off
setlocal
cd /d "%~dp0\.."

echo ========================================================
echo   DYZ MedPaper - Medical Paper Skills Installer (Windows)
echo ========================================================
echo.

set "PY="
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 set "PY=py -3"
if defined PY goto :py_ok
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 set "PY=python"
if defined PY goto :py_ok
python3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 set "PY=python3"
if defined PY goto :py_ok
echo [ERROR] Python 3.10+ not found. Please install from https://www.python.org/downloads/ and check Add Python to PATH.
if not defined DYZ_MED_NONINTERACTIVE pause
exit /b 2

:py_ok
set "CUSTOM_TARGET=%DYZ_MED_CUSTOM_TARGET%"
set "CHOICE=%DYZ_MED_HOST_CHOICE%"
if defined CUSTOM_TARGET goto :ask_pack
if defined CHOICE goto :ask_pack
if defined DYZ_MED_NONINTERACTIVE goto :ask_pack
echo Select target AI agent host:
echo   [1] Claude Code    - %USERPROFILE%\.claude\skills
echo   [2] Codex          - %USERPROFILE%\.agents\skills
echo   [3] Cursor         - %USERPROFILE%\.cursor\skills
echo   [4] GitHub Copilot - %USERPROFILE%\.copilot\skills
echo   [5] Gemini CLI     - %USERPROFILE%\.gemini\skills
echo   [6] Claude Code + Codex [recommended]
echo.
set /p "CHOICE=Enter [1-6] and press Enter [default 6]: "

:ask_pack
if not defined CHOICE set "CHOICE=6"
set "PACK=%DYZ_MED_PACK%"
if defined PACK goto :do_install
if defined DYZ_MED_NONINTERACTIVE goto :do_install
echo.
echo Select skill pack:
echo   [1] all      - all 32 skills
echo   [2] start    - 5 skills
echo   [3] evidence - 7 skills
echo   [4] analysis - 5 skills
echo   [5] writing  - 7 skills
echo   [6] delivery - 8 skills
set /p "PCHOICE=Enter [1-6] and press Enter [default 1]: "
if "%PCHOICE%"=="2" set "PACK=start"
if "%PCHOICE%"=="3" set "PACK=evidence"
if "%PCHOICE%"=="4" set "PACK=analysis"
if "%PCHOICE%"=="5" set "PACK=writing"
if "%PCHOICE%"=="6" set "PACK=delivery"

:do_install
if not defined PACK set "PACK=all"
if defined CUSTOM_TARGET (
    call :install_one "%CUSTOM_TARGET%"
    if errorlevel 1 goto :fail
    goto :ok
)
if "%CHOICE%"=="1" goto :h1
if "%CHOICE%"=="2" goto :h2
if "%CHOICE%"=="3" goto :h3
if "%CHOICE%"=="4" goto :h4
if "%CHOICE%"=="5" goto :h5
call :install_one "%USERPROFILE%\.claude\skills"
if errorlevel 1 goto :fail
call :install_one "%USERPROFILE%\.agents\skills"
if errorlevel 1 goto :fail
goto :ok
:h1
call :install_one "%USERPROFILE%\.claude\skills"
if errorlevel 1 goto :fail
goto :ok
:h2
call :install_one "%USERPROFILE%\.agents\skills"
if errorlevel 1 goto :fail
goto :ok
:h3
call :install_one "%USERPROFILE%\.cursor\skills"
if errorlevel 1 goto :fail
goto :ok
:h4
call :install_one "%USERPROFILE%\.copilot\skills"
if errorlevel 1 goto :fail
goto :ok
:h5
call :install_one "%USERPROFILE%\.gemini\skills"
if errorlevel 1 goto :fail
goto :ok

:ok
echo.
echo Installation and verification PASSED [pack=%PACK%]. Restart your agent host to load skills.
if not defined DYZ_MED_NONINTERACTIVE pause
exit /b 0

:fail
echo.
echo [ERROR] Installation or verification FAILED. Check the error message above.
if not defined DYZ_MED_NONINTERACTIVE pause
exit /b 1

:install_one
echo Installing pack=%PACK% into %~1 ...
%PY% scripts\install_codex.py --pack "%PACK%" --target "%~1"
if errorlevel 1 exit /b 1
%PY% scripts\install_codex.py --pack "%PACK%" --target "%~1" --check
if errorlevel 1 exit /b 1
exit /b 0
