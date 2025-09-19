#!/usr/bin/env python3
"""
Final test to push coverage over 80%.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json
import os

from feishu_spreadsheet_mcp.main import main_async
from feishu_spreadsheet_mcp.tools.spreadsheet_tools import (
    list_spreadsheets,
    get_worksheets,
    read_range,
    read_multiple_ranges,
    find_cells
)
from feishu_spreadsheet_mcp.models.data_models import FeishuAPIError


@pytest.mark.asyncio
async def test_main_async_missing_credentials():
    """Test main_async with missing credentials."""
    # Clear environment variables that might exist
    clean_env = {k: v for k, v in os.environ.items() 
                 if not k.startswith('FEISHU_')}
    
    with patch.dict(os.environ, clean_env, clear=True):
        with patch('sys.argv', ['feishu-spreadsheet-mcp']):
            with pytest.raises(SystemExit) as exc_info:
                await main_async()
            
            assert exc_info.value.code == 1


@pytest.mark.asyncio
async def test_main_async_generate_config():
    """Test main_async with generate config command."""
    test_argv = ['feishu-spreadsheet-mcp', '--create-config', 'test-config.json']
    
    with patch('sys.argv', test_argv):
        with patch('feishu_spreadsheet_mcp.config.config_manager') as mock_manager:
            await main_async()
            
            mock_manager.create_sample_config.assert_called_once_with('test-config.json')


@pytest.mark.asyncio
async def test_main_async_with_config_file():
    """Test main_async with config file."""
    test_env = {
        "FEISHU_APP_ID": "test_id",
        "FEISHU_APP_SECRET": "test_secret"
    }
    
    test_argv = ['feishu-spreadsheet-mcp', '--config', 'test-config.json']
    
    with patch.dict(os.environ, test_env):
        with patch('sys.argv', test_argv):
            with patch('feishu_spreadsheet_mcp.main.run_mcp_server') as mock_run:
                mock_run.return_value = None
                
                await main_async()
                
                mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_list_spreadsheets_folder_token_validation():
    """Test list_spreadsheets folder_token validation."""
    api_client = AsyncMock()
    
    # Test whitespace-only folder_token
    with pytest.raises(ValueError, match="folder_token must be a non-empty string"):
        await list_spreadsheets(api_client, folder_token="   ")


@pytest.mark.asyncio
async def test_list_spreadsheets_invalid_data_handling():
    """Test list_spreadsheets handling invalid data."""
    api_client = AsyncMock()
    
    # Mock response with invalid spreadsheet data
    api_client.list_files.return_value = {
        "data": {
            "files": [
                {
                    "token": "valid_sheet",
                    "name": "Valid Sheet",
                    "type": "sheet",
                    "url": "https://example.com",
                    "created_time": "2023-01-01T00:00:00Z",
                    "modified_time": "2023-01-01T00:00:00Z",
                    "owner_id": "owner1"
                },
                {
                    "token": "invalid_sheet",
                    "name": "Invalid Sheet",
                    "type": "sheet",
                    # Missing required fields like url, created_time, etc.
                }
            ]
        }
    }
    
    # Should skip invalid data and return only valid sheets
    result = await list_spreadsheets(api_client)
    
    assert len(result) == 1
    assert result[0].token == "valid_sheet"


@pytest.mark.asyncio
async def test_get_worksheets_invalid_data_handling():
    """Test get_worksheets handling invalid data."""
    api_client = AsyncMock()
    
    # Mock response with invalid worksheet data
    api_client.get_worksheets.return_value = {
        "data": {
            "sheets": [
                {
                    "sheet_id": "valid_sheet",
                    "title": "Valid Sheet",
                    "index": 0,
                    "row_count": 100,
                    "column_count": 26,
                    "resource_type": "sheet"
                },
                {
                    "sheet_id": "invalid_sheet",
                    "title": "Invalid Sheet",
                    # Missing required fields
                }
            ]
        }
    }
    
    # Should skip invalid data and return only valid sheets
    result = await get_worksheets(api_client, "test_token")
    
    assert len(result) == 1
    assert result[0].sheet_id == "valid_sheet"


@pytest.mark.asyncio
async def test_read_range_data_size_error():
    """Test read_range with data size limit error."""
    api_client = AsyncMock()
    
    # Mock data size limit error
    api_client.read_range.side_effect = FeishuAPIError(
        code=1310218, message="data too large", http_status=413
    )
    
    with pytest.raises(FeishuAPIError) as exc_info:
        await read_range(api_client, "test_token", "Sheet1!A1:Z1000")
    
    assert "返回数据超过10MB限制" in exc_info.value.message


@pytest.mark.asyncio
async def test_read_range_permission_error():
    """Test read_range with permission error."""
    api_client = AsyncMock()
    
    # Mock permission error
    api_client.read_range.side_effect = FeishuAPIError(
        code=1310213, message="permission denied", http_status=403
    )
    
    with pytest.raises(FeishuAPIError) as exc_info:
        await read_range(api_client, "test_token", "Sheet1!A1:B2")
    
    assert "没有读取权限" in exc_info.value.message


@pytest.mark.asyncio
async def test_read_range_sheet_not_found():
    """Test read_range with sheet not found error."""
    api_client = AsyncMock()
    
    # Mock sheet not found error
    api_client.read_range.side_effect = FeishuAPIError(
        code=1310215, message="sheet not found", http_status=404
    )
    
    with pytest.raises(FeishuAPIError) as exc_info:
        await read_range(api_client, "test_token", "InvalidSheet!A1:B2")
    
    assert "指定的工作表不存在" in exc_info.value.message


@pytest.mark.asyncio
async def test_read_multiple_ranges_data_size_error():
    """Test read_multiple_ranges with data size error."""
    api_client = AsyncMock()
    
    # Mock data size limit error
    api_client.read_multiple_ranges.side_effect = FeishuAPIError(
        code=1310218, message="data too large", http_status=413
    )
    
    with pytest.raises(FeishuAPIError) as exc_info:
        await read_multiple_ranges(api_client, "test_token", ["Sheet1!A1:Z1000"])
    
    assert "返回数据超过10MB限制" in exc_info.value.message


@pytest.mark.asyncio
async def test_read_multiple_ranges_permission_error():
    """Test read_multiple_ranges with permission error."""
    api_client = AsyncMock()
    
    # Mock permission error
    api_client.read_multiple_ranges.side_effect = FeishuAPIError(
        code=1310213, message="permission denied", http_status=403
    )
    
    with pytest.raises(FeishuAPIError) as exc_info:
        await read_multiple_ranges(api_client, "test_token", ["Sheet1!A1:B2"])
    
    assert "没有读取权限" in exc_info.value.message


@pytest.mark.asyncio
async def test_find_cells_permission_error():
    """Test find_cells with permission error."""
    api_client = AsyncMock()
    
    # Mock permission error
    api_client.find_cells.side_effect = FeishuAPIError(
        code=1310213, message="permission denied", http_status=403
    )
    
    with pytest.raises(FeishuAPIError) as exc_info:
        await find_cells(api_client, "test_token", "sheet1", "A1:B10", "text")
    
    assert "没有读取权限" in exc_info.value.message


@pytest.mark.asyncio
async def test_find_cells_range_format_error():
    """Test find_cells with range format error."""
    api_client = AsyncMock()
    
    # Mock range format error
    api_client.find_cells.side_effect = FeishuAPIError(
        code=1310216, message="invalid range", http_status=400
    )
    
    with pytest.raises(FeishuAPIError) as exc_info:
        await find_cells(api_client, "test_token", "sheet1", "invalid_range", "text")
    
    assert "范围格式无效" in exc_info.value.message


@pytest.mark.asyncio
async def test_find_cells_unexpected_error():
    """Test find_cells with unexpected error."""
    api_client = AsyncMock()
    
    # Mock unexpected error
    api_client.find_cells.side_effect = ValueError("Unexpected error")
    
    with pytest.raises(FeishuAPIError) as exc_info:
        await find_cells(api_client, "test_token", "sheet1", "A1:B10", "text")
    
    assert "查找单元格时发生错误" in exc_info.value.message
    assert exc_info.value.code == -1


@pytest.mark.asyncio
async def test_get_worksheets_permission_error():
    """Test get_worksheets with permission error."""
    api_client = AsyncMock()
    
    # Mock permission error
    api_client.get_worksheets.side_effect = FeishuAPIError(
        code=1310213, message="permission denied", http_status=403
    )
    
    with pytest.raises(FeishuAPIError) as exc_info:
        await get_worksheets(api_client, "test_token")
    
    assert "没有读取权限" in exc_info.value.message


@pytest.mark.asyncio
async def test_get_worksheets_unexpected_error():
    """Test get_worksheets with unexpected error."""
    api_client = AsyncMock()
    
    # Mock unexpected error
    api_client.get_worksheets.side_effect = RuntimeError("Unexpected error")
    
    with pytest.raises(FeishuAPIError) as exc_info:
        await get_worksheets(api_client, "test_token")
    
    assert "获取工作表列表时发生错误" in exc_info.value.message
    assert exc_info.value.code == -1


@pytest.mark.asyncio
async def test_read_range_unexpected_error():
    """Test read_range with unexpected error."""
    api_client = AsyncMock()
    
    # Mock unexpected error
    api_client.read_range.side_effect = RuntimeError("Unexpected error")
    
    with pytest.raises(FeishuAPIError) as exc_info:
        await read_range(api_client, "test_token", "Sheet1!A1:B2")
    
    assert "读取范围数据时发生错误" in exc_info.value.message
    assert exc_info.value.code == -1


if __name__ == "__main__":
    pytest.main([__file__])