#!/usr/bin/env python3
"""
MCP客户端测试脚本
用于测试Feishu Spreadsheet MCP服务器的所有工具功能
"""

import asyncio
import json
import sys
import os
from typing import Dict, Any


async def test_mcp_server():
    """测试MCP服务器的所有功能"""
    
    # 测试用的表格token和工作表ID（来自用户提供的URL）
    spreadsheet_token = "NYSgsgSKAhKE7ntp133cvpjtnUg"
    sheet_id = "1DZyHm"
    
    # 设置环境变量
    env = os.environ.copy()
    env.update({
        "FEISHU_APP_ID": "cli_a80a58f563f8500c",
        "FEISHU_APP_SECRET": "59cn2FCWvmKZ6Y7hGyDnKeJ0xeZgU0Yh",
        "FEISHU_LOG_LEVEL": "INFO"
    })
    
    # 启动MCP服务器进程
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "feishu_spreadsheet_mcp.main",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env
    )
    
    request_id = 1
    
    try:
        print("🔌 连接到 MCP 服务器...")
        
        # 测试1: 初始化
        print("\n🔄 测试1: 初始化连接")
        init_request = {
            "jsonrpc": "2.0",
            "id": request_id,
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
        
        await send_request(process, init_request)
        response = await read_response(process)
        if response.get("result"):
            server_info = response["result"].get("serverInfo", {})
            print(f"✅ 服务器连接成功: {server_info.get('name', 'Unknown')}")
        else:
            print(f"❌ 初始化失败: {response}")
            return False
        
        request_id += 1
        
        # 发送initialized通知
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        await send_request(process, initialized_notification)
        
        # 测试2: 列出可用工具
        print("\n📋 测试2: 列出可用工具")
        tools_request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/list"
        }
        
        await send_request(process, tools_request)
        response = await read_response(process)
        if response.get("result"):
            tools = response["result"].get("tools", [])
            print(f"✅ 发现 {len(tools)} 个工具:")
            for tool in tools:
                print(f"  - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
        else:
            print(f"❌ 获取工具列表失败: {response}")
            return False
        
        request_id += 1
        
        # 测试3: list_spreadsheets - 获取电子表格列表
        print("\n📊 测试3: 获取电子表格列表")
        list_request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": "list_spreadsheets",
                "arguments": {
                    "args": {
                        "folder_token": "",
                        "page_size": 10
                    }
                }
            }
        }
        
        await send_request(process, list_request)
        response = await read_response(process)
        if response.get("result") and not response["result"].get("isError"):
            content = response["result"]["content"][0]["text"]
            print(f"✅ list_spreadsheets 成功: {content[:100]}...")
        else:
            print(f"❌ list_spreadsheets 失败: {response}")
        
        request_id += 1
        
        # 测试4: get_worksheets - 获取工作表列表
        print("\n📝 测试4: 获取工作表列表")
        worksheets_request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": "get_worksheets",
                "arguments": {
                    "args": {
                        "spreadsheet_token": spreadsheet_token
                    }
                }
            }
        }
        
        await send_request(process, worksheets_request)
        response = await read_response(process)
        if response.get("result") and not response["result"].get("isError"):
            content = response["result"]["content"][0]["text"]
            print(f"✅ get_worksheets 成功: {content[:100]}...")
            
            # 尝试解析结果获取实际的sheet_id
            try:
                import re
                match = re.search(r'"sheet_id":\s*"([^"]+)"', content)
                if match:
                    actual_sheet_id = match.group(1)
                    print(f"📌 发现实际工作表ID: {actual_sheet_id}")
                    if actual_sheet_id != sheet_id:
                        sheet_id = actual_sheet_id
            except:
                pass
        else:
            print(f"❌ get_worksheets 失败: {response}")
        
        request_id += 1
        
        # 测试5: read_range - 读取单元格范围
        print("\n📖 测试5: 读取单元格范围")
        range_spec = f"{sheet_id}!A1:C10"
        read_request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": "read_range",
                "arguments": {
                    "args": {
                        "spreadsheet_token": spreadsheet_token,
                        "range_spec": range_spec,
                        "value_render_option": "UnformattedValue",
                        "date_time_render_option": "FormattedString"
                    }
                }
            }
        }
        
        await send_request(process, read_request)
        response = await read_response(process)
        if response.get("result") and not response["result"].get("isError"):
            content = response["result"]["content"][0]["text"]
            print(f"✅ read_range 成功: {content[:100]}...")
        else:
            print(f"❌ read_range 失败: {response}")
        
        request_id += 1
        
        print("\n🎉 主要测试完成！")
        return True
        
    except Exception as e:
        print(f"💥 测试过程中出现错误: {e}")
        return False
    finally:
        # 清理进程
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()


async def send_request(process, request):
    """发送JSON-RPC请求"""
    request_json = json.dumps(request) + '\n'
    process.stdin.write(request_json.encode())
    await process.stdin.drain()
    print(f"📤 发送请求: {request.get('method', 'unknown')}")


async def read_response(process):
    """读取JSON-RPC响应"""
    try:
        response_line = await asyncio.wait_for(process.stdout.readline(), timeout=15)
        if not response_line:
            raise Exception("Empty response from server")
        response = json.loads(response_line.decode().strip())
        print(f"📥 收到响应")
        return response
    except asyncio.TimeoutError:
        raise Exception("Response timeout")
    except json.JSONDecodeError as e:
        stderr_data = await process.stderr.read(1024)
        stderr_text = stderr_data.decode() if stderr_data else "No stderr"
        raise Exception(f"JSON decode error: {e}, stderr: {stderr_text}")


def main():
    """主函数"""
    print("🚀 开始测试 Feishu Spreadsheet MCP 服务器")
    print("=" * 60)
    
    # 运行异步测试
    result = asyncio.run(test_mcp_server())
    
    if result:
        print("\n✅ 测试完成")
        sys.exit(0)
    else:
        print("\n❌ 测试失败")
        sys.exit(1)


if __name__ == "__main__":
    main()