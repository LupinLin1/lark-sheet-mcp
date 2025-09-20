# Lark Sheet MCP Server

[![PyPI version](https://badge.fury.io/py/lark-sheet-mcp.svg)](https://badge.fury.io/py/lark-sheet-mcp)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A Model Context Protocol (MCP) server for accessing Feishu/Lark spreadsheet data. Available on PyPI for easy installation and MCP integration.

## Quick Start

1. **Install the package**:
   ```bash
   pip install lark-sheet-mcp
   ```

2. **Add to your MCP configuration** (choose one method):

   **Method 1: Using pipx (Recommended)**
   ```json
   {
     "mcpServers": {
       "lark-sheet-mcp": {
         "command": "pipx",
         "args": ["run", "lark-sheet-mcp", "--app-id", "your_app_id", "--app-secret", "your_app_secret"]
       }
     }
   }
   ```

   **Method 2: Using uv**
   ```json
   {
     "mcpServers": {
       "lark-sheet-mcp": {
         "command": "uvx", 
         "args": ["lark-sheet-mcp", "--app-id", "your_app_id", "--app-secret", "your_app_secret"]
       }
     }
   }
   ```

   **Method 3: Pre-installed**
   ```json
   {
     "mcpServers": {
       "lark-sheet-mcp": {
         "command": "lark-sheet-mcp",
         "args": ["--app-id", "your_app_id", "--app-secret", "your_app_secret"]
       }
     }
   }
   ```

3. **Start using**: The package will be automatically installed when needed (methods 1-2) or use pre-installed version (method 3)!

## Overview

This MCP server provides AI assistants with the ability to read and query Feishu (Lark) spreadsheet data through a standardized interface. It supports operations like listing spreadsheets, reading cell ranges, searching for content, and retrieving worksheet information.

## Features

- **List Spreadsheets**: Get accessible spreadsheets from user's Feishu account
- **Worksheet Information**: Retrieve worksheet details including structure and metadata
- **Range Reading**: Read single or multiple cell ranges with various formatting options
- **Cell Search**: Find cells matching specific criteria with regex support
- **Error Handling**: Comprehensive error handling with retry mechanisms for API rate limits

## Installation

### Prerequisites

- Python 3.8 or higher
- Feishu Open Platform app credentials (app_id and app_secret)

### Install from PyPI (Recommended)

The package is now available on PyPI:

```bash
pip install lark-sheet-mcp
```

### Install from GitHub

```bash
pip install git+https://github.com/LupinLin1/lark-sheet-mcp.git
```

### Development Setup

```bash
# Clone the repository
git clone https://github.com/LupinLin1/lark-sheet-mcp.git
cd lark-sheet-mcp

# Install in development mode
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

## Configuration

### MCP Client Configuration

Since the package is available on PyPI, you can configure it in your MCP client. Choose the method that best fits your setup:

**Option A: Auto-install with pipx (Recommended)**
```json
{
  "mcpServers": {
    "lark-sheet-mcp": {
      "command": "pipx",
      "args": ["run", "lark-sheet-mcp", "--app-id", "your_app_id", "--app-secret", "your_app_secret"]
    }
  }
}
```

**Option B: Auto-install with uv**
```json
{
  "mcpServers": {
    "lark-sheet-mcp": {
      "command": "uvx",
      "args": ["lark-sheet-mcp", "--app-id", "your_app_id", "--app-secret", "your_app_secret"]
    }
  }
}
```

**Option C: Use pre-installed package**
```json
{
  "mcpServers": {
    "lark-sheet-mcp": {
      "command": "lark-sheet-mcp", 
      "args": ["--app-id", "your_app_id", "--app-secret", "your_app_secret"]
    }
  }
}
```

**Note**: Replace `your_app_id` and `your_app_secret` with your actual Feishu app credentials.

See `mcp-config-example.json` for a complete configuration example.

### Environment Variables

Alternatively, set the following environment variables:

```bash
export FEISHU_APP_ID="your_app_id"
export FEISHU_APP_SECRET="your_app_secret"
```

### Command Line Arguments

Or pass them as command line arguments:

```bash
lark-sheet-mcp --app-id your_app_id --app-secret your_app_secret
```

## Usage

### Running the Server

```bash
# Using environment variables
lark-sheet-mcp

# Using command line arguments
lark-sheet-mcp --app-id your_app_id --app-secret your_app_secret

# With custom log level
lark-sheet-mcp --log-level DEBUG

# Generate sample configuration file
lark-sheet-mcp --create-config config.json
```

### Configuration Options

| Option | Environment Variable | Description | Default |
|--------|---------------------|-------------|---------|
| `--app-id` | `FEISHU_APP_ID` | Feishu app ID | Required |
| `--app-secret` | `FEISHU_APP_SECRET` | Feishu app secret | Required |
| `--config` | - | Configuration file path | None |
| `--log-level` | - | Log level (DEBUG/INFO/WARNING/ERROR) | INFO |
| `--create-config` | - | Generate sample config file | - |

### Available MCP Tools

#### 1. list_spreadsheets
Get list of accessible spreadsheets from your Feishu account.

**Parameters:**
- `folder_token` (optional): Folder token to list spreadsheets from specific folder
- `page_size` (optional): Number of spreadsheets per page (default: 50, max: 200)

**Example Response:**
```json
[
  {
    "token": "shtxxxxx",
    "name": "My Spreadsheet",
    "url": "https://example.com/sheets/shtxxxxx",
    "type": "sheet",
    "created_time": "2023-01-01T00:00:00Z",
    "modified_time": "2023-01-01T00:00:00Z",
    "owner_id": "ou_xxxxx"
  }
]
```

#### 2. get_worksheets
Get worksheets information for a specific spreadsheet.

**Parameters:**
- `spreadsheet_token` (required): Token of the spreadsheet

**Example Response:**
```json
[
  {
    "sheet_id": "sheet1",
    "title": "Sheet1",
    "index": 0,
    "row_count": 1000,
    "column_count": 26,
    "frozen_row_count": 0,
    "frozen_column_count": 0,
    "resource_type": "sheet"
  }
]
```

#### 3. read_range
Read data from a specific cell range.

**Parameters:**
- `spreadsheet_token` (required): Token of the spreadsheet
- `range_spec` (required): Range specification (e.g., "Sheet1!A1:B10")
- `value_render_option` (optional): How to render values ("ToString", "Formula", "FormattedValue", "UnformattedValue")
- `date_time_render_option` (optional): How to render dates ("FormattedString")

**Example Response:**
```json
{
  "range": "Sheet1!A1:B2",
  "major_dimension": "ROWS",
  "values": [
    ["Name", "Age"],
    ["John", "25"]
  ],
  "revision": 12345
}
```

#### 4. read_multiple_ranges
Read data from multiple cell ranges in batch.

**Parameters:**
- `spreadsheet_token` (required): Token of the spreadsheet
- `ranges` (required): List of range specifications (max 100 ranges)
- `value_render_option` (optional): How to render values
- `date_time_render_option` (optional): How to render dates

**Example Response:**
```json
[
  {
    "range": "Sheet1!A1:B2",
    "major_dimension": "ROWS",
    "values": [["Name", "Age"], ["John", "25"]],
    "revision": 12345
  },
  {
    "range": "Sheet1!C1:D2", 
    "major_dimension": "ROWS",
    "values": [["City", "Country"], ["NYC", "USA"]],
    "revision": 12345
  }
]
```

#### 5. find_cells
Search for cells matching specific criteria within a range.

**Parameters:**
- `spreadsheet_token` (required): Token of the spreadsheet
- `sheet_id` (required): ID of the worksheet
- `range_spec` (required): Range to search within (e.g., "A1:Z100")
- `find_text` (required): Text or regex pattern to search for
- `match_case` (optional): Whether to match case (default: false)
- `match_entire_cell` (optional): Whether to match entire cell content (default: false)
- `search_by_regex` (optional): Whether to use regex search (default: false)
- `include_formulas` (optional): Whether to search formulas only (default: false)

**Example Response:**
```json
{
  "matched_cells": ["A1:A1", "B5:B5"],
  "matched_formula_cells": [],
  "rows_count": 2
}
```

## Authentication Setup

### Getting Feishu App Credentials

1. Go to [Feishu Open Platform](https://open.feishu.cn/app)
2. Create a new app or use existing app
3. Get your `app_id` and `app_secret` from app settings
4. Configure app permissions for spreadsheet access:
   - `spreadsheets:read` - Read spreadsheet data
   - `drive:read` - Access file list

### Permission Requirements

The app needs the following OAuth scopes:
- `spreadsheets:read` - Read spreadsheet content
- `drive:read` - List files and folders

## Error Handling

The server implements comprehensive error handling with:

- **Automatic retry** for rate limits and temporary failures
- **Exponential backoff** for retry delays
- **Authentication refresh** when tokens expire
- **User-friendly error messages** in Chinese and English
- **Structured error responses** following MCP protocol

Common error codes:
- `1310213`: Permission denied
- `1310214`: Spreadsheet not found
- `1310215`: Worksheet not found  
- `1310216`: Invalid range format
- `1310217`: Rate limit exceeded
- `1310218`: Data size limit exceeded

## Troubleshooting

### Common Issues

#### Authentication Errors

**Problem**: `99991663 - app not found`
**Solution**: 
- Verify your `app_id` and `app_secret` are correct
- Ensure the app exists in Feishu Open Platform
- Check that credentials are properly set in environment variables

**Problem**: `1310213 - Permission denied`
**Solution**:
- Verify the app has required permissions (`spreadsheets:read`, `drive:read`)  
- Check if the user has access to the requested spreadsheet
- Ensure the spreadsheet token is correct

#### Rate Limiting

**Problem**: `1310217 - Rate limit exceeded`
**Solution**:
- The server automatically retries with exponential backoff
- Reduce request frequency if persistent
- Check rate limiter configuration

#### Data Issues

**Problem**: `1310218 - Data size limit exceeded`  
**Solution**:
- Reduce the range size (Feishu has 10MB limit per request)
- Use `read_multiple_ranges` to split large ranges
- Consider pagination for large datasets

**Problem**: `1310216 - Invalid range format`
**Solution**:
- Use correct range format: `SheetName!A1:B10`
- Ensure sheet name exists in the spreadsheet
- Check for special characters in sheet names

### Debugging

Enable debug logging to see detailed request/response information:

```bash
lark-sheet-mcp --log-level DEBUG
```

Or set environment variable:
```bash
export FEISHU_LOG_LEVEL=DEBUG
```

### Performance Tips

1. **Use batch operations**: `read_multiple_ranges` is more efficient than multiple `read_range` calls
2. **Limit range sizes**: Keep ranges under 10MB to avoid timeouts
3. **Cache tokens**: The server automatically caches authentication tokens
4. **Rate limiting**: Built-in rate limiting prevents API quota exhaustion

## Frequently Asked Questions

### Q: How do I get a spreadsheet token?
A: Use the `list_spreadsheets` tool to get tokens for accessible spreadsheets, or extract from the Feishu spreadsheet URL.

### Q: What's the maximum data size I can read?
A: Feishu APIs have a 10MB limit per request. The server will return an error if this limit is exceeded.

### Q: Can I write data to spreadsheets?
A: This server currently only supports read operations. Write operations are not implemented for security reasons.

### Q: How are authentication tokens handled?
A: The server automatically manages tenant access tokens, including refresh and caching, with a 5-minute expiration buffer.

### Q: What happens if I exceed rate limits?
A: The server implements automatic retry with exponential backoff. You don't need to handle rate limiting manually.

### Q: Can I use this with international Feishu/Lark instances?
A: Yes, the server uses the standard Feishu Open Platform APIs which work internationally.

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=feishu_spreadsheet_mcp --cov-report=html

# Run specific test file
pytest tests/test_data_models.py
```

### Code Quality

```bash
# Format code
black feishu_spreadsheet_mcp tests

# Sort imports
isort feishu_spreadsheet_mcp tests

# Lint code
flake8 feishu_spreadsheet_mcp tests

# Type checking
mypy feishu_spreadsheet_mcp
```

## Project Structure

```
feishu_spreadsheet_mcp/
├── __init__.py
├── main.py              # Entry point
├── server.py            # MCP server implementation
├── models/              # Data models
│   ├── __init__.py
│   └── data_models.py
├── services/            # Business logic
│   ├── __init__.py
│   ├── auth_manager.py  # Authentication management
│   └── api_client.py    # Feishu API client
└── tools/               # MCP tools
    ├── __init__.py
    └── spreadsheet_tools.py
```

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass and code quality checks pass
6. Submit a pull request