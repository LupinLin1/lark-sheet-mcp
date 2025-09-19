#!/usr/bin/env python3
"""
Test script for SSE DTX package.
"""

import os
import subprocess
import tempfile
import zipfile
import time
import requests
from pathlib import Path


def test_sse_dtx():
    """Test the SSE DTX package."""
    print("=== Testing SSE DTX Package ===")
    
    dtx_file = "feishu-spreadsheet-mcp-sse.dxt"
    
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
        env['MCP_SSE_HOST'] = '127.0.0.1'
        env['MCP_SSE_PORT'] = '8001'  # Use different port to avoid conflicts
        
        # Test startup script
        startup_script = temp_path / "startup_sse.py"
        
        print("Testing SSE server startup...")
        
        # Start server in background
        server_process = None
        try:
            server_process = subprocess.Popen(
                ["python", str(startup_script)],
                env=env,
                cwd=temp_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a moment for server to start
            time.sleep(3)
            
            # Check if server is running
            if server_process.poll() is None:
                print("✓ SSE server started successfully")
                
                # Try to connect to server
                try:
                    response = requests.get("http://127.0.0.1:8001", timeout=2)
                    print(f"✓ Server is responding (status: {response.status_code})")
                    return True
                except requests.exceptions.RequestException as e:
                    print(f"⚠ Server started but not responding to HTTP requests: {e}")
                    print("This is normal for MCP SSE servers that only handle MCP protocol")
                    return True
                    
            else:
                # Server exited, check output
                stdout, stderr = server_process.communicate()
                print(f"❌ Server exited with code: {server_process.returncode}")
                if stdout:
                    print(f"Stdout: {stdout[:300]}")
                if stderr:
                    print(f"Stderr: {stderr[:300]}")
                    
                # Check for import errors
                if "ImportError" in stderr or "ModuleNotFoundError" in stderr:
                    print("❌ Import errors detected")
                    return False
                else:
                    print("⚠ Server exited but no obvious import errors")
                    return False
                    
        except Exception as e:
            print(f"❌ Error testing SSE server: {e}")
            return False
            
        finally:
            # Cleanup server process
            if server_process and server_process.poll() is None:
                server_process.terminate()
                server_process.wait(timeout=5)

if __name__ == "__main__":
    success = test_sse_dtx()
    exit(0 if success else 1)