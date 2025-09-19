#!/usr/bin/env python3
"""
Test to push coverage over 80%.
"""

import pytest
from unittest.mock import AsyncMock, patch
import json

from feishu_spreadsheet_mcp.tools.spreadsheet_tools import (
    list_spreadsheets,
    get_worksheets, 
    read_range,
    read_multiple_ranges,
    find_cells
)
from feishu_spreadsheet_mcp.models.data_models import FeishuAPIError


@pytest.mark.asyncio
async def test_list_spreadsheets_pagination():
    """Test list_spreadsheets with pagination."""
    api_client = AsyncMock()
    
    # Mock paginated response
    api_client.list_files.side_effect = [
        {
            "data": {
                "files": [
                    {
                        "token": "sheet1",
                        "name": "Sheet 1",
                        "type": "sheet",
                        "url": "https://example.com/1",
                        "created_time": "2023-01-01T00:00:00Z",
                        "modified_time": "2023-01-01T00:00:00Z",
                        "owner_id": "owner1"
                    }
                ],
                "page_token": "next_page"
            }
        },
        {
            "data": {
                "files": [
                    {
                        "token": "sheet2",
                        "name": "Sheet 2",
                        "type": "sheet",
                        "url": "https://example.com/2",
                        "created_time": "2023-01-02T00:00:00Z",
                        "modified_time": "2023-01-02T00:00:00Z",
                        "owner_id": "owner2"
                    }
                ],
                "page_token": None
            }
        }
    ]
    
    result = await list_spreadsheets(api_client, page_size=1)
    
    assert len(result) == 2
    assert result[0].token == "sheet1"
    assert result[1].token == "sheet2"
    assert api_client.list_files.call_count == 2


@pytest.mark.asyncio
async def test_list_spreadsheets_api_error():
    """Test list_spreadsheets with API error."""
    api_client = AsyncMock()
    
    # Mock permission error
    api_client.list_files.side_effect = FeishuAPIError(
        code=1061004, message="permission denied", http_status=403
    )
    
    with pytest.raises(FeishuAPIError) as exc_info:
        await list_spreadsheets(api_client)
    
    assert "没有访问权限" in exc_info.value.message


@pytest.mark.asyncio
async def test_list_spreadsheets_auth_error():
    """Test list_spreadsheets with auth error."""
    api_client = AsyncMock()
    
    # Mock auth error
    auth_error = FeishuAPIError(code=99991663, message="app not found", http_status=200)
    auth_error.is_authentication_error = lambda: True
    api_client.list_files.side_effect = auth_error
    
    with pytest.raises(FeishuAPIError) as exc_info:
        await list_spreadsheets(api_client)
    
    assert "认证失败" in exc_info.value.message


@pytest.mark.asyncio
async def test_list_spreadsheets_unexpected_error():
    """Test list_spreadsheets with unexpected error."""
    api_client = AsyncMock()
    
    # Mock unexpected error
    api_client.list_files.side_effect = ValueError("Unexpected error")
    
    with pytest.raises(FeishuAPIError) as exc_info:
        await list_spreadsheets(api_client)
    
    assert "获取电子表格列表时发生错误" in exc_info.value.message
    assert exc_info.value.code == -1


@pytest.mark.asyncio 
async def test_get_worksheets_api_errors():
    """Test get_worksheets with various API errors."""
    api_client = AsyncMock()
    
    # Test spreadsheet not found
    api_client.get_worksheets.side_effect = FeishuAPIError(
        code=1310214, message="spreadsheet not found", http_status=404
    )
    
    with pytest.raises(FeishuAPIError) as exc_info:
        await get_worksheets(api_client, "test_token")
    
    assert "指定的电子表格不存在" in exc_info.value.message


@pytest.mark.asyncio
async def test_read_range_validation_errors():
    """Test read_range validation errors."""
    api_client = AsyncMock()
    
    # Test invalid range specification
    with pytest.raises(ValueError):
        await read_range(api_client, "test_token", "invalid_range")


