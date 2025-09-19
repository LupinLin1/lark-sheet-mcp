#!/usr/bin/env python3
"""
Create DTX package using FastMCP with SSE transport for better compatibility.
"""

import os
import shutil
import json
import zipfile
import subprocess
import sys
from pathlib import Path


def create_sse_server_file(build_dir):
    """Create FastMCP server with SSE transport support."""
    print("Creating SSE transport server...")
    
    server_content = '''"""
FastMCP server with SSE transport for Feishu Spreadsheet.
SSE (Server-Sent Events) provides better compatibility than stdio transport.
"""

import logging
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from pydantic import BaseModel

from .services import AuthenticationManager, FeishuAPIClient
from .tools import spreadsheet_tools

logger = logging.getLogger(__name__)


class ListSpreadsheetsArgs(BaseModel):
    folder_token: Optional[str] = None
    page_size: int = 50


class GetWorksheetsArgs(BaseModel):
    spreadsheet_token: str


class ReadRangeArgs(BaseModel):
    spreadsheet_token: str
    range_spec: str
    value_render_option: str = "UnformattedValue"
    date_time_render_option: str = "FormattedString"


class ReadMultipleRangesArgs(BaseModel):
    spreadsheet_token: str
    ranges: List[str]
    value_render_option: str = "UnformattedValue"
    date_time_render_option: str = "FormattedString"


class FindCellsArgs(BaseModel):
    spreadsheet_token: str
    sheet_id: str
    range_spec: str
    find_text: str
    match_case: bool = False
    match_entire_cell: bool = False
    search_by_regex: bool = False
    include_formulas: bool = False


class FeishuSpreadsheetSSEServer:
    """Feishu Spreadsheet MCP server with SSE transport."""

    def __init__(self, app_id: str, app_secret: str, host: str = "127.0.0.1", port: int = 8000):
        """
        Initialize SSE MCP server.
        
        Args:
            app_id: Feishu app ID
            app_secret: Feishu app secret  
            host: Server host (default: 127.0.0.1)
            port: Server port (default: 8000)
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.host = host
        self.port = port
        
        self.auth_manager = AuthenticationManager(app_id, app_secret)
        self.api_client = FeishuAPIClient(self.auth_manager)

        # Initialize FastMCP
        self.mcp = FastMCP("feishu-spreadsheet-mcp-sse")

        # Register tools
        self._register_tools()

    def _register_tools(self):
        """Register all tools"""

        @self.mcp.tool()
        async def list_spreadsheets(args: ListSpreadsheetsArgs) -> Dict[str, Any]:
            """Get accessible spreadsheets list"""
            return await spreadsheet_tools.list_spreadsheets(
                self.api_client,
                folder_token=args.folder_token,
                page_size=args.page_size,
            )

        @self.mcp.tool()
        async def get_worksheets(args: GetWorksheetsArgs) -> Dict[str, Any]:
            """Get worksheets for specified spreadsheet"""
            return await spreadsheet_tools.get_worksheets(
                self.api_client, spreadsheet_token=args.spreadsheet_token
            )

        @self.mcp.tool()
        async def read_range(args: ReadRangeArgs) -> Dict[str, Any]:
            """Read cell range data"""
            return await spreadsheet_tools.read_range(
                self.api_client,
                spreadsheet_token=args.spreadsheet_token,
                range_spec=args.range_spec,
                value_render_option=args.value_render_option,
                date_time_render_option=args.date_time_render_option,
            )

        @self.mcp.tool()
        async def read_multiple_ranges(args: ReadMultipleRangesArgs) -> Dict[str, Any]:
            """Batch read multiple ranges"""
            return await spreadsheet_tools.read_multiple_ranges(
                self.api_client,
                spreadsheet_token=args.spreadsheet_token,
                ranges=args.ranges,
                value_render_option=args.value_render_option,
                date_time_render_option=args.date_time_render_option,
            )

        @self.mcp.tool()
        async def find_cells(args: FindCellsArgs) -> Dict[str, Any]:
            """Search cells in specified range"""
            return await spreadsheet_tools.find_cells(
                self.api_client,
                spreadsheet_token=args.spreadsheet_token,
                sheet_id=args.sheet_id,
                range_spec=args.range_spec,
                find_text=args.find_text,
                match_case=args.match_case,
                match_entire_cell=args.match_entire_cell,
                search_by_regex=args.search_by_regex,
                include_formulas=args.include_formulas,
            )

    def get_mcp_server(self) -> FastMCP:
        """Get FastMCP instance"""
        return self.mcp

    def run_sse(self):
        """Run server with SSE transport"""
        logger.info(f"Starting SSE server on {self.host}:{self.port}")
        self.mcp.run("sse", host=self.host, port=self.port)

    async def close(self):
        """Close server and cleanup resources"""
        await self.api_client.close()
'''
    
    # Write SSE server
    server_file = build_dir / "feishu_spreadsheet_mcp" / "sse_server.py"
    server_file.write_text(server_content)
    print("✓ SSE server created")
    return True


