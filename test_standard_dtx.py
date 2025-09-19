#!/usr/bin/env python3
"""
Test script for standard MCP DTX package.
"""

import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

def test_standard_dtx():
    """Test the standard MCP DTX package."""
    print("=== Testing Standard MCP DTX Package ===")
    
    dtx_file = "feishu-spreadsheet-mcp-standard.dxt"
    
    if not Path(dtx_file).exists():
        print(f"❌ DTX file not found: {dtx_file}")
        return False
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Extract DTX package
        print("Extracting DTX package...")
        with zipfile.ZipFile(dtx_file, 'r') as zf:
            zf.extractall(temp_path)
        
        # Set test environment
        env = os.environ.copy()
        env['FEISHU_APP_ID'] = 'test_app_id_123'
        env['FEISHU_APP_SECRET'] = 'test_app_secret_456'
        
        # Test startup script
        startup_script = temp_path / "startup_standard.py"
        
        print("Testing standard MCP startup...")
        try:
            # Run with brief timeout
            result = subprocess.run(
                ["python", str(startup_script)],
                env=env,
                timeout=8,
                capture_output=True,
                text=True,
                cwd=temp_path
            )
            
            print(f"Return code: {result.returncode}")
            if result.stdout:
                print(f"Stdout: {result.stdout[:300]}")
            if result.stderr:
                print(f"Stderr: {result.stderr[:300]}")
                
            # Check for import or startup errors
            if "ImportError" in result.stderr or "ModuleNotFoundError" in result.stderr:
                print("❌ Import errors detected")
                return False
            elif "Server error" in result.stderr and "FEISHU_APP_ID" not in result.stderr:
                print("❌ Server startup errors")
                return False
            else:
                print("✓ Standard MCP server loads correctly")
                return True
                
        except subprocess.TimeoutExpired:
            print("✓ Server started successfully (timed out as expected)")
            return True
        except Exception as e:
            print(f"❌ Error testing: {e}")
            return False

if __name__ == "__main__":
    success = test_standard_dtx()
    exit(0 if success else 1)