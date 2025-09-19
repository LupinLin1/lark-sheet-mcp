#!/usr/bin/env python3
"""
Final test script for DTX extension with startup wrapper.
"""

import asyncio
import json
import subprocess
import sys
import os

async def test_startup_wrapper():
    """Test the DTX with the new startup wrapper."""
    
    # Set up environment
    env = os.environ.copy()
    env['FEISHU_APP_ID'] = 'test_app_id'
    env['FEISHU_APP_SECRET'] = 'test_app_secret'
    env['FEISHU_LOG_LEVEL'] = 'DEBUG'
    
    cmd = [sys.executable, 'startup.py']
    cwd = os.path.join(os.getcwd(), 'dxt-build')
    
    print("=== Testing DTX with Startup Wrapper ===")
    print(f"Command: {' '.join(cmd)}")
    print(f"Working directory: {cwd}")
    
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
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "claude-desktop", "version": "1.0.0"}
            }
        }
        
        request_json = json.dumps(init_request) + '\n'
        print(f"Sending: {request_json.strip()}")
        
        proc.stdin.write(request_json.encode())
        await proc.stdin.drain()
        
        # Read response
        try:
            response_data = await asyncio.wait_for(proc.stdout.readline(), timeout=10.0)
            if response_data:
                response_str = response_data.decode().strip()
                print(f"Response: {response_str}")
                
                response = json.loads(response_str)
                if response.get('result'):
                    print("✅ DTX startup wrapper test passed!")
                    
                    # Test tools list
                    tools_request = {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/list",
                        "params": {}
                    }
                    
                    request_json = json.dumps(tools_request) + '\n'
                    proc.stdin.write(request_json.encode())
                    await proc.stdin.drain()
                    
                    tools_response = await asyncio.wait_for(proc.stdout.readline(), timeout=5.0)
                    if tools_response:
                        tools_str = tools_response.decode().strip()
                        print(f"Tools response: {tools_str}")
                        tools_data = json.loads(tools_str)
                        print(f"✅ Found {len(tools_data.get('result', {}).get('tools', []))} tools")
                        
                    return True
                else:
                    print(f"❌ Initialization failed: {response}")
                    return False
            else:
                print("❌ No response from server")
                return False
                
        except asyncio.TimeoutError:
            print("❌ Timeout waiting for response")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
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
    result = asyncio.run(test_startup_wrapper())
    sys.exit(0 if result else 1)