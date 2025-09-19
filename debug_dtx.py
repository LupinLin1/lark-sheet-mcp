#!/usr/bin/env python3
"""
Debug script to test DTX with extended logging and better compatibility.
"""

import asyncio
import json
import subprocess
import sys
import os
import time

async def test_mcp_with_tools():
    """Test MCP server with tool listing to debug the Claude Desktop issue."""
    
    # Set up environment
    env = os.environ.copy()
    env['FEISHU_APP_ID'] = 'test_app_id'
    env['FEISHU_APP_SECRET'] = 'test_app_secret'
    env['PYTHONPATH'] = os.path.join(os.getcwd(), 'dxt-build', 'lib')
    
    cmd = [sys.executable, '-m', 'feishu_spreadsheet_mcp.main']
    cwd = os.path.join(os.getcwd(), 'dxt-build')
    
    print("=== Testing MCP Server with Full Protocol ===")
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=cwd
        )
        
        async def send_request(request, name):
            request_json = json.dumps(request) + '\n'
            print(f"\n[{name}] Sending: {request_json.strip()}")
            
            proc.stdin.write(request_json.encode())
            await proc.stdin.drain()
            
            try:
                response_data = await asyncio.wait_for(proc.stdout.readline(), timeout=5.0)
                if response_data:
                    response_str = response_data.decode().strip()
                    print(f"[{name}] Response: {response_str}")
                    return json.loads(response_str)
                else:
                    print(f"[{name}] No response")
                    return None
            except asyncio.TimeoutError:
                print(f"[{name}] Timeout")
                return None
        
        # 1. Initialize
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "claude-desktop",
                    "version": "1.0.0"
                }
            }
        }
        
        response = await send_request(init_request, "INIT")
        if not response or "error" in response:
            print("❌ Initialization failed")
            return False
            
        # 2. Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }
        
        await send_request(initialized_notification, "INITIALIZED")
        
        # Give server time to process
        await asyncio.sleep(0.1)
        
        # 3. List tools
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        response = await send_request(tools_request, "TOOLS")
        if not response or "error" in response:
            print("❌ Tools listing failed")
            return False
            
        print(f"✅ Found {len(response.get('result', {}).get('tools', []))} tools")
        
        # Keep server alive for a bit to see if it closes
        print("\n=== Keeping server alive for 3 seconds ===")
        await asyncio.sleep(3)
        
        # Check if process is still running
        if proc.returncode is None:
            print("✅ Server is still running")
        else:
            print(f"❌ Server exited with code {proc.returncode}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            if proc.returncode is None:
                proc.terminate()
                await proc.wait()
                
            stderr_data = await proc.stderr.read()
            if stderr_data:
                print(f"\n=== Server stderr ===")
                print(stderr_data.decode())
        except:
            pass

if __name__ == "__main__":
    result = asyncio.run(test_mcp_with_tools())
    sys.exit(0 if result else 1)