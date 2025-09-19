#!/usr/bin/env python3
"""
Create DTX package using standard MCP protocol (without FastMCP dependency).
"""

import os
import shutil
import json
import zipfile
import subprocess
import sys
from pathlib import Path


def create_standard_mcp_server_file(build_dir):
    """Create a standard MCP server implementation."""
    print("Creating standard MCP server...")
    
    server_content = '''"""
Standard MCP server implementation for Feishu Spreadsheet.
Uses official MCP Python SDK instead of FastMCP.
"""

import json
import sys
import asyncio
import logging
from typing import Any, Dict, List, Optional

from mcp import McpError
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool, 
    TextContent,
    CallToolRequest,
    CallToolResult,
    ListToolsRequest
)
from pydantic import BaseModel

from .services import AuthenticationManager, FeishuAPIClient
from .tools import spreadsheet_tools

logger = logging.getLogger(__name__)


# Request models
class ListSpreadsheetsRequest(BaseModel):
    folder_token: Optional[str] = None
    page_size: int = 50


class GetWorksheetsRequest(BaseModel):
    spreadsheet_token: str


class ReadRangeRequest(BaseModel):
    spreadsheet_token: str
    range_spec: str
    value_render_option: str = "UnformattedValue"
    date_time_render_option: str = "FormattedString"


class ReadMultipleRangesRequest(BaseModel):
    spreadsheet_token: str
    ranges: List[str]
    value_render_option: str = "UnformattedValue"
    date_time_render_option: str = "FormattedString"


class FindCellsRequest(BaseModel):
    spreadsheet_token: str
    sheet_id: str
    range_spec: str
    find_text: str
    match_case: bool = False
    match_entire_cell: bool = False
    search_by_regex: bool = False
    include_formulas: bool = False


async def run_server(app_id: str, app_secret: str):
    """Run the standard MCP server."""
    
    # Initialize API components
    auth_manager = AuthenticationManager(app_id, app_secret)
    api_client = FeishuAPIClient(auth_manager)
    
    # List tools handler
    async def list_tools() -> list[Tool]:
        """Return available tools."""
        return [
            Tool(
                name="list_spreadsheets",
                description="Get accessible spreadsheets from user's account", 
                inputSchema={
                    "type": "object",
                    "properties": {
                        "folder_token": {"type": "string", "description": "Optional folder token to filter results"},
                        "page_size": {"type": "integer", "description": "Number of results per page (default 50)", "default": 50}
                    }
                }
            ),
            Tool(
                name="get_worksheets",
                description="Retrieve worksheets for a specific spreadsheet",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_token": {"type": "string", "description": "The spreadsheet token"}
                    },
                    "required": ["spreadsheet_token"]
                }
            ),
            Tool(
                name="read_range",
                description="Read single cell range data",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_token": {"type": "string", "description": "The spreadsheet token"},
                        "range_spec": {"type": "string", "description": "Range specification (e.g., 'Sheet1!A1:B10')"},
                        "value_render_option": {"type": "string", "description": "Value render option", "default": "UnformattedValue"},
                        "date_time_render_option": {"type": "string", "description": "Date time render option", "default": "FormattedString"}
                    },
                    "required": ["spreadsheet_token", "range_spec"]
                }
            ),
            Tool(
                name="read_multiple_ranges", 
                description="Batch read multiple cell ranges",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_token": {"type": "string", "description": "The spreadsheet token"},
                        "ranges": {"type": "array", "items": {"type": "string"}, "description": "List of range specifications"},
                        "value_render_option": {"type": "string", "description": "Value render option", "default": "UnformattedValue"},
                        "date_time_render_option": {"type": "string", "description": "Date time render option", "default": "FormattedString"}
                    },
                    "required": ["spreadsheet_token", "ranges"]
                }
            ),
            Tool(
                name="find_cells",
                description="Search cells with regex support",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_token": {"type": "string", "description": "The spreadsheet token"},
                        "sheet_id": {"type": "string", "description": "The sheet ID"},
                        "range_spec": {"type": "string", "description": "Range specification to search within"},
                        "find_text": {"type": "string", "description": "Text to search for"},
                        "match_case": {"type": "boolean", "description": "Case sensitive search", "default": False},
                        "match_entire_cell": {"type": "boolean", "description": "Match entire cell content", "default": False},
                        "search_by_regex": {"type": "boolean", "description": "Use regex search", "default": False},
                        "include_formulas": {"type": "boolean", "description": "Include formulas in search", "default": False}
                    },
                    "required": ["spreadsheet_token", "sheet_id", "range_spec", "find_text"]
                }
            )
        ]
    
    # Call tool handler  
    async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
        """Handle tool calls."""
        try:
            result = None
            
            if name == "list_spreadsheets":
                args = ListSpreadsheetsRequest(**arguments)
                result = await spreadsheet_tools.list_spreadsheets(
                    api_client,
                    folder_token=args.folder_token,
                    page_size=args.page_size
                )
            elif name == "get_worksheets":
                args = GetWorksheetsRequest(**arguments)
                result = await spreadsheet_tools.get_worksheets(
                    api_client,
                    spreadsheet_token=args.spreadsheet_token
                )
            elif name == "read_range":
                args = ReadRangeRequest(**arguments)
                result = await spreadsheet_tools.read_range(
                    api_client,
                    spreadsheet_token=args.spreadsheet_token,
                    range_spec=args.range_spec,
                    value_render_option=args.value_render_option,
                    date_time_render_option=args.date_time_render_option
                )
            elif name == "read_multiple_ranges":
                args = ReadMultipleRangesRequest(**arguments)
                result = await spreadsheet_tools.read_multiple_ranges(
                    api_client,
                    spreadsheet_token=args.spreadsheet_token,
                    ranges=args.ranges,
                    value_render_option=args.value_render_option,
                    date_time_render_option=args.date_time_render_option
                )
            elif name == "find_cells":
                args = FindCellsRequest(**arguments)
                result = await spreadsheet_tools.find_cells(
                    api_client,
                    spreadsheet_token=args.spreadsheet_token,
                    sheet_id=args.sheet_id,
                    range_spec=args.range_spec,
                    find_text=args.find_text,
                    match_case=args.match_case,
                    match_entire_cell=args.match_entire_cell,
                    search_by_regex=args.search_by_regex,
                    include_formulas=args.include_formulas
                )
            else:
                raise McpError(f"Unknown tool: {name}")
            
            # Format result as TextContent
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
                
        except Exception as e:
            logger.error(f"Tool call failed: {e}")
            raise McpError(f"Tool execution failed: {str(e)}")
    
    # Run stdio server
    await stdio_server(list_tools, call_tool)
'''
    
    # Write standard MCP server
    server_file = build_dir / "feishu_spreadsheet_mcp" / "standard_server.py"
    server_file.write_text(server_content)
    print("✓ Standard MCP server created")
    return True


