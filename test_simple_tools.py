#!/usr/bin/env python3
"""
Simple test to boost spreadsheet tools coverage.
"""

import pytest
from unittest.mock import AsyncMock

from feishu_spreadsheet_mcp.tools.spreadsheet_tools import (
    list_spreadsheets,
    get_worksheets, 
    read_range,
    read_multiple_ranges,
    find_cells
)
from feishu_spreadsheet_mcp.models.data_models import FeishuAPIError


@pytest.mark.asyncio
async def test_list_spreadsheets_basic():
    """Test basic list_spreadsheets functionality."""
    # Mock API client
    api_client = AsyncMock()
    api_client.list_files.return_value = {
        "data": {
            "files": [
                {
                    "token": "sheet123",
                    "name": "Test Sheet",
                    "type": "sheet",
                    "url": "https://example.com",
                    "created_time": "2023-01-01T00:00:00Z",
                    "modified_time": "2023-01-01T00:00:00Z",
                    "owner_id": "owner123"
                }
            ],
            "page_token": None
        }
    }
    
    result = await list_spreadsheets(api_client, page_size=10)
    
    assert len(result) == 1
    assert result[0].token == "sheet123"
    assert result[0].name == "Test Sheet"


@pytest.mark.asyncio
async def test_list_spreadsheets_validation_errors():
    """Test list_spreadsheets parameter validation."""
    api_client = AsyncMock()
    
    # Test invalid page_size
    with pytest.raises(ValueError, match="page_size must be a positive integer"):
        await list_spreadsheets(api_client, page_size=0)
    
    # Test invalid folder_token
    with pytest.raises(ValueError, match="folder_token must be a non-empty string"):
        await list_spreadsheets(api_client, folder_token="")


@pytest.mark.asyncio
async def test_get_worksheets_basic():
    """Test basic get_worksheets functionality."""
    api_client = AsyncMock()
    api_client.get_worksheets.return_value = {
        "data": {
            "sheets": [
                {
                    "sheet_id": "sheet123",
                    "title": "Sheet1",
                    "index": 0,
                    "row_count": 100,
                    "column_count": 26,
                    "resource_type": "sheet"
                }
            ]
        }
    }
    
    result = await get_worksheets(api_client, "test_token")
    
    assert len(result) == 1
    assert result[0].sheet_id == "sheet123"
    assert result[0].title == "Sheet1"


@pytest.mark.asyncio
async def test_get_worksheets_validation():
    """Test get_worksheets parameter validation."""
    api_client = AsyncMock()
    
    # Test invalid spreadsheet_token
    with pytest.raises(ValueError, match="spreadsheet_token must be a non-empty string"):
        await get_worksheets(api_client, "")


@pytest.mark.asyncio
async def test_read_range_basic():
    """Test basic read_range functionality."""
    api_client = AsyncMock()
    api_client.read_range.return_value = {
        "data": {
            "valueRange": {
                "range": "Sheet1!A1:B2",
                "majorDimension": "ROWS",
                "values": [["A1", "B1"], ["A2", "B2"]],
                "revision": 123
            }
        }
    }
    
    result = await read_range(api_client, "test_token", "Sheet1!A1:B2")
    
    assert result.range == "Sheet1!A1:B2"
    assert result.values == [["A1", "B1"], ["A2", "B2"]]


@pytest.mark.asyncio 
async def test_read_range_validation():
    """Test read_range parameter validation."""
    api_client = AsyncMock()
    
    # Test invalid spreadsheet_token
    with pytest.raises(ValueError, match="spreadsheet_token must be a non-empty string"):
        await read_range(api_client, "", "Sheet1!A1:B2")
    
    # Test invalid value render option
    with pytest.raises(ValueError, match="value_render_option must be one of"):
        await read_range(api_client, "test_token", "Sheet1!A1:B2", value_render_option="Invalid")


@pytest.mark.asyncio
async def test_read_multiple_ranges_basic():
    """Test basic read_multiple_ranges functionality."""
    api_client = AsyncMock()
    api_client.read_multiple_ranges.return_value = {
        "data": {
            "valueRanges": [
                {
                    "range": "Sheet1!A1:B2",
                    "majorDimension": "ROWS", 
                    "values": [["A1", "B1"]],
                    "revision": 123
                }
            ]
        }
    }
    
    result = await read_multiple_ranges(api_client, "test_token", ["Sheet1!A1:B2"])
    
    assert len(result) == 1
    assert result[0].range == "Sheet1!A1:B2"


@pytest.mark.asyncio
async def test_read_multiple_ranges_validation():
    """Test read_multiple_ranges parameter validation."""
    api_client = AsyncMock()
    
    # Test empty ranges
    with pytest.raises(ValueError, match="ranges cannot be empty"):
        await read_multiple_ranges(api_client, "test_token", [])
    
    # Test too many ranges  
    with pytest.raises(ValueError, match="ranges cannot contain more than 100 items"):
        await read_multiple_ranges(api_client, "test_token", ["range"] * 101)


@pytest.mark.asyncio
async def test_find_cells_basic():
    """Test basic find_cells functionality."""
    api_client = AsyncMock()
    api_client.find_cells.return_value = {
        "data": {
            "find_result": {
                "matched_cells": ["A1:A1"],
                "matched_formula_cells": [],
                "rows_count": 1
            }
        }
    }
    
    result = await find_cells(
        api_client, 
        "test_token", 
        "sheet123", 
        "A1:B10", 
        "test"
    )
    
    assert result is not None


@pytest.mark.asyncio
async def test_find_cells_validation():
    """Test find_cells parameter validation."""
    api_client = AsyncMock()
    
    # Test empty find_text
    with pytest.raises(ValueError, match="find_text must be a non-empty string"):
        await find_cells(api_client, "test_token", "sheet123", "A1:B10", "")
    
    # Test invalid regex
    with pytest.raises(ValueError, match="Invalid regular expression"):
        await find_cells(api_client, "test_token", "sheet123", "A1:B10", "[", search_by_regex=True)


if __name__ == "__main__":
    pytest.main([__file__])