#!/usr/bin/env python3
"""
Create full DTX package with all dependencies included.
"""

import os
import shutil
import json
import zipfile
import subprocess
import sys
from pathlib import Path


def create_full_dtx():
    """Create a complete DTX package with all dependencies bundled."""
    print("=== Creating Full FastMCP DTX Package (with dependencies) ===")
    
    build_dir = Path("dtx-full-build")
    output_name = "feishu-spreadsheet-mcp-fastmcp-full.dxt"
    
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
        
        # 2. Install dependencies
        print("Installing dependencies (this may take a moment)...")
        lib_dir = build_dir / "lib"
        lib_dir.mkdir(parents=True, exist_ok=True)
        
        # Install all packages in one command for better efficiency
        essential_packages = ["fastmcp>=0.9.0", "pydantic>=2.0.0", "python-dotenv>=1.0.0", "httpx", "anyio"]
        
        print(f"Installing packages: {', '.join(essential_packages)}")
        cmd = [
            sys.executable, "-m", "pip", "install",
            "--target", str(lib_dir),
            "--no-user",
            "--no-cache-dir",
            "--upgrade",
            "--timeout", "180"
        ] + essential_packages
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=200)
        if result.returncode != 0:
            print(f"Warning: Installation failed: {result.stderr}")
            # Try with individual packages as fallback
            for package in essential_packages:
                print(f"Trying to install {package} individually...")
                cmd_single = [
                    sys.executable, "-m", "pip", "install",
                    "--target", str(lib_dir),
                    "--no-user",
                    "--no-cache-dir",
                    "--timeout", "120",
                    package
                ]
                result_single = subprocess.run(cmd_single, capture_output=True, text=True, timeout=150)
                if result_single.returncode == 0:
                    print(f"✓ {package} installed")
                else:
                    print(f"⚠ Failed to install {package}: {result_single.stderr}")
        else:
            print("✓ All packages installed successfully")
        
        print("✓ Dependencies installation completed")
        
        # 3. Create manifest
        print("Creating manifest...")
        with open("manifest.json", 'r') as f:
            manifest = json.load(f)
        
        # Update for full DTX
        manifest["server"]["mcp_config"]["args"] = ["${__dirname}/startup_full.py"]
        manifest["version"] = "1.1.0-fastmcp-full"
        manifest["dtx_info"] = {
            "type": "full",
            "framework": "fastmcp",
            "includes_dependencies": True,
            "self_contained": True
        }
        
        with open(build_dir / "manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)
        print("✓ Manifest created")
        
        # 4. Create full startup script
        print("Creating startup script...")
        startup_script = '''#!/usr/bin/env python3
"""
Full startup script with bundled dependencies for FastMCP Feishu Spreadsheet MCP Server.
"""

import sys
import os
import logging
from pathlib import Path

# Add bundled lib directory to Python path first
current_dir = Path(__file__).parent
lib_dir = current_dir / "lib"
sys.path.insert(0, str(lib_dir))
sys.path.insert(0, str(current_dir))

# Disable buffering for stdout/stderr to ensure immediate output to MCP client
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

try:
    # Setup basic logging to avoid missing log messages
    logging.basicConfig(
        level=logging.WARNING,
        format='%(message)s',
        stream=sys.stderr
    )
    
    # Import and run the main module
    from feishu_spreadsheet_mcp.main import main
    
    if __name__ == "__main__":
        # Ensure environment variables are available
        app_id = os.getenv('FEISHU_APP_ID')
        app_secret = os.getenv('FEISHU_APP_SECRET')
        
        if not app_id or not app_secret:
            print("Error: FEISHU_APP_ID and FEISHU_APP_SECRET environment variables are required", file=sys.stderr)
            sys.exit(1)
            
        main()
        
except ImportError as e:
    print(f"Import error - missing dependency: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error starting FastMCP server: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''
        
        (build_dir / "startup_full.py").write_text(startup_script)
        print("✓ Startup script created")
        
        # 5. Create package info
        info_content = f"""# Feishu Spreadsheet MCP Server (FastMCP - Full Package)

Version: 1.1.0-fastmcp-full
Framework: FastMCP
Package Type: Self-contained

## Included Dependencies
- fastmcp
- pydantic  
- python-dotenv
- All transitive dependencies

## Configuration
Set these environment variables:
- FEISHU_APP_ID: Your Feishu application ID
- FEISHU_APP_SECRET: Your Feishu application secret

## Usage
This package is self-contained and includes all required dependencies.
Simply configure the environment variables and run.

Built with Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}
"""
        
        (build_dir / "PACKAGE_INFO.md").write_text(info_content)
        print("✓ Package info created")
        
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
        
        # 7. List package contents
        print("\nPackage contents:")
        with zipfile.ZipFile(output_name, 'r') as zf:
            file_list = zf.namelist()
            print(f"  Total files: {len(file_list)}")
            print("  Key components:")
            for item in sorted(file_list):
                if item.endswith(('.py', '.json', '.md')) and not item.startswith('lib/'):
                    print(f"    {item}")
        
        # 8. Cleanup build directory
        shutil.rmtree(build_dir)
        print("✓ Build directory cleaned")
        
        print(f"\n✅ Full DTX package created successfully!")
        print(f"📦 Package: {output_name} ({file_size:.1f} MB)")
        print(f"🚀 Self-contained package with all dependencies included")
        
        return True
        
    except Exception as e:
        print(f"❌ Build failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = create_full_dtx()
    exit(0 if success else 1)