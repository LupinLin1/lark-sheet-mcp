#!/bin/bash
# Startup script for Feishu Spreadsheet MCP Server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    print_error "Python $PYTHON_VERSION found, but Python $REQUIRED_VERSION or higher is required."
    exit 1
fi

print_status "Using Python $PYTHON_VERSION"

# Check if .env file exists, if not create from example
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        print_warning ".env file not found. Creating from .env.example"
        cp .env.example .env
        print_warning "Please edit .env file with your Feishu app credentials before running the server."
        exit 1
    else
        print_error "No .env or .env.example file found. Please create .env with your configuration."
        exit 1
    fi
fi

# Load environment variables
if [ -f ".env" ]; then
    print_status "Loading environment variables from .env"
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if required environment variables are set
if [ -z "$FEISHU_APP_ID" ] || [ -z "$FEISHU_APP_SECRET" ]; then
    print_error "FEISHU_APP_ID and FEISHU_APP_SECRET must be set in .env file"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
print_status "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Install the package in development mode
print_status "Installing feishu-spreadsheet-mcp..."
pip install -q -e .

# Create logs directory if it doesn't exist
mkdir -p logs

# Start the server
print_status "Starting Feishu Spreadsheet MCP Server..."
print_status "App ID: ${FEISHU_APP_ID:0:10}..."
print_status "Log Level: ${FEISHU_LOG_LEVEL:-INFO}"

exec feishu-spreadsheet-mcp "$@"