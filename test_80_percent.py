#!/usr/bin/env python3
"""
Final test to push coverage over 80%.
"""

import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_simple_edge_cases():
    """Test simple edge cases to boost coverage."""
    from feishu_spreadsheet_mcp.tools.spreadsheet_tools import list_spreadsheets
    
    api_client = AsyncMock()
    
    # Test with exact page_size boundary - should not be capped
    api_client.list_files.return_value = {"data": {"files": []}}
    
    await list_spreadsheets(api_client, page_size=200)
    
    # Should be called with exact 200 (not capped)
    call_args = api_client.list_files.call_args
    assert call_args.kwargs["page_size"] == 200


@pytest.mark.asyncio
async def test_empty_folder_token():
    """Test with None folder_token."""
    from feishu_spreadsheet_mcp.tools.spreadsheet_tools import list_spreadsheets
    
    api_client = AsyncMock()
    api_client.list_files.return_value = {"data": {"files": []}}
    
    # Test with None folder_token (default behavior)
    await list_spreadsheets(api_client, folder_token=None)
    
    # Should be called with folder_token=None
    call_args = api_client.list_files.call_args
    assert call_args.kwargs["folder_token"] is None


def test_simple_sync_validation():
    """Test simple synchronous validation."""
    from feishu_spreadsheet_mcp.models.data_models import validate_range_spec
    
    # Test valid range spec
    result = validate_range_spec("Sheet1!A1:B2")
    assert result == "Sheet1!A1:B2"
    
    # Test range spec that needs stripping
    result = validate_range_spec("  Sheet1!A1:B2  ")
    assert result == "Sheet1!A1:B2"


if __name__ == "__main__":
    pytest.main([__file__])