def create_standard_main_file(build_dir):
    """Create main entry point using standard MCP."""
    print("Creating standard main file...")
    
    main_content = '''"""
Main entry point for Standard MCP Feishu Spreadsheet server.
"""

import argparse
import asyncio
import logging
import sys
import os
from typing import Optional

from .config import config_manager
from .standard_server import run_server


async def run_standard_server(
    app_id: Optional[str] = None,
    app_secret: Optional[str] = None,
    config_file: Optional[str] = None,
) -> None:
    """
    Run the standard MCP server.
    """
    try:
        # Load configuration if available
        if config_file or not (app_id and app_secret):
            config = config_manager.load_config(app_id, app_secret, config_file)
            app_id = app_id or config.app_id
            app_secret = app_secret or config.app_secret

        # Setup logging to stderr only (preserve stdout for MCP protocol)
        logging.basicConfig(
            level=logging.WARNING,
            format='%(levelname)s: %(message)s',
            stream=sys.stderr
        )

        # Validate credentials
        if not app_id or not app_secret:
            raise ValueError("Missing app_id or app_secret")

        logger = logging.getLogger(__name__)
        logger.info(f"Standard MCP Server starting with app_id: {app_id[:8]}...")

        # Run server
        await run_server(app_id, app_secret)
        
    except Exception as e:
        print(f"Failed to start server: {e}", file=sys.stderr)
        raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Feishu Spreadsheet Standard MCP Server")
    parser.add_argument("--app-id", help="Feishu app ID")
    parser.add_argument("--app-secret", help="Feishu app secret") 
    parser.add_argument("--config", help="Configuration file path")

    args = parser.parse_args()

    try:
        # Get credentials from args or environment
        app_id = args.app_id or os.getenv('FEISHU_APP_ID')
        app_secret = args.app_secret or os.getenv('FEISHU_APP_SECRET')
        
        if not app_id or not app_secret:
            print("Error: FEISHU_APP_ID and FEISHU_APP_SECRET are required", file=sys.stderr)
            sys.exit(1)

        # Run server
        asyncio.run(run_standard_server(app_id, app_secret, args.config))

    except KeyboardInterrupt:
        print("Shutting down server...", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
'''
    
    # Write standard main
    main_file = build_dir / "feishu_spreadsheet_mcp" / "standard_main.py"
    main_file.write_text(main_content)
    print("✓ Standard main file created")
    return True


