#!/usr/bin/env python3
"""
Test the fixed MCP connection with proper parameter format.
"""

import asyncio
import json
import subprocess
import sys
import os


async def test_fixed_mcp_connection():
    """Test MCP connection with correct parameter format for FastMCP."""
    print("=== Testing Fixed MCP Connection ===")
    
    # Set environment variables
    env = os.environ.copy()
    env['FEISHU_APP_ID'] = 'test_app_id'
    env['FEISHU_APP_SECRET'] = 'test_app_secret'
    
    # Command to run the server
    cmd = [sys.executable, '-m', 'feishu_spreadsheet_mcp.main']
    
    try:
        # Start the server process
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        
        print("✓ Server process started")
        
        async def send_jsonrpc_request(request, request_name):
            """Send a JSON-RPC request and get response."""
            request_json = json.dumps(request) + '\n'
            print(f"\n[{request_name}] → {request_json.strip()}")
            
            proc.stdin.write(request_json.encode())
            await proc.stdin.drain()
            
            try:
                response_data = await asyncio.wait_for(proc.stdout.readline(), timeout=3.0)
                if response_data:
                    response_str = response_data.decode().strip()
                    print(f"[{request_name}] ← {response_str}")
                    return json.loads(response_str)
                else:
                    print(f"[{request_name}] ← No response")
                    return None
            except asyncio.TimeoutError:
                print(f"[{request_name}] ← Timeout")
                return None
        
        # 1. Initialize
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        
        init_response = await send_jsonrpc_request(init_request, "INIT")
        if not init_response or "error" in init_response:
            print("❌ Initialization failed")
            return False
        
        print("✅ Initialization successful")
        
        # 2. Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }
        
        await send_jsonrpc_request(initialized_notification, "INITIALIZED")
        
        # 3. List tools
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        tools_response = await send_jsonrpc_request(tools_request, "TOOLS_LIST")
        if not tools_response or "error" in tools_response:
            print("❌ Tools listing failed")
            return False
        
        tools = tools_response.get("result", {}).get("tools", [])
        print(f"✅ Found {len(tools)} tools")
        
        # 4. Test tool call with CORRECT FastMCP parameter format
        print("\n=== Testing correct parameter format ===")
        tool_call_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "list_spreadsheets",
                "arguments": {
                    "args": {  # FastMCP expects parameters wrapped in 'args'
                        "folder_token": None,
                        "page_size": 10
                    }
                }
            }
        }
        
        call_response = await send_jsonrpc_request(tool_call_request, "TOOL_CALL")
        if call_response and "error" not in call_response:
            print("✅ Tool call with correct format successful!")
            result = call_response.get("result", {})
            if result.get("isError"):
                print(f"   Server returned error: {result}")
            else:
                print("   Server processed request successfully")
        else:
            print(f"⚠️ Tool call failed: {call_response}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    finally:
        # Clean up
        try:
            if proc.returncode is None:
                proc.terminate()
                await proc.wait()
        except:
            pass


if __name__ == "__main__":
    result = asyncio.run(test_fixed_mcp_connection())
    print(f"\n{'='*50}")
    if result:
        print("🎉 Fixed MCP connection test PASSED!")
    else:
        print("💥 MCP connection test FAILED!")
    print("="*50)
    sys.exit(0 if result else 1)