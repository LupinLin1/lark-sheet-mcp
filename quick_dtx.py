#!/usr/bin/env python3
"""
Quick DTX package creation for FastMCP Feishu Spreadsheet MCP Server.
"""

import os
import shutil
import json
import zipfile
from pathlib import Path


def create_simple_dtx():
    """Create a simple DTX package without heavy dependencies."""
    print("=== Creating Simple FastMCP DTX Package ===")
    
    build_dir = Path("dtx-simple-build")
    output_name = "feishu-spreadsheet-mcp-fastmcp-simple.dxt"
    
    # Clean and create build directory
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
        
        # 2. Copy and update manifest
        print("Creating manifest...")
        with open("manifest.json", 'r') as f:
            manifest = json.load(f)
        
        # Update for simple DTX
        manifest["server"]["mcp_config"]["args"] = ["${__dirname}/startup.py"]
        manifest["version"] = "1.1.0-fastmcp-simple"
        manifest["dtx_info"] = {
            "type": "simple",
            "framework": "fastmcp",
            "requires_external_deps": True,
            "note": "Requires fastmcp to be installed on target system"
        }
        
        with open(build_dir / "manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)
        print("✓ Manifest created")
        
        # 3. Create simple startup script
        print("Creating startup script...")
        startup_script = '''#!/usr/bin/env python3
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
'''
        
        (build_dir / "startup.py").write_text(startup_script)
        print("✓ Startup script created")
        
        # 4. Create requirements file
        print("Creating requirements file...")
        requirements = """# FastMCP Feishu Spreadsheet MCP Server Requirements
fastmcp>=0.9.0
pydantic>=2.0.0
python-dotenv>=1.0.0

# Installation instructions:
# pip install -r requirements.txt
"""
        (build_dir / "requirements.txt").write_text(requirements)
        print("✓ Requirements file created")
        
        # 5. Create README
        print("Creating README...")
        readme = """# Feishu Spreadsheet MCP Server (FastMCP)

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
"""
        (build_dir / "README.md").write_text(readme)
        print("✓ README created")
        
        # 6. Create DTX package
        print(f"Creating DTX package: {output_name}")
        with zipfile.ZipFile(output_name, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(build_dir):
                for file in files:
                    file_path = Path(root) / file
                    arc_path = file_path.relative_to(build_dir)
                    zf.write(file_path, arc_path)
        
        file_size = Path(output_name).stat().st_size / 1024 / 1024
        print(f"✓ DTX package created: {output_name} ({file_size:.1f} MB)")
        
        # 7. Cleanup build directory
        shutil.rmtree(build_dir)
        print("✓ Build directory cleaned")
        
        print(f"\n✅ Simple DTX package created successfully!")
        print(f"📦 Package: {output_name}")
        print(f"📋 Note: This package requires fastmcp to be installed on the target system")
        
        return True
        
    except Exception as e:
        print(f"❌ Build failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = create_simple_dtx()
    exit(0 if success else 1)