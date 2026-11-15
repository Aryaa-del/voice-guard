@echo off
setlocal
cd /d "%~dp0"
set "PIP_NO_INDEX=0"
set "PIP_CONFIG_FILE=NUL"
if not exist ".venv\Scripts\python.exe" python -m venv .venv
if errorlevel 1 goto failed
if exist ".venv\windows-ca.pem" set "PIP_CERT=%CD%\.venv\windows-ca.pem"
".venv\Scripts\python.exe" -m pip install --upgrade pip --index-url https://pypi.org/simple
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt --index-url https://pypi.org/simple
if errorlevel 1 goto failed
".venv\Scripts\python.exe" download_model.py
if errorlevel 1 goto failed
echo Setup complete. Double-click start.bat.
pause
exit /b 0
:failed
echo Setup did not finish. Check the error above, then try setup.bat again.
pause
exit /b 1
