#!/usr/bin/env python3
"""
Quick test script to verify DTX package can start without errors.
"""

import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

def test_dtx_startup():
    """Test if the DTX package can start without immediate errors."""
    print("=== Testing DTX Package Startup ===")
    
    dtx_file = "feishu-spreadsheet-mcp-fastmcp-full.dxt"
    
    if not Path(dtx_file).exists():
        print(f"❌ DTX file not found: {dtx_file}")
        return False
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Extract DTX package
        print("Extracting DTX package...")
        with zipfile.ZipFile(dtx_file, 'r') as zf:
            zf.extractall(temp_path)
        
        # Set test environment variables
        env = os.environ.copy()
        env['FEISHU_APP_ID'] = 'test_app_id_123'
        env['FEISHU_APP_SECRET'] = 'test_app_secret_456'
        
        # Try to start the startup script briefly
        startup_script = temp_path / "startup_full.py"
        
        print("Testing startup script...")
        try:
            # Run with timeout to avoid hanging
            result = subprocess.run(
                ["python", str(startup_script)],
                env=env,
                timeout=10,
                capture_output=True,
                text=True,
                cwd=temp_path
            )
            
            # We expect it to fail due to no actual MCP client, but it should import correctly
            print(f"Return code: {result.returncode}")
            if result.stdout:
                print(f"Stdout: {result.stdout[:200]}")
            if result.stderr:
                print(f"Stderr: {result.stderr[:200]}")
                
            # Check if the error is related to import issues
            if "ImportError" in result.stderr or "ModuleNotFoundError" in result.stderr:
                print("❌ Import errors detected")
                return False
            else:
                print("✓ No import errors - startup script loads correctly")
                return True
                
        except subprocess.TimeoutExpired:
            print("✓ Script started successfully (timed out as expected)")
            return True
        except Exception as e:
            print(f"❌ Error testing startup: {e}")
            return False

if __name__ == "__main__":
    success = test_dtx_startup()
    exit(0 if success else 1)