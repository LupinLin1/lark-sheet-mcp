# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Testing
```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=feishu_spreadsheet_mcp --cov-report=html

# Run specific test file
pytest tests/test_data_models.py
```

### Code Quality
```bash
# Format code with Black
black feishu_spreadsheet_mcp tests

# Sort imports with isort
isort feishu_spreadsheet_mcp tests

# Lint with flake8
flake8 feishu_spreadsheet_mcp tests

# Type checking with mypy
mypy feishu_spreadsheet_mcp
```

### Installation and Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

### Running the Server
```bash
# Using environment variables (FEISHU_APP_ID, FEISHU_APP_SECRET)
feishu-spreadsheet-mcp

# Using command line arguments
feishu-spreadsheet-mcp --app-id your_app_id --app-secret your_app_secret
```

## Architecture Overview

This is a Model Context Protocol (MCP) server for accessing Feishu/Lark spreadsheet data. The architecture follows a clean separation of concerns:

### Core Components

- **`main.py`**: Entry point with CLI argument parsing and configuration management
- **`server.py`**: Main MCP server class that coordinates all operations
- **`services/`**: Business logic layer
  - `auth_manager.py`: Handles Feishu OAuth authentication and token management
  - `api_client.py`: HTTP client wrapper for Feishu API interactions
- **`models/`**: Data models and validation
  - `data_models.py`: Pydantic models for API requests/responses
  - `error_handling.py`: Custom exception classes
- **`tools/`**: MCP tool implementations
  - `spreadsheet_tools.py`: Spreadsheet-specific operations

### MCP Tools Available

1. `list_spreadsheets`: Get accessible spreadsheets from user's account
2. `get_worksheets`: Retrieve worksheets for a specific spreadsheet
3. `read_range`: Read single cell range data
4. `read_multiple_ranges`: Batch read multiple cell ranges
5. `find_cells`: Search cells with regex support

### Configuration

The server requires Feishu app credentials:
- Environment variables: `FEISHU_APP_ID`, `FEISHU_APP_SECRET`
- Command line: `--app-id`, `--app-secret`

### Code Style Configuration

- **Black**: Line length 88, Python 3.8+ target
- **isort**: Black-compatible profile
- **mypy**: Strict type checking enabled
- **pytest**: Auto coverage with HTML reports