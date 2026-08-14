@echo off
REM ============================================================
REM  Build Stat_Editor_GUI.exe   (run this on Windows)
REM  Requires Python 3.8+ from python.org, "Add to PATH" ticked.
REM ============================================================
setlocal

echo.
echo [1/4] Creating virtual environment...
if not exist .venv (
    py -3 -m venv .venv || goto :error
)

echo [2/4] Installing dependencies...
call .venv\Scripts\activate.bat || goto :error
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt || goto :error

echo [3/4] Running self-test...
python selftest.py || goto :error

echo [4/4] Building executable...
pyinstaller Stat_Editor_GUI.spec --noconfirm --clean || goto :error

echo.
echo ==========================================================================
echo   Done. Your exe is located: dist\Stat_Editor_GUI.exe
echo.
echo   Copy bpe.exe next to it if you want to save files.
echo ==========================================================================
echo.
pause
exit /b 0

:error
echo.
echo *** BUILD FAILED - see the messages above. ***
pause
exit /b 1
