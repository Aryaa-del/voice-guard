@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto missing
if not exist "models\voice-detector-bgeorge\model.safetensors" goto missing
echo Starting Voice Guard with the trained detection model.
echo Open http://localhost:8000 in your browser. Keep this window open.
".venv\Scripts\python.exe" app.py
pause
exit /b
:missing
echo First run setup.bat to install the trained voice detection model.
pause
