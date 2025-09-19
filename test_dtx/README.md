# Feishu Spreadsheet MCP Server (FastMCP)

This is a FastMCP-based MCP server for accessing Feishu/Lark spreadsheet data.

## Installation

1. Install Python dependencies:
   ```bash
   pip install fastmcp pydantic python-dotenv
   ```

2. Set environment variables:
   - `FEISHU_APP_ID`: Your Feishu application ID
   - `FEISHU_APP_SECRET`: Your Feishu application secret

3. Run the server:
   ```bash
   python startup.py
   ```

## Features

- List spreadsheets
- Get worksheets 
- Read cell ranges
- Read multiple ranges
- Find cells with regex support

Built with FastMCP framework for improved performance and developer experience.
