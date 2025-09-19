#!/usr/bin/env python3
"""
Create DTX package for Feishu Spreadsheet MCP Server with FastMCP.
"""

import os
import shutil
import subprocess
import sys
import json
import zipfile
from pathlib import Path


def install_dependencies(build_dir):
    """Install dependencies to the build directory."""
    print("Installing dependencies...")
    
    # Create lib directory
    lib_dir = build_dir / "lib"
    lib_dir.mkdir(parents=True, exist_ok=True)
    
    # Install only essential dependencies with minimal footprint
    cmd = [
        sys.executable, "-m", "pip", "install",
        "--target", str(lib_dir),
        "--no-user",
        "--no-cache-dir",
        "--no-deps",  # Don't install dependencies of dependencies
        "fastmcp",
        "pydantic",
        "python-dotenv"
    ]
    
    print("Installing core packages...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Core installation failed, trying with dependencies: {result.stderr}")
        # Fallback: install with dependencies but limit to essentials
        cmd_fallback = [
            sys.executable, "-m", "pip", "install",
            "--target", str(lib_dir),
            "--no-user",
            "--no-cache-dir",
            "fastmcp>=0.9.0"
        ]
        result = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            print(f"Failed to install dependencies: {result.stderr}")
            return False
    
    print("✓ Dependencies installed")
    return True


def copy_source_code(build_dir):
    """Copy source code to build directory."""
    print("Copying source code...")
    
    # Copy the main package
    src_pkg = Path("feishu_spreadsheet_mcp")
    dst_pkg = build_dir / "feishu_spreadsheet_mcp"
    
    if dst_pkg.exists():
        shutil.rmtree(dst_pkg)
    shutil.copytree(src_pkg, dst_pkg)
    
    # Copy manifest
    shutil.copy2("manifest.json", build_dir / "manifest.json")
    
    print("✓ Source code copied")
    return True


def create_startup_script(build_dir):
    """Create startup scripts for the DTX package."""
    print("Creating startup scripts...")
    
    # Main startup script
    startup_py = build_dir / "startup.py"
    startup_py.write_text('''#!/usr/bin/env python3
"""
Startup script for Feishu Spreadsheet MCP Server DTX package.
"""

import sys
import os
from pathlib import Path

# Add lib directory to Python path
lib_path = Path(__file__).parent / "lib"
sys.path.insert(0, str(lib_path))

# Now import and run the main module
try:
    from feishu_spreadsheet_mcp.main import main
    if __name__ == "__main__":
        main()
except Exception as e:
    print(f"Error starting server: {e}", file=sys.stderr)
    sys.exit(1)
''')
    
    # FastMCP-specific startup script
    startup_fast_py = build_dir / "startup_fast.py"
    startup_fast_py.write_text('''#!/usr/bin/env python3
"""
FastMCP-optimized startup script for Feishu Spreadsheet MCP Server.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add lib directory to Python path
lib_path = Path(__file__).parent / "lib"
sys.path.insert(0, str(lib_path))

async def main():
    """Main async entry point."""
    try:
        from feishu_spreadsheet_mcp.main import main_async
        
        # Get configuration from environment
        app_id = os.getenv('FEISHU_APP_ID')
        app_secret = os.getenv('FEISHU_APP_SECRET')
        
        if not app_id or not app_secret:
            raise ValueError("FEISHU_APP_ID and FEISHU_APP_SECRET environment variables are required")
        
        await main_async(app_id, app_secret)
        
    except Exception as e:
        print(f"Error starting FastMCP server: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
''')
    
    print("✓ Startup scripts created")
    return True


def create_dtx_package(build_dir, output_name):
    """Create the final DTX package."""
    print(f"Creating DTX package: {output_name}")
    
    with zipfile.ZipFile(output_name, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add all files from build directory
        for root, dirs, files in os.walk(build_dir):
            for file in files:
                file_path = Path(root) / file
                arc_path = file_path.relative_to(build_dir)
                zf.write(file_path, arc_path)
    
    print(f"✓ DTX package created: {output_name}")
    return True


def update_manifest_for_dtx(build_dir):
    """Update manifest.json for DTX compatibility."""
    print("Updating manifest for DTX...")
    
    manifest_path = build_dir / "manifest.json"
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    
    # Update for DTX packaging
    manifest["server"]["mcp_config"]["args"] = ["${__dirname}/startup_fast.py"]
    manifest["version"] = "1.1.0-fastmcp"
    
    # Add DTX-specific metadata
    manifest["dtx_info"] = {
        "framework": "fastmcp",
        "python_requirements": [
            "fastmcp>=0.9.0",
            "pydantic>=2.0.0", 
            "python-dotenv>=1.0.0"
        ],
        "build_timestamp": str(Path().cwd().stat().st_mtime),
        "build_python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    }
    
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print("✓ Manifest updated for DTX")
    return True


def main():
    """Main build function."""
    print("=== Creating Feishu Spreadsheet MCP DTX Package (FastMCP) ===")
    
    build_dir = Path("dxt-build")
    output_name = "feishu-spreadsheet-mcp-fastmcp.dxt"
    
    # Clean and create build directory
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)
    
    try:
        # Build steps
        steps = [
            (copy_source_code, build_dir),
            (install_dependencies, build_dir),
            (create_startup_script, build_dir),
            (update_manifest_for_dtx, build_dir),
            (create_dtx_package, build_dir, output_name)
        ]
        
        for step_func, *args in steps:
            if not step_func(*args):
                print(f"❌ Build failed at step: {step_func.__name__}")
                return False
        
        print(f"\n✅ DTX package created successfully: {output_name}")
        print(f"📦 Package size: {Path(output_name).stat().st_size / 1024 / 1024:.1f} MB")
        
        return True
        
    except Exception as e:
        print(f"❌ Build failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)