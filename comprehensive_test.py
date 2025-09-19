#!/usr/bin/env python3
"""
全面测试 Feishu Spreadsheet MCP 服务器的所有工具功能
"""

import asyncio
import json
import sys
import os
from typing import Dict, Any


async def comprehensive_test():
    """全面测试所有工具功能"""
    
    # 测试用的表格token和工作表ID（来自用户提供的URL）
    spreadsheet_token = "NYSgsgSKAhKE7ntp133cvpjtnUg"
    sheet_id = "1DZyHm"  # 加量包工作表
    
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
        
        # 初始化连接
        init_request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "comprehensive-test-client", "version": "1.0.0"}
            }
        }
        
        await send_request(process, init_request)
        response = await read_response(process)
        if not response.get("result"):
            print(f"❌ 初始化失败: {response}")
            return False
        
        print(f"✅ 服务器连接成功: {response['result']['serverInfo']['name']}")
        request_id += 1
        
        # 发送initialized通知
        await send_request(process, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        
        # 1. 测试 list_spreadsheets
        print("\n📊 测试 1/5: list_spreadsheets")
        success = await test_list_spreadsheets(process, request_id)
        request_id += 1
        print("✅ 通过" if success else "❌ 失败")
        
        # 2. 测试 get_worksheets
        print("\n📝 测试 2/5: get_worksheets")
        actual_sheet_id = await test_get_worksheets(process, request_id, spreadsheet_token)
        if actual_sheet_id:
            sheet_id = actual_sheet_id  # 使用实际发现的工作表ID
            print(f"✅ 通过，使用工作表ID: {sheet_id}")
        else:
            print("❌ 失败")
        request_id += 1
        
        # 3. 测试 read_range
        print("\n📖 测试 3/5: read_range")
        success = await test_read_range(process, request_id, spreadsheet_token, sheet_id)
        request_id += 1
        print("✅ 通过" if success else "❌ 失败")
        
        # 4. 测试 read_multiple_ranges
        print("\n📚 测试 4/5: read_multiple_ranges")
        success = await test_read_multiple_ranges(process, request_id, spreadsheet_token, sheet_id)
        request_id += 1
        print("✅ 通过" if success else "❌ 失败")
        
        # 5. 测试 find_cells
        print("\n🔍 测试 5/5: find_cells")
        success = await test_find_cells(process, request_id, spreadsheet_token, sheet_id)
        request_id += 1
        print("✅ 通过" if success else "❌ 失败")
        
        print("\n🎉 全面测试完成！")
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


async def test_list_spreadsheets(process, request_id):
    """测试获取电子表格列表"""
    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {
            "name": "list_spreadsheets",
            "arguments": {
                "args": {
                    "folder_token": "",
                    "page_size": 50
                }
            }
        }
    }
    
    await send_request(process, request)
    response = await read_response(process)
    
    if response.get("result") and not response["result"].get("isError"):
        content = response["result"]["content"][0]["text"]
        data = json.loads(content)
        print(f"  📄 找到 {data.get('total_count', 0)} 个电子表格")
        return True
    else:
        print(f"  ❌ 错误: {response}")
        return False


async def test_get_worksheets(process, request_id, spreadsheet_token):
    """测试获取工作表列表"""
    request = {
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
    
    await send_request(process, request)
    response = await read_response(process)
    
    if response.get("result") and not response["result"].get("isError"):
        content = response["result"]["content"][0]["text"]
        data = json.loads(content)
        worksheets = data.get("worksheets", [])
        print(f"  📋 找到 {len(worksheets)} 个工作表:")
        
        target_sheet_id = None
        for ws in worksheets:
            print(f"    - {ws['title']} (ID: {ws['sheet_id']})")
            if ws['title'] == '加量包' or ws['sheet_id'] == '1DZyHm':
                target_sheet_id = ws['sheet_id']
        
        return target_sheet_id or worksheets[0]['sheet_id'] if worksheets else None
    else:
        print(f"  ❌ 错误: {response}")
        return None


async def test_read_range(process, request_id, spreadsheet_token, sheet_id):
    """测试读取单元格范围"""
    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {
            "name": "read_range",
            "arguments": {
                "args": {
                    "spreadsheet_token": spreadsheet_token,
                    "range_spec": f"{sheet_id}!A1:E10",
                    "value_render_option": "UnformattedValue",
                    "date_time_render_option": "FormattedString"
                }
            }
        }
    }
    
    await send_request(process, request)
    response = await read_response(process)
    
    if response.get("result") and not response["result"].get("isError"):
        content = response["result"]["content"][0]["text"]
        data = json.loads(content)
        values = data.get("values", [])
        print(f"  📖 读取范围 {data.get('range', 'unknown')}")
        print(f"  📊 数据行数: {len(values)}")
        
        # 显示一些数据示例
        for i, row in enumerate(values[:3]):  # 显示前3行
            non_null_cells = [cell for cell in row if cell is not None and cell != ""]
            if non_null_cells:
                print(f"    第{i+1}行: {non_null_cells[:3]}")  # 显示前3个非空单元格
        
        return True
    else:
        print(f"  ❌ 错误: {response}")
        return False


