#!/usr/bin/env python3
"""
Test script to manually verify DTX extension works.
"""

import asyncio
import json
import subprocess
import sys
import os
import tempfile

async def test_mcp_server():
    """Test the MCP server by sending a simple initialization request."""
    
    # Set up environment
    env = os.environ.copy()
    env['FEISHU_APP_ID'] = 'test_app_id'
    env['FEISHU_APP_SECRET'] = 'test_app_secret'
    env['PYTHONPATH'] = os.path.join(os.getcwd(), 'dxt-build', 'lib')
    
    # Start the MCP server process
    cmd = [
        sys.executable, 
        '-m', 
        'feishu_spreadsheet_mcp.main'
    ]
    
    cwd = os.path.join(os.getcwd(), 'dxt-build')
    
    print(f"Starting MCP server: {' '.join(cmd)}")
    print(f"Working directory: {cwd}")
    print(f"PYTHONPATH: {env.get('PYTHONPATH')}")
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=cwd
        )
        
        # Send initialization request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        request_json = json.dumps(init_request) + '\n'
        print(f"Sending request: {request_json.strip()}")
        
        proc.stdin.write(request_json.encode())
        await proc.stdin.drain()
        
        # Read response with timeout
        try:
            response_data = await asyncio.wait_for(proc.stdout.readline(), timeout=10.0)
            if response_data:
                response_str = response_data.decode().strip()
                print(f"Received response: {response_str}")
                
                try:
                    response = json.loads(response_str)
                    if response.get('result'):
                        print("✅ MCP server initialized successfully!")
                        return True
                    else:
                        print(f"❌ Server returned error: {response}")
                        return False
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON response: {e}")
                    return False
            else:
                print("❌ No response received from server")
                return False
                
        except asyncio.TimeoutError:
            print("❌ Timeout waiting for server response")
            return False
            
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return False
    finally:
        try:
            proc.stdin.close()
            await proc.wait()
            
            # Print any stderr output
            stderr_data = await proc.stderr.read()
            if stderr_data:
                print(f"Server stderr: {stderr_data.decode()}")
        except:
            pass

if __name__ == "__main__":
    print("Testing DTX MCP Server...")
    result = asyncio.run(test_mcp_server())
    if result:
        print("✅ DTX extension test passed!")
        sys.exit(0)
    else:
        print("❌ DTX extension test failed!")
        sys.exit(1)