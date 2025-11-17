REM ...existing code...
@echo off
REM start.bat — run app.py from the current folder

pushd "%~dp0"

if not exist "app.py" (
  echo app.py not found in "%cd%"
  pause
  popd
  exit /b 1
)

echo Starting app.py in a new window...
REM Try to use the py launcher first, fall back to python
where py >nul 2>&1
if %ERRORLEVEL%==0 (
  start "Flask" py -3 "app.py"
) else (
  where python >nul 2>&1
  if %ERRORLEVEL%==0 (
    start "Flask" python "app.py"
  ) else (
    echo Failed to start Python. Make sure Python is installed and on PATH.
    pause
    popd
    exit /b 1
  )
)

REM Give the server a moment to start, then open the default browser
timeout /t 1 /nobreak >nul
echo Opening browser http://127.0.0.1:5000/ ...
start "" "http://127.0.0.1:5000/"

popd
REM ...existing code...