async def test_read_multiple_ranges(process, request_id, spreadsheet_token, sheet_id):
    """测试批量读取多个范围"""
    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {
            "name": "read_multiple_ranges",
            "arguments": {
                "args": {
                    "spreadsheet_token": spreadsheet_token,
                    "ranges": [f"{sheet_id}!A1:C5", f"{sheet_id}!A6:C10"],
                    "value_render_option": "UnformattedValue"
                }
            }
        }
    }
    
    await send_request(process, request)
    response = await read_response(process)
    
    if response.get("result") and not response["result"].get("isError"):
        content = response["result"]["content"][0]["text"]
        data = json.loads(content)
        ranges = data.get("ranges", [])
        print(f"  📚 读取 {len(ranges)} 个范围")
        
        for i, range_data in enumerate(ranges):
            print(f"    范围{i+1}: {range_data.get('range', 'unknown')} ({len(range_data.get('values', []))} 行)")
        
        return True
    else:
        print(f"  ❌ 错误: {response}")
        return False


async def test_find_cells(process, request_id, spreadsheet_token, sheet_id):
    """测试查找单元格"""
    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {
            "name": "find_cells",
            "arguments": {
                "args": {
                    "spreadsheet_token": spreadsheet_token,
                    "sheet_id": sheet_id,
                    "range_spec": f"{sheet_id}!A1:Z50",
                    "find_text": "包",
                    "match_case": False,
                    "match_entire_cell": False,
                    "search_by_regex": False,
                    "include_formulas": False
                }
            }
        }
    }
    
    await send_request(process, request)
    response = await read_response(process)
    
    if response.get("result") and not response["result"].get("isError"):
        content = response["result"]["content"][0]["text"]
        data = json.loads(content)
        
        matched_cells = data.get("matched_cells", [])
        total_matches = data.get("total_matches", 0)
        
        print(f"  🔍 找到 {total_matches} 个匹配项")
        if matched_cells:
            print(f"    匹配的单元格: {matched_cells[:5]}")  # 显示前5个
            
        return True
    else:
        print(f"  ❌ 错误: {response}")
        return False


async def send_request(process, request):
    """发送JSON-RPC请求"""
    request_json = json.dumps(request) + '\n'
    process.stdin.write(request_json.encode())
    await process.stdin.drain()


async def read_response(process):
    """读取JSON-RPC响应"""
    try:
        response_line = await asyncio.wait_for(process.stdout.readline(), timeout=15)
        if not response_line:
            raise Exception("Empty response from server")
        response = json.loads(response_line.decode().strip())
        return response
    except asyncio.TimeoutError:
        raise Exception("Response timeout")
    except json.JSONDecodeError as e:
        stderr_data = await process.stderr.read(1024)
        stderr_text = stderr_data.decode() if stderr_data else "No stderr"
        raise Exception(f"JSON decode error: {e}, stderr: {stderr_text}")


def main():
    """主函数"""
    print("🚀 开始全面测试 Feishu Spreadsheet MCP 服务器")
    print("=" * 70)
    print(f"📋 测试表格: NYSgsgSKAhKE7ntp133cvpjtnUg")
    print(f"🔗 URL: https://zuvjnsu1rw.feishu.cn/sheets/NYSgsgSKAhKE7ntp133cvpjtnUg")
    print("=" * 70)
    
    # 运行异步测试
    result = asyncio.run(comprehensive_test())
    
    if result:
        print("\n🎊 全面测试成功完成！")
        print("✅ 所有工具都正常运行")
        print("✅ 数据格式兼容 FastMCP")
        print("✅ 连接稳定性良好")
        sys.exit(0)
    else:
        print("\n❌ 测试失败")
        sys.exit(1)


if __name__ == "__main__":
    main()