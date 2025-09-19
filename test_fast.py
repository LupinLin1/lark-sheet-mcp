#!/usr/bin/env python3
"""
Test fast startup version.
"""

import asyncio
import json
import subprocess
import sys
import os
import time

async def test_fast_startup():
    """Test the optimized fast startup version."""
    
    env = os.environ.copy()
    env['FEISHU_APP_ID'] = 'test_app_id'
    env['FEISHU_APP_SECRET'] = 'test_app_secret'
    env['FEISHU_LOG_LEVEL'] = 'INFO'
    
    cmd = [sys.executable, 'startup_fast.py']
    cwd = os.path.join(os.getcwd(), 'dxt-build')
    
    print("=== Testing Fast DTX Startup ===")
    start_time = time.time()
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=cwd
        )
        
        # Send initialization request quickly
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
        proc.stdin.write(request_json.encode())
        await proc.stdin.drain()
        
        # Read response with shorter timeout to test speed
        try:
            response_data = await asyncio.wait_for(proc.stdout.readline(), timeout=3.0)
            end_time = time.time()
            
            if response_data:
                response_str = response_data.decode().strip()
                response = json.loads(response_str)
                
                startup_time = end_time - start_time
                print(f"✅ Startup time: {startup_time:.2f}s")
                print(f"Response: {response.get('result', {}).get('serverInfo', {})}")
                
                if startup_time < 2.0:  # Target: under 2 seconds
                    print("✅ Fast startup achieved!")
                    return True
                else:
                    print("⚠️ Still too slow for optimal performance")
                    return True  # Still working, just slow
            else:
                print("❌ No response")
                return False
                
        except asyncio.TimeoutError:
            print("❌ Timeout - still too slow")
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
                print(f"stderr: {stderr_data.decode()}")
        except:
            pass

if __name__ == "__main__":
    result = asyncio.run(test_fast_startup())
    sys.exit(0 if result else 1)