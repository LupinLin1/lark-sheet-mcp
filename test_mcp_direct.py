#!/usr/bin/env python3
"""
Direct test of MCP server functionality without MCP protocol.
"""

import os
import asyncio
from feishu_spreadsheet_mcp.services.auth_manager import AuthenticationManager
from feishu_spreadsheet_mcp.services.api_client import FeishuAPIClient
from feishu_spreadsheet_mcp.tools.spreadsheet_tools import list_spreadsheets

async def test_direct_connection():
    """Test direct connection to Feishu API."""
    app_id = "cli_a80a58f563f8500c"
    app_secret = "59cn2FCWvmKZ6Y7hGyDnKeJ0xeZgU0Yh"
    
    print(f"Testing with app_id: {app_id[:10]}...")
    
    # Initialize auth manager
    auth_manager = AuthenticationManager(app_id, app_secret)
    
    # Initialize API client  
    api_client = FeishuAPIClient(auth_manager)
    
    try:
        # Test listing spreadsheets
        print("Attempting to list spreadsheets...")
        result = await list_spreadsheets(api_client, page_size=10)
        
        print(f"Success! Found {len(result.get('spreadsheets', []))} spreadsheets:")
        for sheet in result.get('spreadsheets', []):
            print(f"  - {sheet.get('name')}: {sheet.get('token')}")
        
        # Try accessing the known test spreadsheet
        print("\nTrying to access known test spreadsheet...")
        spreadsheet_token = "NYSgsgSKAhKE7ntp133cvpjtnUg"
        
        from feishu_spreadsheet_mcp.tools.spreadsheet_tools import get_worksheets, read_range
        
        # Get worksheets for the known spreadsheet
        worksheets_result = await get_worksheets(api_client, spreadsheet_token)
        print(f"Found {len(worksheets_result.get('worksheets', []))} worksheets:")
        
        for worksheet in worksheets_result.get('worksheets', []):
            print(f"  - {worksheet.get('title')} (ID: {worksheet.get('sheet_id')})")
            
            # Try to read some data from each worksheet
            sheet_id = worksheet.get('sheet_id')
            if sheet_id:
                try:
                    # Read a small range to see what data is there
                    range_result = await read_range(api_client, spreadsheet_token, f"{sheet_id}!A1:E10")
                    print(f"    Sample data from {worksheet.get('title')}:")
                    values = range_result.get('values', [])
                    for i, row in enumerate(values[:5]):  # Show first 5 rows
                        if row:  # Skip empty rows
                            print(f"      Row {i+1}: {row}")
                except Exception as e:
                    print(f"    Error reading data: {e}")
        
        return result
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(test_direct_connection())
    if result and result.get('spreadsheets'):
        print(f"\nFound {len(result['spreadsheets'])} spreadsheets total")