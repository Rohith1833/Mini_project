@echo off
cd /d "%~dp0"
set "VENV=.venv"
if exist .venv\Scripts\python.exe (
	.venv\Scripts\python.exe -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)"
	if errorlevel 1 set "VENV=.venv312"
)
if not exist "%VENV%\Scripts\python.exe" (
	where py >nul 2>nul
	if errorlevel 1 goto pythonfail
	py -3.12 -m venv "%VENV%"
	if errorlevel 1 goto pythonfail
)
"%VENV%\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail
"%VENV%\Scripts\python.exe" -m streamlit run app.py
pause
exit /b
:pythonfail
echo Python 3.12 was not found. Install Python 3.12, then run this launcher again.
pause
exit /b 1
:fail
echo Setup failed. Check the error above and your internet connection.
pause
exit /b 1
