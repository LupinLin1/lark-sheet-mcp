#!/usr/bin/env python3
"""
读取完整的表格数据并搜索客户转化漏斗相关信息
"""

import asyncio
from feishu_spreadsheet_mcp.services.auth_manager import AuthenticationManager
from feishu_spreadsheet_mcp.services.api_client import FeishuAPIClient
from feishu_spreadsheet_mcp.tools.spreadsheet_tools import get_worksheets, read_range, find_cells

async def read_full_spreadsheet_data():
    """读取完整表格数据并搜索客户转化漏斗相关信息"""
    
    app_id = "cli_a80a58f563f8500c"
    app_secret = "59cn2FCWvmKZ6Y7hGyDnKeJ0xeZgU0Yh"
    # 用户提供的新表格链接: https://zuvjnsu1rw.feishu.cn/sheets/Hyj2sNNTxhf1latlxgBcgo1mncf?sheet=k1OMbE
    # 提取表格token: Hyj2sNNTxhf1latlxgBcgo1mncf
    # 工作表ID: k1OMbE
    spreadsheet_token = "Hyj2sNNTxhf1latlxgBcgo1mncf"
    
    print(f"Reading full data from spreadsheet: {spreadsheet_token}")
    
    # Initialize auth manager and API client
    auth_manager = AuthenticationManager(app_id, app_secret)
    api_client = FeishuAPIClient(auth_manager)
    
    try:
        # Get all worksheets
        worksheets_result = await get_worksheets(api_client, spreadsheet_token)
        worksheets = worksheets_result.get('worksheets', [])
        
        print(f"Found {len(worksheets)} worksheets:")
        
        for worksheet in worksheets:
            sheet_title = worksheet.get('title')
            sheet_id = worksheet.get('sheet_id')
            row_count = worksheet.get('row_count', 0)
            col_count = worksheet.get('column_count', 0)
            
            print(f"\n=== 工作表: {sheet_title} (ID: {sheet_id}) ===")
            print(f"大小: {row_count} 行 x {col_count} 列")
            
            if sheet_id:
                try:
                    # Read a larger range to see more data
                    max_rows = min(50, row_count) if row_count > 0 else 50
                    max_cols_letter = chr(ord('A') + min(10, col_count) - 1) if col_count > 0 else 'J'
                    range_spec = f"{sheet_id}!A1:{max_cols_letter}{max_rows}"
                    
                    print(f"Reading range: {range_spec}")
                    range_result = await read_range(api_client, spreadsheet_token, range_spec)
                    values = range_result.get('values', [])
                    
                    print(f"实际数据行数: {len(values)}")
                    
                    # Display the data
                    for i, row in enumerate(values):
                        if row and any(cell for cell in row if cell):  # Skip completely empty rows
                            # Convert None values to empty strings for display
                            display_row = [str(cell) if cell is not None else '' for cell in row]
                            print(f"第{i+1}行: {display_row}")
                    
                    # Search for funnel-related keywords
                    funnel_keywords = ["转化", "漏斗", "客户", "潜客", "线索", "成交", "转换", "获客", "销售", "营销"]
                    
                    print(f"\n搜索转化漏斗相关关键词...")
                    for keyword in funnel_keywords:
                        try:
                            search_result = await find_cells(
                                api_client,
                                spreadsheet_token,
                                sheet_id,
                                f"A1:{max_cols_letter}{max_rows}",
                                keyword
                            )
                            
                            if search_result.get('has_matches'):
                                matched_cells = search_result.get('matched_cells', [])
                                print(f"  找到关键词 '{keyword}': {len(matched_cells)} 个匹配")
                                for cell in matched_cells[:5]:  # Show first 5 matches
                                    print(f"    - {cell}")
                        except Exception as e:
                            print(f"  搜索关键词 '{keyword}' 时出错: {e}")
                    
                except Exception as e:
                    print(f"读取工作表 {sheet_title} 数据时出错: {e}")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(read_full_spreadsheet_data())