def create_sse_main_file(build_dir):
    """Create main entry point using SSE transport."""
    print("Creating SSE main file...")
    
    main_content = '''"""
Main entry point for FastMCP Feishu Spreadsheet server with SSE transport.
"""

import argparse
import logging
import sys
import os
from typing import Optional

from .config import config_manager
from .sse_server import FeishuSpreadsheetSSEServer


def run_sse_server(
    app_id: Optional[str] = None,
    app_secret: Optional[str] = None,
    config_file: Optional[str] = None,
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    """
    Run the FastMCP server with SSE transport.

    Args:
        app_id: Feishu app ID
        app_secret: Feishu app secret
        config_file: Configuration file path
        host: Server host
        port: Server port
    """
    try:
        # Load configuration
        config = config_manager.load_config(app_id, app_secret, config_file)

        # Setup logging
        config_manager.setup_logging()

        # Validate configuration
        if not config_manager.validate_config():
            raise ValueError("Invalid configuration")

        logger = logging.getLogger(__name__)
        logger.info(
            f"Feishu Spreadsheet MCP SSE Server initialized with app_id: {config.app_id[:8]}..."
        )
        logger.info(f"Server will start on {host}:{port}")

        # Create and run server with SSE transport
        server = FeishuSpreadsheetSSEServer(config.app_id, config.app_secret, host, port)
        
        # Run the SSE server
        server.run_sse()

    except Exception as e:
        logging.error(f"Failed to start SSE server: {e}")
        raise


def main() -> None:
    """Main entry point for command line."""
    parser = argparse.ArgumentParser(
        description="Feishu Spreadsheet MCP Server with SSE Transport",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
SSE Transport Configuration:
The server will start an HTTP server with SSE (Server-Sent Events) transport.
This provides better compatibility than stdio transport.

Default server: http://127.0.0.1:8000

Environment variables:
  FEISHU_APP_ID          Feishu application ID
  FEISHU_APP_SECRET      Feishu application secret
  FEISHU_LOG_LEVEL       Log level (DEBUG, INFO, WARNING, ERROR)
        """,
    )

    parser.add_argument(
        "--app-id",
        help="Feishu app ID (can also use FEISHU_APP_ID env var)",
    )
    parser.add_argument(
        "--app-secret", 
        help="Feishu app secret (can also use FEISHU_APP_SECRET env var)",
    )
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Server host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Server port (default: 8000)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set log level",
    )

    args = parser.parse_args()

    try:
        # Set log level early if specified
        if args.log_level:
            logging.basicConfig(level=getattr(logging, args.log_level))

        # Get credentials
        app_id = args.app_id or os.getenv('FEISHU_APP_ID')
        app_secret = args.app_secret or os.getenv('FEISHU_APP_SECRET')
        
        if not app_id or not app_secret:
            print("Error: FEISHU_APP_ID and FEISHU_APP_SECRET are required", file=sys.stderr)
            sys.exit(1)

        print(f"Starting SSE server on {args.host}:{args.port}")
        run_sse_server(app_id, app_secret, args.config, args.host, args.port)

    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\\nShutting down server...")
        sys.exit(0)
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
'''
    
    # Write SSE main
    main_file = build_dir / "feishu_spreadsheet_mcp" / "sse_main.py"
    main_file.write_text(main_content)
    print("✓ SSE main file created")
    return True


