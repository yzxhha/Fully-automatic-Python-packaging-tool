@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%scripts\ensure_python_windows.ps1"
if errorlevel 1 (
  echo.
  echo Python setup or application launch failed. See the message above.
  pause
  exit /b 1
)
endlocal
