@echo off
REM Startup script for Feishu Spreadsheet MCP Server (Windows)

setlocal EnableDelayedExpansion

echo [INFO] Starting Feishu Spreadsheet MCP Server...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist ".env" (
    if exist ".env.example" (
        echo [WARN] .env file not found. Creating from .env.example
        copy .env.example .env
        echo [WARN] Please edit .env file with your Feishu app credentials before running the server.
        pause
        exit /b 1
    ) else (
        echo [ERROR] No .env or .env.example file found.
        echo Please create .env with your configuration.
        pause
        exit /b 1
    )
)

REM Load environment variables from .env file
for /f "tokens=1,2 delims==" %%a in ('type .env ^| findstr /v "^#"') do (
    set "%%a=%%b"
)

REM Check required environment variables
if "%FEISHU_APP_ID%"=="" (
    echo [ERROR] FEISHU_APP_ID must be set in .env file
    pause
    exit /b 1
)

if "%FEISHU_APP_SECRET%"=="" (
    echo [ERROR] FEISHU_APP_SECRET must be set in .env file
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/update dependencies
echo [INFO] Installing dependencies...
pip install -q --upgrade pip
pip install -q -r requirements.txt

REM Install the package in development mode
echo [INFO] Installing feishu-spreadsheet-mcp...
pip install -q -e .

REM Create logs directory
if not exist "logs" mkdir logs

REM Start the server
echo [INFO] Starting server with:
echo   App ID: %FEISHU_APP_ID:~0,10%...
echo   Log Level: %FEISHU_LOG_LEVEL%

feishu-spreadsheet-mcp %*