@pytest.mark.asyncio
async def test_read_range_api_errors():
    """Test read_range with API errors."""
    api_client = AsyncMock()
    
    # Mock range format error
    api_client.read_range.side_effect = FeishuAPIError(
        code=1310216, message="range format error", http_status=400
    )
    
    with pytest.raises(FeishuAPIError) as exc_info:
        await read_range(api_client, "test_token", "Sheet1!A1:B2")
    
    assert "范围格式无效" in exc_info.value.message


@pytest.mark.asyncio
async def test_read_multiple_ranges_invalid_range():
    """Test read_multiple_ranges with invalid range in list."""
    api_client = AsyncMock()
    
    # Test invalid range in list
    with pytest.raises(ValueError, match="Invalid range at index 1"):
        await read_multiple_ranges(api_client, "test_token", ["Sheet1!A1:B2", "invalid"])


@pytest.mark.asyncio
async def test_read_multiple_ranges_invalid_data():
    """Test read_multiple_ranges with invalid response data."""
    api_client = AsyncMock()
    api_client.read_multiple_ranges.return_value = {
        "data": {
            "valueRanges": [
                {
                    "range": "Sheet1!A1:B2",
                    "majorDimension": "ROWS",
                    "values": [["A1", "B1"]],
                    "revision": 123
                },
                {
                    # Invalid data that will cause parsing error
                    "range": "Sheet2!A1:B2",
                    # Missing required fields
                }
            ]
        }
    }
    
    # Should continue processing and create placeholder for invalid data
    result = await read_multiple_ranges(api_client, "test_token", ["Sheet1!A1:B2", "Sheet2!A1:B2"])
    
    assert len(result) == 2
    assert result[0].range == "Sheet1!A1:B2"
    assert result[1].range == "Sheet2!A1:B2"  # Should have placeholder


@pytest.mark.asyncio
async def test_find_cells_regex_validation():
    """Test find_cells regex validation."""
    api_client = AsyncMock()
    
    # Test valid regex
    api_client.find_cells.return_value = {
        "data": {
            "find_result": {
                "matched_cells": ["A1:A1"],
                "matched_formula_cells": [],
                "rows_count": 1
            }
        }
    }
    
    # Should not raise for valid regex
    result = await find_cells(
        api_client, "test_token", "sheet1", "A1:B10", 
        r"\d+", search_by_regex=True
    )
    assert result is not None


@pytest.mark.asyncio
async def test_find_cells_api_errors():
    """Test find_cells with various API errors."""
    api_client = AsyncMock()
    
    # Test sheet not found
    api_client.find_cells.side_effect = FeishuAPIError(
        code=1310215, message="sheet not found", http_status=404
    )
    
    with pytest.raises(FeishuAPIError) as exc_info:
        await find_cells(api_client, "test_token", "invalid_sheet", "A1:B10", "text")
    
    assert "指定的工作表不存在" in exc_info.value.message


@pytest.mark.asyncio
async def test_find_cells_regex_error():
    """Test find_cells with regex API error."""
    api_client = AsyncMock()
    
    # Mock regex error from API - but use valid regex to pass validation
    api_client.find_cells.side_effect = FeishuAPIError(
        code=1310219, message="invalid regex", http_status=400
    )
    
    with pytest.raises(FeishuAPIError) as exc_info:
        await find_cells(api_client, "test_token", "sheet1", "A1:B10", r"\w+", search_by_regex=True)
    
    assert "正则表达式格式无效" in exc_info.value.message


def test_range_page_size_limits():  
    """Test page_size limits in list_spreadsheets."""
    import asyncio
    
    async def run_test():
        api_client = AsyncMock()
        api_client.list_files.return_value = {"data": {"files": []}}
        
        # Test page_size over 200 gets capped
        await list_spreadsheets(api_client, page_size=300)
        
        # Should have been called with capped page size
        call_args = api_client.list_files.call_args
        assert call_args.kwargs["page_size"] == 200
    
    asyncio.run(run_test())


if __name__ == "__main__":
    pytest.main([__file__])