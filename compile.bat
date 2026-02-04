@echo off
REM === Check for Python ===
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo Python is not installed or not in PATH. Please install Python 3.9+ and try again.
    pause
    exit /b
)

echo Creating virtual environment...
python -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate

echo Installing requirements...
pip install --upgrade pip
pip install PySide6 requests pyinstaller

echo Compiling main.py into standalone EXE...
pyinstaller --onefile --windowed --add-data "assets\app.ico;assets" --icon=assets\app.ico --noconsole --name VehicleLookup main.py

echo Cleaning up build junk...
rmdir /s /q build
rmdir /s /q venv
del /q VehicleLookup.spec

echo Done! Your compiled EXE is in the /dist folder.
pause