def create_sse_dtx():
    """Create DTX package with SSE transport."""
    print("=== Creating FastMCP SSE Transport DTX Package ===")
    
    build_dir = Path("dtx-sse-build")
    output_name = "feishu-spreadsheet-mcp-sse.dxt"
    
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
        
        # 2. Create SSE implementations
        if not create_sse_server_file(build_dir):
            return False
        if not create_sse_main_file(build_dir):
            return False
            
        # 3. Install dependencies (same as before)
        print("Installing dependencies...")
        lib_dir = build_dir / "lib"
        lib_dir.mkdir(parents=True, exist_ok=True)
        
        packages = ["fastmcp>=0.9.0", "pydantic>=2.0.0", "python-dotenv>=1.0.0", "httpx", "anyio"]
        cmd = [
            sys.executable, "-m", "pip", "install",
            "--target", str(lib_dir),
            "--no-user", "--no-cache-dir",
            "--upgrade", "--timeout", "180"
        ] + packages
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=200)
        if result.returncode != 0:
            print(f"Dependencies installation failed: {result.stderr}")
            return False
        print("✓ Dependencies installed")
        
        # 4. Create SSE manifest
        print("Creating SSE manifest...")
        with open("manifest.json", 'r') as f:
            manifest = json.load(f)
            
        # Update for SSE transport
        manifest["server"]["mcp_config"] = {
            "transport": "sse",
            "host": "127.0.0.1", 
            "port": 8000,
            "command": "python",
            "args": ["${__dirname}/startup_sse.py"],
            "env": {
                "FEISHU_APP_ID": "${user_config.app_id}",
                "FEISHU_APP_SECRET": "${user_config.app_secret}"
            }
        }
        manifest["version"] = "1.1.0-fastmcp-sse"
        manifest["dtx_info"] = {
            "type": "sse",
            "framework": "fastmcp", 
            "transport": "sse",
            "includes_dependencies": True,
            "server_url": "http://127.0.0.1:8000",
            "notes": "Uses SSE transport for better compatibility"
        }
        
        with open(build_dir / "manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)
        print("✓ SSE manifest created")
        
        # 5. Create SSE startup script
        print("Creating SSE startup script...")
        startup_content = '''#!/usr/bin/env python3
"""
SSE startup script for FastMCP Feishu Spreadsheet server.
Starts HTTP server with SSE transport for better MCP client compatibility.
"""

import sys
import os
from pathlib import Path

# Setup paths
current_dir = Path(__file__).parent
lib_dir = current_dir / "lib"
sys.path.insert(0, str(lib_dir))
sys.path.insert(0, str(current_dir))

try:
    # Check environment
    app_id = os.getenv('FEISHU_APP_ID')
    app_secret = os.getenv('FEISHU_APP_SECRET')
    
    if not app_id or not app_secret:
        print("Error: FEISHU_APP_ID and FEISHU_APP_SECRET environment variables are required", file=sys.stderr)
        sys.exit(1)
    
    # Get server configuration
    host = os.getenv('MCP_SSE_HOST', '127.0.0.1')
    port = int(os.getenv('MCP_SSE_PORT', '8000'))
    
    print(f"Starting Feishu Spreadsheet MCP SSE Server on {host}:{port}")
    
    # Import and run SSE main
    from feishu_spreadsheet_mcp.sse_main import run_sse_server
    run_sse_server(app_id, app_secret, host=host, port=port)
    
except ImportError as e:
    print(f"Import error: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Server error: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''
        
        (build_dir / "startup_sse.py").write_text(startup_content)
        print("✓ SSE startup script created")
        
        # 6. Create README
        readme_content = """# Feishu Spreadsheet MCP Server (FastMCP + SSE)

This package uses FastMCP with SSE (Server-Sent Events) transport for maximum compatibility.

## SSE Transport Benefits
- Better compatibility with MCP clients
- Reliable bidirectional communication over HTTP
- No stdio transport issues
- Works well in containerized environments

## Configuration
Set environment variables:
- FEISHU_APP_ID: Your Feishu application ID
- FEISHU_APP_SECRET: Your Feishu application secret

Optional:
- MCP_SSE_HOST: Server host (default: 127.0.0.1)  
- MCP_SSE_PORT: Server port (default: 8000)

## Usage
The server will start on http://127.0.0.1:8000 by default.
MCP clients should connect to this URL using SSE transport.

## MCP Client Configuration Example
```json
{
  "mcpServers": {
    "feishu-spreadsheet": {
      "transport": "sse",
      "url": "http://127.0.0.1:8000"
    }
  }
}
```

Built with FastMCP SSE transport for reliable MCP communication.
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
        print(f"✓ SSE DTX package created: {output_name} ({file_size:.1f} MB)")
        
        # 8. Cleanup
        shutil.rmtree(build_dir)
        print("✓ Build directory cleaned")
        
        print(f"\\n✅ FastMCP SSE DTX package created successfully!")
        print(f"📦 Package: {output_name} ({file_size:.1f} MB)")
        print(f"🌐 Uses SSE transport on http://127.0.0.1:8000")
        print(f"🚀 Better MCP client compatibility than stdio transport")
        
        return True
        
    except Exception as e:
        print(f"❌ Build failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = create_sse_dtx()
    sys.exit(0 if success else 1)