def install_standard_mcp_dependencies(build_dir):
    """Install standard MCP dependencies."""
    print("Installing standard MCP dependencies...")
    
    lib_dir = build_dir / "lib"
    lib_dir.mkdir(parents=True, exist_ok=True)
    
    # Install mcp package instead of fastmcp
    packages = ["mcp>=1.0.0", "pydantic>=2.0.0", "python-dotenv>=1.0.0", "httpx", "anyio"]
    
    cmd = [
        sys.executable, "-m", "pip", "install",
        "--target", str(lib_dir),
        "--no-user",
        "--no-cache-dir",
        "--upgrade",
        "--timeout", "180"
    ] + packages
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=200)
    if result.returncode != 0:
        print(f"Standard MCP installation failed: {result.stderr}")
        return False
        
    print("✓ Standard MCP dependencies installed")
    return True


def create_standard_dtx():
    """Create DTX package with standard MCP implementation."""
    print("=== Creating Standard MCP DTX Package ===")
    
    build_dir = Path("dtx-standard-build")
    output_name = "feishu-spreadsheet-mcp-standard.dxt"
    
    # Clean build directory
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)
    
    try:
        # 1. Copy source code
        print("Copying source code...")
        src_pkg = Path("feishu_spreadsheet_mcp")
        dst_pkg = build_dir / "feishu_spreadsheet_mcp"
        shutil.copytree(src_pkg, dst_pkg)
        print("✓ Source code copied")
        
        # 2. Create standard MCP implementations
        if not create_standard_mcp_server_file(build_dir):
            return False
        if not create_standard_main_file(build_dir):
            return False
            
        # 3. Install dependencies
        if not install_standard_mcp_dependencies(build_dir):
            return False
            
        # 4. Create manifest
        print("Creating manifest...")
        with open("manifest.json", 'r') as f:
            manifest = json.load(f)
            
        manifest["server"]["mcp_config"]["args"] = ["${__dirname}/startup_standard.py"]
        manifest["version"] = "1.1.0-standard-mcp"
        manifest["dtx_info"] = {
            "type": "standard",
            "framework": "standard-mcp",
            "includes_dependencies": True,
            "notes": "Uses official MCP Python SDK"
        }
        
        with open(build_dir / "manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)
        print("✓ Manifest created")
        
        # 5. Create startup script
        print("Creating startup script...")
        startup_content = '''#!/usr/bin/env python3
"""
Standard MCP startup script for Feishu Spreadsheet server.
"""

import sys
import os
from pathlib import Path

# Setup paths
current_dir = Path(__file__).parent
lib_dir = current_dir / "lib"
sys.path.insert(0, str(lib_dir))
sys.path.insert(0, str(current_dir))

# Ensure stdout/stderr are line buffered
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

try:
    # Check environment
    app_id = os.getenv('FEISHU_APP_ID')
    app_secret = os.getenv('FEISHU_APP_SECRET')
    
    if not app_id or not app_secret:
        print("Error: FEISHU_APP_ID and FEISHU_APP_SECRET environment variables are required", file=sys.stderr)
        sys.exit(1)
    
    # Import and run standard main
    from feishu_spreadsheet_mcp.standard_main import main
    main()
    
except ImportError as e:
    print(f"Import error: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Server error: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''
        
        (build_dir / "startup_standard.py").write_text(startup_content)
        print("✓ Startup script created")
        
        # 6. Create README
        readme_content = """# Feishu Spreadsheet MCP Server (Standard MCP)

This package uses the official MCP Python SDK for maximum compatibility.

## Features
- Standard MCP protocol compliance
- All spreadsheet operations supported
- Better compatibility with MCP clients
- Self-contained with dependencies

## Configuration
Set environment variables:
- FEISHU_APP_ID: Your Feishu application ID
- FEISHU_APP_SECRET: Your Feishu application secret

Built with official MCP Python SDK for reliable stdio transport.
"""
        (build_dir / "README.md").write_text(readme_content)
        print("✓ README created")
        
        # 7. Create DTX package
        print(f"Creating DTX package: {output_name}")
        with zipfile.ZipFile(output_name, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(build_dir):
                for file in files:
                    file_path = Path(root) / file
                    arc_path = file_path.relative_to(build_dir)
                    zf.write(file_path, arc_path)
        
        file_size = Path(output_name).stat().st_size / 1024 / 1024
        print(f"✓ Standard MCP DTX package created: {output_name} ({file_size:.1f} MB)")
        
        # 8. Cleanup
        shutil.rmtree(build_dir)
        print("✓ Build directory cleaned")
        
        print(f"\n✅ Standard MCP DTX package created successfully!")
        print(f"📦 Package: {output_name} ({file_size:.1f} MB)")
        print(f"🚀 Uses official MCP SDK for better compatibility")
        
        return True
        
    except Exception as e:
        print(f"❌ Build failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = create_standard_dtx()
    sys.exit(0 if success else 1)