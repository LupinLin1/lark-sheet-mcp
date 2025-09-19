#!/usr/bin/env python3
"""
直接测试 find_cells API 调用
"""

import asyncio
import os
from feishu_spreadsheet_mcp.services import AuthenticationManager, FeishuAPIClient


async def test_find_direct():
    """直接测试API调用"""
    
    # 设置认证
    app_id = "cli_a80a58f563f8500c"
    app_secret = "59cn2FCWvmKZ6Y7hGyDnKeJ0xeZgU0Yh"
    
    auth_manager = AuthenticationManager(app_id, app_secret)
    api_client = FeishuAPIClient(auth_manager)
    
    try:
        print("🔗 测试认证...")
        token = await auth_manager.get_tenant_access_token()
        print(f"✅ 认证成功: {token[:20]}...")
        
        print("\n🔍 测试 find_cells API...")
        spreadsheet_token = "NYSgsgSKAhKE7ntp133cvpjtnUg"
        
        # 首先获取实际的 sheet_id
        worksheets_response = await api_client.get_worksheets(spreadsheet_token)
        worksheets_data = worksheets_response.get("data", {}).get("sheets", [])
        
        if not worksheets_data:
            raise Exception("No worksheets found")
            
        # 找到加量包工作表
        target_sheet = None
        for ws in worksheets_data:
            if ws.get("title") == "加量包":
                target_sheet = ws
                break
        
        if not target_sheet:
            target_sheet = worksheets_data[0]  # 使用第一个工作表
            
        sheet_id = target_sheet["sheet_id"]
        print(f"使用工作表: {target_sheet['title']} (ID: {sheet_id})")
        
        # 尝试不同的范围格式
        test_ranges = [
            f"{sheet_id}!A1:C10",  # 带工作表ID
            "A1:C10",              # 不带工作表ID
            f"{sheet_id}!A1:Z20"   # 更大范围
        ]
        
        result = None
        for range_spec in test_ranges:
            try:
                print(f"  尝试范围格式: {range_spec}")
                result = await api_client.find_cells(
                    spreadsheet_token=spreadsheet_token,
                    sheet_id=sheet_id,
                    range_spec=range_spec,
                    find_text="包",
                    match_case=False,
                    match_entire_cell=False,
                    search_by_regex=False,
                    include_formulas=False
                )
                print(f"  ✅ 成功! 使用范围: {range_spec}")
                break
            except Exception as e:
                print(f"  ❌ 失败: {e}")
                continue
        
        if not result:
            raise Exception("所有范围格式都失败了")
        
        print(f"✅ API 调用成功: {result}")
        
    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        import traceback
        print(f"详细错误信息:\n{traceback.format_exc()}")
    
    finally:
        await api_client.close()


if __name__ == "__main__":
    asyncio.run(test_find_direct())