@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title Building VaultLite
echo ============================================
echo   VaultLite - automatic build (installer + exe)
echo ============================================

rem ---- 1. Find Python 3.12 (never calls the Microsoft Store "python" shortcut) ----
echo [1/4] Looking for Python 3.12 ...
set "PY="
where py >nul 2>&1 && py -3.12 -c "import sys" >nul 2>&1 && set "PY=py -3.12"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY if exist "%ProgramFiles%\Python312\python.exe" set PY="%ProgramFiles%\Python312\python.exe"
if not defined PY (
  echo Python 3.12 not found - installing it with winget, please wait ...
  winget install -e --id Python.Python.3.12 --silent --disable-interactivity --accept-package-agreements --accept-source-agreements
  if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  if exist "%ProgramFiles%\Python312\python.exe" set PY="%ProgramFiles%\Python312\python.exe"
)
if not defined PY (
  echo.
  echo Could not set up Python 3.12 automatically.
  echo Install it from https://www.python.org/downloads/release/python-3128/ ^(tick "Add python.exe to PATH"^),
  echo then double-click build.bat again.
  pause & exit /b 1
)
echo Using: %PY%

rem ---- 2. Private build environment + dependencies ----
echo [2/4] Installing libraries (1-3 minutes) ...
if not exist .buildenv\Scripts\python.exe ( %PY% -m venv .buildenv || goto :fail )
call .buildenv\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt || goto :fail
pip install --quiet pyinstaller==6.10.0 || goto :fail

rem ---- 3. Build the app (dist\VaultLite\VaultLite.exe) ----
echo [3/4] Building the app ...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
pyinstaller --noconfirm VaultLite.spec || goto :fail

rem ---- 4. Build the installer with Inno Setup (install it automatically if missing) ----
echo [4/4] Building the installer ...
for /f "delims=" %%v in ('python -c "import product;print(product.APP_VERSION)"') do set "APPVER=%%v"
for /f "delims=" %%v in ('python -c "import product;print(product.PUBLISHER)"') do set "PUBL=%%v"
call :findiscc
if not defined ISCC (
  echo Inno Setup not found - installing it with winget...
  winget install -e --id JRSoftware.InnoSetup --silent --disable-interactivity --accept-package-agreements --accept-source-agreements
  call :findiscc
)
if not defined ISCC (
  echo Could not find Inno Setup. Your app is still ready in dist\VaultLite\
  goto :done
)
"%ISCC%" /Qp "/DAppVersion=%APPVER%" "/DPublisher=%PUBL%" installer\VaultLite.iss || goto :fail

:done
echo.
echo ============================================
echo   DONE.  Your product is in the "release" folder:
echo   release\VaultLite-Setup-%APPVER%.exe   ^<-- sell / send THIS file
echo ============================================
explorer release 2>nul
pause
exit /b 0

:findiscc
set "ISCC="
for %%p in ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe" "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe") do if exist %%p set "ISCC=%%~p"
exit /b 0

:fail
echo.
echo BUILD FAILED - scroll up to see the error.
pause
exit /b 1
