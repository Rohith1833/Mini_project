@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set "PYTHON=py") else (set "PYTHON=python")
if not exist .venv\Scripts\python.exe %PYTHON% -m venv .venv
if not exist .venv\Scripts\python.exe goto fail
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m streamlit run app.py
pause
exit /b
:fail
echo Setup failed. Install Python 3.12 with PATH enabled and check your internet connection.
pause
