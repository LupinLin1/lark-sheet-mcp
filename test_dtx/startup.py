#!/usr/bin/env python3
"""
Simple startup script for FastMCP Feishu Spreadsheet MCP Server.
Assumes fastmcp is already installed on the system.
"""

import sys
import os

# Ensure we can import our package
sys.path.insert(0, os.path.dirname(__file__))

try:
    from feishu_spreadsheet_mcp.main import main
    if __name__ == "__main__":
        main()
except ImportError as e:
    print(f"Error: Required dependencies not found: {e}", file=sys.stderr)
    print("Please install: pip install fastmcp pydantic python-dotenv", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error starting server: {e}", file=sys.stderr)
    sys.exit(1)
