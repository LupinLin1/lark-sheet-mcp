#!/usr/bin/env python3
"""
Test MCP connection with the fixed FastMCP server.
"""

import asyncio
import json
import subprocess
import sys
import os


async def test_mcp_connection():
    """Test MCP server connection with proper protocol flow."""
    print("=== Testing MCP Connection with FastMCP Server ===")
    
    # Set environment variables
    env = os.environ.copy()
    env['FEISHU_APP_ID'] = 'test_app_id'
    env['FEISHU_APP_SECRET'] = 'test_app_secret'
    
    # Command to run the server
    cmd = [sys.executable, '-m', 'feishu_spreadsheet_mcp.main']
    
    print(f"Starting server with command: {' '.join(cmd)}")
    
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
                # Wait for response with timeout
                response_data = await asyncio.wait_for(proc.stdout.readline(), timeout=5.0)
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
        
        # 1. Initialize the MCP session
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
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        init_response = await send_jsonrpc_request(init_request, "INITIALIZE")
        if not init_response or "error" in init_response:
            print("❌ Initialization failed")
            if init_response:
                print(f"Error: {init_response.get('error')}")
            return False
        
        print("✅ Initialization successful")
        
        # 2. Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }
        
        await send_jsonrpc_request(initialized_notification, "INITIALIZED")
        
        # 3. List available tools
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        tools_response = await send_jsonrpc_request(tools_request, "TOOLS_LIST")
        if not tools_response or "error" in tools_response:
            print("❌ Tools listing failed")
            if tools_response:
                print(f"Error: {tools_response.get('error')}")
            return False
        
        tools = tools_response.get("result", {}).get("tools", [])
        print(f"✅ Found {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool.get('name')}: {tool.get('description')}")
        
        # 4. Test a simple tool call
        if tools:
            tool_call_request = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "list_spreadsheets",
                    "arguments": {
                        "page_size": 10
                    }
                }
            }
            
            call_response = await send_jsonrpc_request(tool_call_request, "TOOL_CALL")
            if call_response and "error" not in call_response:
                print("✅ Tool call successful")
            else:
                print(f"⚠️ Tool call failed (expected with test credentials)")
        
        # Keep server alive briefly to check stability
        print("\n=== Checking server stability ===")
        await asyncio.sleep(1)
        
        if proc.returncode is None:
            print("✅ Server is still running and stable")
            success = True
        else:
            print(f"❌ Server exited unexpectedly with code: {proc.returncode}")
            success = False
        
        return success
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up the process
        try:
            if proc.returncode is None:
                proc.terminate()
                await proc.wait()
            
            # Check for any stderr output
            stderr_data = await proc.stderr.read()
            if stderr_data:
                stderr_text = stderr_data.decode().strip()
                if stderr_text:
                    print(f"\n=== Server stderr ===")
                    print(stderr_text)
        except:
            pass


if __name__ == "__main__":
    result = asyncio.run(test_mcp_connection())
    print(f"\n{'='*50}")
    if result:
        print("🎉 MCP connection test PASSED!")
    else:
        print("💥 MCP connection test FAILED!")
    print("="*50)
    sys.exit(0 if result else 1)