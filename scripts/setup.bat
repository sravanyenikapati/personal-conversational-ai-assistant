@echo off
:: ──────────────────────────────────────────────────────────────────────────────
:: setup.bat — One-shot project setup for Windows
:: Run: scripts\setup.bat  (from the project root)
:: ──────────────────────────────────────────────────────────────────────────────

title Personal AI Assistant — Setup
color 0B

echo.
echo  ============================================
echo   ^|^|  Personal AI Assistant — Windows Setup
echo  ============================================
echo.

:: ── Check Python is installed ─────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Download it from https://python.org
    echo         Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version') do echo [OK] %%v detected

:: ── Create virtual environment ────────────────────────────────────────────────
if not exist ".venv\" (
    echo [ ] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment already exists
)

:: ── Activate virtual environment ──────────────────────────────────────────────
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)
echo [OK] Virtual environment activated

:: ── Upgrade pip ───────────────────────────────────────────────────────────────
echo [ ] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo [OK] pip up to date

:: ── Install dependencies ──────────────────────────────────────────────────────
echo [ ] Installing dependencies (this may take a minute)...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo.
    echo [WARN] Some packages may have failed. Common fix:
    echo        PyAudio on Windows needs a pre-built wheel. Run:
    echo        pip install pipwin ^&^& pipwin install pyaudio
    echo.
) else (
    echo [OK] All dependencies installed
)

:: ── Copy .env template if not present ─────────────────────────────────────────
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo [OK] .env created from .env.example
    echo.
    echo  *** ACTION REQUIRED ***
    echo  Open .env in a text editor and set your OPENAI_API_KEY
    echo  Example:  OPENAI_API_KEY=sk-...your-key-here...
    echo.
) else (
    echo [OK] .env already exists
)

:: ── Done ──────────────────────────────────────────────────────────────────────
echo.
echo  ============================================
echo   Setup complete!
echo  ============================================
echo.
echo  Next steps:
echo    1. Open .env and add your OPENAI_API_KEY
echo    2. To launch the assistant, run:
echo         python main.py
echo    3. To run in terminal mode:
echo         python main.py --cli
echo    4. To run tests:
echo         pip install -r requirements-dev.txt
echo         pytest
echo.
echo  Note: Always activate your venv first:
echo        .venv\Scripts\activate
echo.
pause
