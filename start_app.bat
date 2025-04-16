@echo off
cd /d %~dp0
if not exist instance mkdir instance
set "DB_PATH=%~dp0instance\jewelry.db"
echo Veritabani yolu: %DB_PATH%
"C:\Users\USER\CursorProject\JERP\venv\Scripts\python.exe" run.py
if errorlevel 1 (
    echo Veritabani hatasi olustu! 
    echo Veritabani yolu: %DB_PATH%
    echo Lutfen instance klasorune yazma izninizin oldugundan emin olun.
    pause
) 