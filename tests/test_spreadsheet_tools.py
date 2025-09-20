"""
Tests for spreadsheet tools.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from src.models.data_models import FeishuAPIError, SpreadsheetInfo, WorksheetInfo, RangeData, FindResult
from src.tools import (
    find_cells,
    get_worksheets,
    list_spreadsheets,
    read_multiple_ranges,
    read_range,
)


class TestListSpreadsheetsFunction:
    """Test list_spreadsheets function."""

    @pytest.fixture
    def mock_api_client(self):
        """Create mock API client."""
        return AsyncMock()

    @pytest.fixture
    def sample_api_response(self):
        """Sample API response with spreadsheet data."""
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "files": [
                    {
                        "token": "shtcnmBA*****yGehy8",
                        "name": "测试电子表格",
                        "type": "sheet",
                        "url": "https://example.feishu.cn/sheets/shtcnmBA*****yGehy8",
                        "created_time": "2023-01-01T10:00:00Z",
                        "modified_time": "2023-01-02T15:30:00Z",
                        "owner_id": "ou_123456789"
                    },
                    {
                        "token": "docxcnmBA*****yGehy9",
                        "name": "测试文档",
                        "type": "doc",  # Not a spreadsheet
                        "url": "https://example.feishu.cn/docs/docxcnmBA*****yGehy9",
                        "created_time": "2023-01-01T10:00:00Z",
                        "modified_time": "2023-01-02T15:30:00Z",
                        "owner_id": "ou_123456789"
                    },
                    {
                        "token": "shtcnmBA*****yGehy10",
                        "name": "另一个电子表格",
                        "type": "sheet",
                        "url": "https://example.feishu.cn/sheets/shtcnmBA*****yGehy10",
                        "created_time": "2023-01-03T08:00:00Z",
                        "modified_time": "2023-01-03T16:45:00Z",
                        "owner_id": "ou_987654321"
                    }
                ],
                "page_token": None
            }
        }

    @pytest.fixture
    def sample_paginated_response_page1(self):
        """First page of paginated response."""
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "files": [
                    {
                        "token": "shtcnmBA*****yGehy1",
                        "name": "电子表格1",
                        "type": "sheet",
                        "url": "https://example.feishu.cn/sheets/shtcnmBA*****yGehy1",
                        "created_time": "2023-01-01T10:00:00Z",
                        "modified_time": "2023-01-02T15:30:00Z",
                        "owner_id": "ou_123456789"
                    }
                ],
                "page_token": "next_page_token"
            }
        }

    @pytest.fixture
    def sample_paginated_response_page2(self):
        """Second page of paginated response."""
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "files": [
                    {
                        "token": "shtcnmBA*****yGehy2",
                        "name": "电子表格2",
                        "type": "sheet",
                        "url": "https://example.feishu.cn/sheets/shtcnmBA*****yGehy2",
                        "created_time": "2023-01-03T08:00:00Z",
                        "modified_time": "2023-01-03T16:45:00Z",
                        "owner_id": "ou_987654321"
                    }
                ],
                "page_token": None
            }
        }

    @pytest.mark.asyncio
    async def test_list_spreadsheets_success(self, mock_api_client, sample_api_response):
        """Test successful spreadsheet listing."""
        mock_api_client.list_files.return_value = sample_api_response

        result = await list_spreadsheets(mock_api_client)

        # Should return only spreadsheets (type="sheet")
        assert len(result) == 2
        assert all(isinstance(item, SpreadsheetInfo) for item in result)
        assert result[0].name == "测试电子表格"
        assert result[0].type == "sheet"
        assert result[1].name == "另一个电子表格"
        assert result[1].type == "sheet"

        # Verify API was called correctly
        mock_api_client.list_files.assert_called_once_with(
            folder_token=None, page_size=50
        )

    @pytest.mark.asyncio
    async def test_list_spreadsheets_with_folder_token(self, mock_api_client, sample_api_response):
        """Test spreadsheet listing with folder token."""
        mock_api_client.list_files.return_value = sample_api_response

        result = await list_spreadsheets(mock_api_client, folder_token="test_folder_token")

        assert len(result) == 2
        mock_api_client.list_files.assert_called_once_with(
            folder_token="test_folder_token", page_size=50
        )

    @pytest.mark.asyncio
    async def test_list_spreadsheets_with_custom_page_size(self, mock_api_client, sample_api_response):
        """Test spreadsheet listing with custom page size."""
        mock_api_client.list_files.return_value = sample_api_response

        result = await list_spreadsheets(mock_api_client, page_size=100)

        assert len(result) == 2
        mock_api_client.list_files.assert_called_once_with(
            folder_token=None, page_size=100
        )

    @pytest.mark.asyncio
    async def test_list_spreadsheets_page_size_limit(self, mock_api_client, sample_api_response):
        """Test that page size is limited to 200."""
        mock_api_client.list_files.return_value = sample_api_response

        result = await list_spreadsheets(mock_api_client, page_size=300)

        assert len(result) == 2
        mock_api_client.list_files.assert_called_once_with(
            folder_token=None, page_size=200
        )

    @pytest.mark.asyncio
    async def test_list_spreadsheets_pagination(
        self, mock_api_client, sample_paginated_response_page1, sample_paginated_response_page2
    ):
        """Test pagination handling."""
        mock_api_client.list_files.side_effect = [
            sample_paginated_response_page1,
            sample_paginated_response_page2
        ]

        result = await list_spreadsheets(mock_api_client)

        # Should return results from both pages
        assert len(result) == 2
        assert result[0].name == "电子表格1"
        assert result[1].name == "电子表格2"

        # Should make two API calls
        assert mock_api_client.list_files.call_count == 2
        
        # First call without page_token
        first_call = mock_api_client.list_files.call_args_list[0]
        assert first_call[1] == {"folder_token": None, "page_size": 50}
        
        # Second call with page_token
        second_call = mock_api_client.list_files.call_args_list[1]
        assert second_call[1] == {"folder_token": None, "page_size": 50, "page_token": "next_page_token"}

    @pytest.mark.asyncio
    async def test_list_spreadsheets_empty_result(self, mock_api_client):
        """Test handling of empty result."""
        mock_api_client.list_files.return_value = {
            "code": 0,
            "msg": "success",
            "data": {
                "files": [],
                "page_token": None
            }
        }

        result = await list_spreadsheets(mock_api_client)

        assert result == []

    @pytest.mark.asyncio
    async def test_list_spreadsheets_no_spreadsheets(self, mock_api_client):
        """Test handling when no spreadsheets are found."""
        mock_api_client.list_files.return_value = {
            "code": 0,
            "msg": "success",
            "data": {
                "files": [
                    {
                        "token": "docxcnmBA*****yGehy9",
                        "name": "测试文档",
                        "type": "doc",
                        "url": "https://example.feishu.cn/docs/docxcnmBA*****yGehy9",
                        "created_time": "2023-01-01T10:00:00Z",
                        "modified_time": "2023-01-02T15:30:00Z",
                        "owner_id": "ou_123456789"
                    }
                ],
                "page_token": None
            }
        }

        result = await list_spreadsheets(mock_api_client)

        assert result == []

    @pytest.mark.asyncio
    async def test_list_spreadsheets_invalid_page_size(self, mock_api_client):
        """Test validation of page_size parameter."""
        with pytest.raises(ValueError, match="page_size must be a positive integer"):
            await list_spreadsheets(mock_api_client, page_size=0)

        with pytest.raises(ValueError, match="page_size must be a positive integer"):
            await list_spreadsheets(mock_api_client, page_size=-1)

        with pytest.raises(ValueError, match="page_size must be a positive integer"):
            await list_spreadsheets(mock_api_client, page_size="invalid")

    @pytest.mark.asyncio
    async def test_list_spreadsheets_invalid_folder_token(self, mock_api_client):
        """Test validation of folder_token parameter."""
        with pytest.raises(ValueError, match="folder_token must be a non-empty string if provided"):
            await list_spreadsheets(mock_api_client, folder_token="")

        with pytest.raises(ValueError, match="folder_token must be a non-empty string if provided"):
            await list_spreadsheets(mock_api_client, folder_token="   ")

        with pytest.raises(ValueError, match="folder_token must be a non-empty string if provided"):
            await list_spreadsheets(mock_api_client, folder_token=123)

    @pytest.mark.asyncio
    async def test_list_spreadsheets_permission_error(self, mock_api_client):
        """Test handling of permission errors."""
        mock_api_client.list_files.side_effect = FeishuAPIError(
            code=1061004,
            message="Permission denied",
            http_status=403
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await list_spreadsheets(mock_api_client)

        assert exc_info.value.code == 1061004
        assert "没有访问权限" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_list_spreadsheets_authentication_error(self, mock_api_client):
        """Test handling of authentication errors."""
        mock_api_client.list_files.side_effect = FeishuAPIError(
            code=99991663,
            message="Invalid access token",
            http_status=401
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await list_spreadsheets(mock_api_client)

        assert exc_info.value.code == 99991663
        assert "认证失败" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_list_spreadsheets_api_error(self, mock_api_client):
        """Test handling of other API errors."""
        mock_api_client.list_files.side_effect = FeishuAPIError(
            code=1310217,
            message="Too many requests",
            http_status=429
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await list_spreadsheets(mock_api_client)

        assert exc_info.value.code == 1310217
        assert exc_info.value.message == "Too many requests"

    @pytest.mark.asyncio
    async def test_list_spreadsheets_unexpected_error(self, mock_api_client):
        """Test handling of unexpected errors."""
        mock_api_client.list_files.side_effect = Exception("Unexpected error")

        with pytest.raises(FeishuAPIError) as exc_info:
            await list_spreadsheets(mock_api_client)

        assert exc_info.value.code == -1
        assert "获取电子表格列表时发生错误" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_list_spreadsheets_invalid_data_skipped(self, mock_api_client, caplog):
        """Test that invalid spreadsheet data is skipped with warning."""
        mock_api_client.list_files.return_value = {
            "code": 0,
            "msg": "success",
            "data": {
                "files": [
                    {
                        "token": "shtcnmBA*****yGehy8",
                        "name": "有效电子表格",
                        "type": "sheet",
                        "url": "https://example.feishu.cn/sheets/shtcnmBA*****yGehy8",
                        "created_time": "2023-01-01T10:00:00Z",
                        "modified_time": "2023-01-02T15:30:00Z",
                        "owner_id": "ou_123456789"
                    },
                    {
                        # Missing required fields
                        "token": "shtcnmBA*****invalid",
                        "type": "sheet"
                    }
                ],
                "page_token": None
            }
        }

        result = await list_spreadsheets(mock_api_client)

        # Should return only valid spreadsheets
        assert len(result) == 1
        assert result[0].name == "有效电子表格"

        # Should log warning for invalid data
        assert "Skipping invalid spreadsheet data" in caplog.text


class TestGetWorksheetsFunction:
    """Test get_worksheets function."""

    @pytest.fixture
    def mock_api_client(self):
        """Create mock API client."""
        return AsyncMock()

    @pytest.fixture
    def sample_worksheets_response(self):
        """Sample API response with worksheet data."""
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "sheets": [
                    {
                        "sheet_id": "sheet123",
                        "title": "工作表1",
                        "index": 0,
                        "hidden": False,
                        "row_count": 1000,
                        "column_count": 26,
                        "frozen_row_count": 1,
                        "frozen_column_count": 0,
                        "resource_type": "sheet",
                        "merges": [
                            {
                                "start_row_index": 0,
                                "end_row_index": 1,
                                "start_column_index": 0,
                                "end_column_index": 2
                            }
                        ]
                    },
                    {
                        "sheet_id": "sheet456",
                        "title": "隐藏工作表",
                        "index": 1,
                        "hidden": True,
                        "row_count": 500,
                        "column_count": 10,
                        "frozen_row_count": 0,
                        "frozen_column_count": 1,
                        "resource_type": "sheet"
                    }
                ]
            }
        }

    @pytest.mark.asyncio
    async def test_get_worksheets_success(self, mock_api_client, sample_worksheets_response):
        """Test successful worksheet listing."""
        mock_api_client.get_worksheets.return_value = sample_worksheets_response

        result = await get_worksheets(mock_api_client, "test_spreadsheet_token")

        assert len(result) == 2
        assert all(isinstance(item, WorksheetInfo) for item in result)
        
        # Check first worksheet
        assert result[0].sheet_id == "sheet123"
        assert result[0].title == "工作表1"
        assert result[0].index == 0
        assert result[0].hidden is False
        assert result[0].row_count == 1000
        assert result[0].column_count == 26
        assert result[0].frozen_row_count == 1
        assert result[0].frozen_column_count == 0
        assert result[0].resource_type == "sheet"
        assert result[0].merges is not None
        assert len(result[0].merges) == 1

        # Check second worksheet
        assert result[1].sheet_id == "sheet456"
        assert result[1].title == "隐藏工作表"
        assert result[1].index == 1
        assert result[1].hidden is True
        assert result[1].row_count == 500
        assert result[1].column_count == 10
        assert result[1].frozen_row_count == 0
        assert result[1].frozen_column_count == 1
        assert result[1].resource_type == "sheet"
        assert result[1].merges is None

        # Verify API was called correctly
        mock_api_client.get_worksheets.assert_called_once_with("test_spreadsheet_token")

    @pytest.mark.asyncio
    async def test_get_worksheets_empty_result(self, mock_api_client):
        """Test handling of empty worksheet list."""
        mock_api_client.get_worksheets.return_value = {
            "code": 0,
            "msg": "success",
            "data": {
                "sheets": []
            }
        }

        result = await get_worksheets(mock_api_client, "test_spreadsheet_token")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_worksheets_invalid_token(self, mock_api_client):
        """Test validation of spreadsheet_token parameter."""
        with pytest.raises(ValueError, match="spreadsheet_token must be a non-empty string"):
            await get_worksheets(mock_api_client, "")

        with pytest.raises(ValueError, match="spreadsheet_token cannot be empty or whitespace only"):
            await get_worksheets(mock_api_client, "   ")

        with pytest.raises(ValueError, match="spreadsheet_token must be a non-empty string"):
            await get_worksheets(mock_api_client, None)

        with pytest.raises(ValueError, match="spreadsheet_token must be a non-empty string"):
            await get_worksheets(mock_api_client, 123)

    @pytest.mark.asyncio
    async def test_get_worksheets_spreadsheet_not_found(self, mock_api_client):
        """Test handling of spreadsheet not found error."""
        mock_api_client.get_worksheets.side_effect = FeishuAPIError(
            code=1310214,
            message="Spreadsheet not found",
            http_status=404
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await get_worksheets(mock_api_client, "invalid_token")

        assert exc_info.value.code == 1310214
        assert "指定的电子表格不存在" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_get_worksheets_permission_error(self, mock_api_client):
        """Test handling of permission errors."""
        mock_api_client.get_worksheets.side_effect = FeishuAPIError(
            code=1310213,
            message="Permission denied",
            http_status=403
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await get_worksheets(mock_api_client, "test_spreadsheet_token")

        assert exc_info.value.code == 1310213
        assert "没有读取权限" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_get_worksheets_authentication_error(self, mock_api_client):
        """Test handling of authentication errors."""
        mock_api_client.get_worksheets.side_effect = FeishuAPIError(
            code=99991663,
            message="Invalid access token",
            http_status=401
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await get_worksheets(mock_api_client, "test_spreadsheet_token")

        assert exc_info.value.code == 99991663
        assert "认证失败" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_get_worksheets_api_error(self, mock_api_client):
        """Test handling of other API errors."""
        mock_api_client.get_worksheets.side_effect = FeishuAPIError(
            code=1310217,
            message="Too many requests",
            http_status=429
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await get_worksheets(mock_api_client, "test_spreadsheet_token")

        assert exc_info.value.code == 1310217
        assert exc_info.value.message == "Too many requests"

    @pytest.mark.asyncio
    async def test_get_worksheets_unexpected_error(self, mock_api_client):
        """Test handling of unexpected errors."""
        mock_api_client.get_worksheets.side_effect = Exception("Unexpected error")

        with pytest.raises(FeishuAPIError) as exc_info:
            await get_worksheets(mock_api_client, "test_spreadsheet_token")

        assert exc_info.value.code == -1
        assert "获取工作表列表时发生错误" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_get_worksheets_invalid_data_skipped(self, mock_api_client, caplog):
        """Test that invalid worksheet data is skipped with warning."""
        mock_api_client.get_worksheets.return_value = {
            "code": 0,
            "msg": "success",
            "data": {
                "sheets": [
                    {
                        "sheet_id": "sheet123",
                        "title": "有效工作表",
                        "index": 0,
                        "hidden": False,
                        "row_count": 1000,
                        "column_count": 26,
                        "frozen_row_count": 0,
                        "frozen_column_count": 0,
                        "resource_type": "sheet"
                    },
                    {
                        # Missing required fields
                        "sheet_id": "invalid_sheet",
                        "title": "无效工作表"
                    }
                ]
            }
        }

        result = await get_worksheets(mock_api_client, "test_spreadsheet_token")

        # Should return only valid worksheets
        assert len(result) == 1
        assert result[0].title == "有效工作表"

        # Should log warning for invalid data
        assert "Skipping invalid worksheet data" in caplog.text

    @pytest.mark.asyncio
    async def test_get_worksheets_with_merges(self, mock_api_client):
        """Test handling of worksheets with merge information."""
        mock_api_client.get_worksheets.return_value = {
            "code": 0,
            "msg": "success",
            "data": {
                "sheets": [
                    {
                        "sheet_id": "sheet123",
                        "title": "带合并单元格的工作表",
                        "index": 0,
                        "hidden": False,
                        "row_count": 100,
                        "column_count": 10,
                        "frozen_row_count": 0,
                        "frozen_column_count": 0,
                        "resource_type": "sheet",
                        "merges": [
                            {
                                "start_row_index": 0,
                                "end_row_index": 1,
                                "start_column_index": 0,
                                "end_column_index": 2
                            },
                            {
                                "start_row_index": 2,
                                "end_row_index": 3,
                                "start_column_index": 1,
                                "end_column_index": 3
                            }
                        ]
                    }
                ]
            }
        }

        result = await get_worksheets(mock_api_client, "test_spreadsheet_token")

        assert len(result) == 1
        assert result[0].merges is not None
        assert len(result[0].merges) == 2
        assert result[0].merges[0]["start_row_index"] == 0
        assert result[0].merges[1]["start_row_index"] == 2


class TestReadRangeFunction:
    """Test read_range function."""

    @pytest.fixture
    def mock_api_client(self):
        """Create mock API client."""
        return AsyncMock()

    @pytest.fixture
    def sample_range_response(self):
        """Sample API response with range data."""
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "valueRange": {
                    "range": "sheet123!A1:C3",
                    "majorDimension": "ROWS",
                    "values": [
                        ["Name", "Age", "City"],
                        ["Alice", "25", "New York"],
                        ["Bob", "30", "London"]
                    ],
                    "revision": 12345
                }
            }
        }

    @pytest.fixture
    def sample_empty_range_response(self):
        """Sample API response with empty range data."""
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "valueRange": {
                    "range": "sheet123!A1:A1",
                    "majorDimension": "ROWS",
                    "values": [],
                    "revision": 12345
                }
            }
        }

    @pytest.mark.asyncio
    async def test_read_range_success(self, mock_api_client, sample_range_response):
        """Test successful range reading."""
        mock_api_client.read_range.return_value = sample_range_response

        result = await read_range(
            mock_api_client,
            "test_spreadsheet_token",
            "sheet123!A1:C3"
        )

        assert isinstance(result, RangeData)
        assert result.range == "sheet123!A1:C3"
        assert result.major_dimension == "ROWS"
        assert len(result.values) == 3
        assert result.values[0] == ["Name", "Age", "City"]
        assert result.values[1] == ["Alice", "25", "New York"]
        assert result.values[2] == ["Bob", "30", "London"]
        assert result.revision == 12345

        # Verify API was called correctly
        mock_api_client.read_range.assert_called_once_with(
            spreadsheet_token="test_spreadsheet_token",
            range_spec="sheet123!A1:C3",
            value_render_option="UnformattedValue",
            date_time_render_option="FormattedString"
        )

    @pytest.mark.asyncio
    async def test_read_range_with_options(self, mock_api_client, sample_range_response):
        """Test range reading with custom options."""
        mock_api_client.read_range.return_value = sample_range_response

        result = await read_range(
            mock_api_client,
            "test_spreadsheet_token",
            "sheet123!A1:C3",
            value_render_option="FormattedValue",
            date_time_render_option="FormattedString"
        )

        assert isinstance(result, RangeData)
        mock_api_client.read_range.assert_called_once_with(
            spreadsheet_token="test_spreadsheet_token",
            range_spec="sheet123!A1:C3",
            value_render_option="FormattedValue",
            date_time_render_option="FormattedString"
        )

    @pytest.mark.asyncio
    async def test_read_range_empty_result(self, mock_api_client, sample_empty_range_response):
        """Test handling of empty range result."""
        mock_api_client.read_range.return_value = sample_empty_range_response

        result = await read_range(
            mock_api_client,
            "test_spreadsheet_token",
            "sheet123!A1:A1"
        )

        assert isinstance(result, RangeData)
        assert result.range == "sheet123!A1:A1"
        assert result.values == []
        assert result.is_empty()

    @pytest.mark.asyncio
    async def test_read_range_invalid_spreadsheet_token(self, mock_api_client):
        """Test validation of spreadsheet_token parameter."""
        with pytest.raises(ValueError, match="spreadsheet_token must be a non-empty string"):
            await read_range(mock_api_client, "", "sheet123!A1:B10")

        with pytest.raises(ValueError, match="spreadsheet_token cannot be empty or whitespace only"):
            await read_range(mock_api_client, "   ", "sheet123!A1:B10")

        with pytest.raises(ValueError, match="spreadsheet_token must be a non-empty string"):
            await read_range(mock_api_client, None, "sheet123!A1:B10")

        with pytest.raises(ValueError, match="spreadsheet_token must be a non-empty string"):
            await read_range(mock_api_client, 123, "sheet123!A1:B10")

    @pytest.mark.asyncio
    async def test_read_range_invalid_range_spec(self, mock_api_client):
        """Test validation of range_spec parameter."""
        with pytest.raises(ValueError, match="Range specification must include sheet ID"):
            await read_range(mock_api_client, "test_token", "A1:B10")

        with pytest.raises(ValueError, match="Sheet ID cannot be empty"):
            await read_range(mock_api_client, "test_token", "!A1:B10")

        with pytest.raises(ValueError, match="Range part cannot be empty"):
            await read_range(mock_api_client, "test_token", "sheet123!")

        with pytest.raises(ValueError, match="Invalid range format"):
            await read_range(mock_api_client, "test_token", "sheet123!invalid_range")

    @pytest.mark.asyncio
    async def test_read_range_invalid_value_render_option(self, mock_api_client):
        """Test validation of value_render_option parameter."""
        with pytest.raises(ValueError, match="value_render_option must be one of"):
            await read_range(
                mock_api_client,
                "test_token",
                "sheet123!A1:B10",
                value_render_option="InvalidOption"
            )

    @pytest.mark.asyncio
    async def test_read_range_invalid_date_time_render_option(self, mock_api_client):
        """Test validation of date_time_render_option parameter."""
        with pytest.raises(ValueError, match="date_time_render_option must be one of"):
            await read_range(
                mock_api_client,
                "test_token",
                "sheet123!A1:B10",
                date_time_render_option="InvalidOption"
            )

    @pytest.mark.asyncio
    async def test_read_range_all_value_render_options(self, mock_api_client, sample_range_response):
        """Test all valid value render options."""
        valid_options = ["ToString", "Formula", "FormattedValue", "UnformattedValue"]
        
        for option in valid_options:
            mock_api_client.read_range.return_value = sample_range_response
            
            result = await read_range(
                mock_api_client,
                "test_token",
                "sheet123!A1:C3",
                value_render_option=option
            )
            
            assert isinstance(result, RangeData)

    @pytest.mark.asyncio
    async def test_read_range_spreadsheet_not_found(self, mock_api_client):
        """Test handling of spreadsheet not found error."""
        mock_api_client.read_range.side_effect = FeishuAPIError(
            code=1310214,
            message="Spreadsheet not found",
            http_status=404
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await read_range(mock_api_client, "invalid_token", "sheet123!A1:B10")

        assert exc_info.value.code == 1310214
        assert "指定的电子表格不存在" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_read_range_sheet_not_found(self, mock_api_client):
        """Test handling of sheet not found error."""
        mock_api_client.read_range.side_effect = FeishuAPIError(
            code=1310215,
            message="Sheet not found",
            http_status=404
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await read_range(mock_api_client, "test_token", "invalid_sheet!A1:B10")

        assert exc_info.value.code == 1310215
        assert "指定的工作表不存在" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_read_range_permission_error(self, mock_api_client):
        """Test handling of permission errors."""
        mock_api_client.read_range.side_effect = FeishuAPIError(
            code=1310213,
            message="Permission denied",
            http_status=403
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await read_range(mock_api_client, "test_token", "sheet123!A1:B10")

        assert exc_info.value.code == 1310213
        assert "没有读取权限" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_read_range_format_error(self, mock_api_client):
        """Test handling of range format errors."""
        mock_api_client.read_range.side_effect = FeishuAPIError(
            code=1310216,
            message="Invalid range format",
            http_status=400
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await read_range(mock_api_client, "test_token", "sheet123!A1:B10")

        assert exc_info.value.code == 1310216
        assert "范围格式无效" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_read_range_data_size_limit(self, mock_api_client):
        """Test handling of data size limit errors."""
        mock_api_client.read_range.side_effect = FeishuAPIError(
            code=1310218,
            message="Data size limit exceeded",
            http_status=413
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await read_range(mock_api_client, "test_token", "sheet123!A1:Z1000")

        assert exc_info.value.code == 1310218
        assert "返回数据超过10MB限制" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_read_range_authentication_error(self, mock_api_client):
        """Test handling of authentication errors."""
        mock_api_client.read_range.side_effect = FeishuAPIError(
            code=99991663,
            message="Invalid access token",
            http_status=401
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await read_range(mock_api_client, "test_token", "sheet123!A1:B10")

        assert exc_info.value.code == 99991663
        assert "认证失败" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_read_range_api_error(self, mock_api_client):
        """Test handling of other API errors."""
        mock_api_client.read_range.side_effect = FeishuAPIError(
            code=1310217,
            message="Too many requests",
            http_status=429
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await read_range(mock_api_client, "test_token", "sheet123!A1:B10")

        assert exc_info.value.code == 1310217
        assert exc_info.value.message == "Too many requests"

    @pytest.mark.asyncio
    async def test_read_range_unexpected_error(self, mock_api_client):
        """Test handling of unexpected errors."""
        mock_api_client.read_range.side_effect = Exception("Unexpected error")

        with pytest.raises(FeishuAPIError) as exc_info:
            await read_range(mock_api_client, "test_token", "sheet123!A1:B10")

        assert exc_info.value.code == -1
        assert "读取范围数据时发生错误" in exc_info.value.message


class TestReadMultipleRangesFunction:
    """Test read_multiple_ranges function."""

    @pytest.fixture
    def mock_api_client(self):
        """Create mock API client."""
        return AsyncMock()

    @pytest.fixture
    def sample_multiple_ranges_response(self):
        """Sample API response with multiple range data."""
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "valueRanges": [
                    {
                        "range": "sheet123!A1:B2",
                        "majorDimension": "ROWS",
                        "values": [
                            ["Name", "Age"],
                            ["Alice", "25"]
                        ],
                        "revision": 12345
                    },
                    {
                        "range": "sheet123!C1:D2",
                        "majorDimension": "ROWS",
                        "values": [
                            ["City", "Country"],
                            ["New York", "USA"]
                        ],
                        "revision": 12345
                    }
                ]
            }
        }

    @pytest.fixture
    def sample_mixed_ranges_response(self):
        """Sample API response with mixed valid/empty ranges."""
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "valueRanges": [
                    {
                        "range": "sheet123!A1:B2",
                        "majorDimension": "ROWS",
                        "values": [
                            ["Name", "Age"],
                            ["Alice", "25"]
                        ],
                        "revision": 12345
                    },
                    {
                        "range": "sheet123!E1:F1",
                        "majorDimension": "ROWS",
                        "values": [],
                        "revision": 12345
                    }
                ]
            }
        }

    @pytest.mark.asyncio
    async def test_read_multiple_ranges_success(self, mock_api_client, sample_multiple_ranges_response):
        """Test successful multiple ranges reading."""
        mock_api_client.read_multiple_ranges.return_value = sample_multiple_ranges_response

        result = await read_multiple_ranges(
            mock_api_client,
            "test_spreadsheet_token",
            ["sheet123!A1:B2", "sheet123!C1:D2"]
        )

        assert len(result) == 2
        assert all(isinstance(item, RangeData) for item in result)
        
        # Check first range
        assert result[0].range == "sheet123!A1:B2"
        assert result[0].values == [["Name", "Age"], ["Alice", "25"]]
        
        # Check second range
        assert result[1].range == "sheet123!C1:D2"
        assert result[1].values == [["City", "Country"], ["New York", "USA"]]

        # Verify API was called correctly
        mock_api_client.read_multiple_ranges.assert_called_once_with(
            spreadsheet_token="test_spreadsheet_token",
            ranges=["sheet123!A1:B2", "sheet123!C1:D2"],
            value_render_option="UnformattedValue",
            date_time_render_option="FormattedString"
        )

    @pytest.mark.asyncio
    async def test_read_multiple_ranges_with_options(self, mock_api_client, sample_multiple_ranges_response):
        """Test multiple ranges reading with custom options."""
        mock_api_client.read_multiple_ranges.return_value = sample_multiple_ranges_response

        result = await read_multiple_ranges(
            mock_api_client,
            "test_spreadsheet_token",
            ["sheet123!A1:B2", "sheet123!C1:D2"],
            value_render_option="FormattedValue",
            date_time_render_option="FormattedString"
        )

        assert len(result) == 2
        mock_api_client.read_multiple_ranges.assert_called_once_with(
            spreadsheet_token="test_spreadsheet_token",
            ranges=["sheet123!A1:B2", "sheet123!C1:D2"],
            value_render_option="FormattedValue",
            date_time_render_option="FormattedString"
        )

    @pytest.mark.asyncio
    async def test_read_multiple_ranges_mixed_results(self, mock_api_client, sample_mixed_ranges_response):
        """Test handling of mixed valid/empty ranges."""
        mock_api_client.read_multiple_ranges.return_value = sample_mixed_ranges_response

        result = await read_multiple_ranges(
            mock_api_client,
            "test_spreadsheet_token",
            ["sheet123!A1:B2", "sheet123!E1:F1"]
        )

        assert len(result) == 2
        assert result[0].values == [["Name", "Age"], ["Alice", "25"]]
        assert result[1].values == []
        assert result[1].is_empty()

    @pytest.mark.asyncio
    async def test_read_multiple_ranges_single_range(self, mock_api_client):
        """Test reading single range using multiple ranges function."""
        mock_api_client.read_multiple_ranges.return_value = {
            "code": 0,
            "msg": "success",
            "data": {
                "valueRanges": [
                    {
                        "range": "sheet123!A1:B2",
                        "majorDimension": "ROWS",
                        "values": [["Name", "Age"], ["Alice", "25"]],
                        "revision": 12345
                    }
                ]
            }
        }

        result = await read_multiple_ranges(
            mock_api_client,
            "test_spreadsheet_token",
            ["sheet123!A1:B2"]
        )

        assert len(result) == 1
        assert result[0].range == "sheet123!A1:B2"

    @pytest.mark.asyncio
    async def test_read_multiple_ranges_invalid_spreadsheet_token(self, mock_api_client):
        """Test validation of spreadsheet_token parameter."""
        with pytest.raises(ValueError, match="spreadsheet_token must be a non-empty string"):
            await read_multiple_ranges(mock_api_client, "", ["sheet123!A1:B10"])

        with pytest.raises(ValueError, match="spreadsheet_token cannot be empty or whitespace only"):
            await read_multiple_ranges(mock_api_client, "   ", ["sheet123!A1:B10"])

        with pytest.raises(ValueError, match="spreadsheet_token must be a non-empty string"):
            await read_multiple_ranges(mock_api_client, None, ["sheet123!A1:B10"])

        with pytest.raises(ValueError, match="spreadsheet_token must be a non-empty string"):
            await read_multiple_ranges(mock_api_client, 123, ["sheet123!A1:B10"])

    @pytest.mark.asyncio
    async def test_read_multiple_ranges_invalid_ranges_parameter(self, mock_api_client):
        """Test validation of ranges parameter."""
        with pytest.raises(ValueError, match="ranges must be a list"):
            await read_multiple_ranges(mock_api_client, "test_token", "not_a_list")

        with pytest.raises(ValueError, match="ranges cannot be empty"):
            await read_multiple_ranges(mock_api_client, "test_token", [])

        # Test too many ranges
        too_many_ranges = [f"sheet123!A{i}:B{i}" for i in range(1, 102)]
        with pytest.raises(ValueError, match="ranges cannot contain more than 100 items"):
            await read_multiple_ranges(mock_api_client, "test_token", too_many_ranges)

    @pytest.mark.asyncio
    async def test_read_multiple_ranges_invalid_range_specs(self, mock_api_client):
        """Test validation of individual range specifications."""
        with pytest.raises(ValueError, match="Invalid range at index 0"):
            await read_multiple_ranges(mock_api_client, "test_token", ["invalid_range"])

        with pytest.raises(ValueError, match="Invalid range at index 1"):
            await read_multiple_ranges(mock_api_client, "test_token", ["sheet123!A1:B10", "!A1:B10"])

    @pytest.mark.asyncio
    async def test_read_multiple_ranges_invalid_value_render_option(self, mock_api_client):
        """Test validation of value_render_option parameter."""
        with pytest.raises(ValueError, match="value_render_option must be one of"):
            await read_multiple_ranges(
                mock_api_client,
                "test_token",
                ["sheet123!A1:B10"],
                value_render_option="InvalidOption"
            )

    @pytest.mark.asyncio
    async def test_read_multiple_ranges_invalid_date_time_render_option(self, mock_api_client):
        """Test validation of date_time_render_option parameter."""
        with pytest.raises(ValueError, match="date_time_render_option must be one of"):
            await read_multiple_ranges(
                mock_api_client,
                "test_token",
                ["sheet123!A1:B10"],
                date_time_render_option="InvalidOption"
            )

    @pytest.mark.asyncio
    async def test_read_multiple_ranges_all_value_render_options(self, mock_api_client, sample_multiple_ranges_response):
        """Test all valid value render options."""
        valid_options = ["ToString", "Formula", "FormattedValue", "UnformattedValue"]
        
        for option in valid_options:
            mock_api_client.read_multiple_ranges.return_value = sample_multiple_ranges_response
            
            result = await read_multiple_ranges(
                mock_api_client,
                "test_token",
                ["sheet123!A1:B2", "sheet123!C1:D2"],
                value_render_option=option
            )
            
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_read_multiple_ranges_spreadsheet_not_found(self, mock_api_client):
        """Test handling of spreadsheet not found error."""
        mock_api_client.read_multiple_ranges.side_effect = FeishuAPIError(
            code=1310214,
            message="Spreadsheet not found",
            http_status=404
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await read_multiple_ranges(mock_api_client, "invalid_token", ["sheet123!A1:B10"])

        assert exc_info.value.code == 1310214
        assert "指定的电子表格不存在" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_read_multiple_ranges_sheet_not_found(self, mock_api_client):
        """Test handling of sheet not found error."""
        mock_api_client.read_multiple_ranges.side_effect = FeishuAPIError(
            code=1310215,
            message="Sheet not found",
            http_status=404
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await read_multiple_ranges(mock_api_client, "test_token", ["invalid_sheet!A1:B10"])

        assert exc_info.value.code == 1310215
        assert "指定的工作表不存在" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_read_multiple_ranges_permission_error(self, mock_api_client):
        """Test handling of permission errors."""
        mock_api_client.read_multiple_ranges.side_effect = FeishuAPIError(
            code=1310213,
            message="Permission denied",
            http_status=403
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await read_multiple_ranges(mock_api_client, "test_token", ["sheet123!A1:B10"])

        assert exc_info.value.code == 1310213
        assert "没有读取权限" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_read_multiple_ranges_format_error(self, mock_api_client):
        """Test handling of range format errors."""
        mock_api_client.read_multiple_ranges.side_effect = FeishuAPIError(
            code=1310216,
            message="Invalid range format",
            http_status=400
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await read_multiple_ranges(mock_api_client, "test_token", ["sheet123!A1:B10"])

        assert exc_info.value.code == 1310216
        assert "范围格式无效" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_read_multiple_ranges_data_size_limit(self, mock_api_client):
        """Test handling of data size limit errors."""
        mock_api_client.read_multiple_ranges.side_effect = FeishuAPIError(
            code=1310218,
            message="Data size limit exceeded",
            http_status=413
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await read_multiple_ranges(mock_api_client, "test_token", ["sheet123!A1:Z1000"])

        assert exc_info.value.code == 1310218
        assert "返回数据超过10MB限制" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_read_multiple_ranges_authentication_error(self, mock_api_client):
        """Test handling of authentication errors."""
        mock_api_client.read_multiple_ranges.side_effect = FeishuAPIError(
            code=99991663,
            message="Invalid access token",
            http_status=401
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await read_multiple_ranges(mock_api_client, "test_token", ["sheet123!A1:B10"])

        assert exc_info.value.code == 99991663
        assert "认证失败" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_read_multiple_ranges_api_error(self, mock_api_client):
        """Test handling of other API errors."""
        mock_api_client.read_multiple_ranges.side_effect = FeishuAPIError(
            code=1310217,
            message="Too many requests",
            http_status=429
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await read_multiple_ranges(mock_api_client, "test_token", ["sheet123!A1:B10"])

        assert exc_info.value.code == 1310217
        assert exc_info.value.message == "Too many requests"

    @pytest.mark.asyncio
    async def test_read_multiple_ranges_unexpected_error(self, mock_api_client):
        """Test handling of unexpected errors."""
        mock_api_client.read_multiple_ranges.side_effect = Exception("Unexpected error")

        with pytest.raises(FeishuAPIError) as exc_info:
            await read_multiple_ranges(mock_api_client, "test_token", ["sheet123!A1:B10"])

        assert exc_info.value.code == -1
        assert "批量读取范围数据时发生错误" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_read_multiple_ranges_invalid_data_skipped(self, mock_api_client, caplog):
        """Test that invalid range data is skipped with warning."""
        mock_api_client.read_multiple_ranges.return_value = {
            "code": 0,
            "msg": "success",
            "data": {
                "valueRanges": [
                    {
                        "range": "sheet123!A1:B2",
                        "majorDimension": "ROWS",
                        "values": [["Name", "Age"], ["Alice", "25"]],
                        "revision": 12345
                    },
                    {
                        # Missing required fields
                        "range": "sheet123!C1:D2"
                    }
                ]
            }
        }

        result = await read_multiple_ranges(
            mock_api_client,
            "test_token",
            ["sheet123!A1:B2", "sheet123!C1:D2"]
        )

        # Should return results for both ranges (invalid one as empty placeholder)
        assert len(result) == 2
        assert result[0].values == [["Name", "Age"], ["Alice", "25"]]
        assert result[1].values == []  # Placeholder for invalid data

        # Should log warning for invalid data
        assert "Skipping invalid range data at index 1" in caplog.text


class TestFindCellsFunction:
    """Test find_cells function."""

    @pytest.fixture
    def mock_api_client(self):
        """Create mock API client."""
        return AsyncMock()

    @pytest.fixture
    def sample_find_response(self):
        """Sample API response with find results."""
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "find_result": {
                    "matched_cells": ["A1", "B2", "C3"],
                    "matched_formula_cells": ["D4"],
                    "rows_count": 4
                }
            }
        }

    @pytest.fixture
    def sample_empty_find_response(self):
        """Sample API response with no matches."""
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "find_result": {
                    "matched_cells": [],
                    "matched_formula_cells": [],
                    "rows_count": 0
                }
            }
        }

    @pytest.mark.asyncio
    async def test_find_cells_success(self, mock_api_client, sample_find_response):
        """Test successful cell finding."""
        mock_api_client.find_cells.return_value = sample_find_response

        result = await find_cells(
            mock_api_client,
            "test_spreadsheet_token",
            "sheet123",
            "A1:Z100",
            "search_text"
        )

        assert isinstance(result, FindResult)
        assert result.matched_cells == ["A1", "B2", "C3"]
        assert result.matched_formula_cells == ["D4"]
        assert result.rows_count == 4
        assert result.has_matches()
        assert result.total_matches() == 4

        # Verify API was called correctly
        mock_api_client.find_cells.assert_called_once_with(
            spreadsheet_token="test_spreadsheet_token",
            sheet_id="sheet123",
            range_spec="A1:Z100",
            find_text="search_text",
            match_case=False,
            match_entire_cell=False,
            search_by_regex=False,
            include_formulas=False
        )

    @pytest.mark.asyncio
    async def test_find_cells_with_all_options(self, mock_api_client, sample_find_response):
        """Test cell finding with all options enabled."""
        mock_api_client.find_cells.return_value = sample_find_response

        result = await find_cells(
            mock_api_client,
            "test_spreadsheet_token",
            "sheet123",
            "A1:Z100",
            "search.*pattern",
            match_case=True,
            match_entire_cell=True,
            search_by_regex=True,
            include_formulas=True
        )

        assert isinstance(result, FindResult)
        mock_api_client.find_cells.assert_called_once_with(
            spreadsheet_token="test_spreadsheet_token",
            sheet_id="sheet123",
            range_spec="A1:Z100",
            find_text="search.*pattern",
            match_case=True,
            match_entire_cell=True,
            search_by_regex=True,
            include_formulas=True
        )

    @pytest.mark.asyncio
    async def test_find_cells_no_matches(self, mock_api_client, sample_empty_find_response):
        """Test handling of no matches found."""
        mock_api_client.find_cells.return_value = sample_empty_find_response

        result = await find_cells(
            mock_api_client,
            "test_spreadsheet_token",
            "sheet123",
            "A1:Z100",
            "nonexistent_text"
        )

        assert isinstance(result, FindResult)
        assert result.matched_cells == []
        assert result.matched_formula_cells == []
        assert result.rows_count == 0
        assert not result.has_matches()
        assert result.total_matches() == 0

    @pytest.mark.asyncio
    async def test_find_cells_invalid_spreadsheet_token(self, mock_api_client):
        """Test validation of spreadsheet_token parameter."""
        with pytest.raises(ValueError, match="spreadsheet_token must be a non-empty string"):
            await find_cells(mock_api_client, "", "sheet123", "A1:Z100", "text")

        with pytest.raises(ValueError, match="spreadsheet_token cannot be empty or whitespace only"):
            await find_cells(mock_api_client, "   ", "sheet123", "A1:Z100", "text")

        with pytest.raises(ValueError, match="spreadsheet_token must be a non-empty string"):
            await find_cells(mock_api_client, None, "sheet123", "A1:Z100", "text")

        with pytest.raises(ValueError, match="spreadsheet_token must be a non-empty string"):
            await find_cells(mock_api_client, 123, "sheet123", "A1:Z100", "text")

    @pytest.mark.asyncio
    async def test_find_cells_invalid_sheet_id(self, mock_api_client):
        """Test validation of sheet_id parameter."""
        with pytest.raises(ValueError, match="sheet_id must be a non-empty string"):
            await find_cells(mock_api_client, "test_token", "", "A1:Z100", "text")

        with pytest.raises(ValueError, match="sheet_id cannot be empty or whitespace only"):
            await find_cells(mock_api_client, "test_token", "   ", "A1:Z100", "text")

        with pytest.raises(ValueError, match="sheet_id must be a non-empty string"):
            await find_cells(mock_api_client, "test_token", None, "A1:Z100", "text")

        with pytest.raises(ValueError, match="sheet_id must be a non-empty string"):
            await find_cells(mock_api_client, "test_token", 123, "A1:Z100", "text")

    @pytest.mark.asyncio
    async def test_find_cells_invalid_range_spec(self, mock_api_client):
        """Test validation of range_spec parameter."""
        with pytest.raises(ValueError, match="range_spec must be a non-empty string"):
            await find_cells(mock_api_client, "test_token", "sheet123", "", "text")

        with pytest.raises(ValueError, match="range_spec cannot be empty or whitespace only"):
            await find_cells(mock_api_client, "test_token", "sheet123", "   ", "text")

        with pytest.raises(ValueError, match="range_spec must be a non-empty string"):
            await find_cells(mock_api_client, "test_token", "sheet123", None, "text")

        with pytest.raises(ValueError, match="range_spec must be a non-empty string"):
            await find_cells(mock_api_client, "test_token", "sheet123", 123, "text")

    @pytest.mark.asyncio
    async def test_find_cells_invalid_find_text(self, mock_api_client):
        """Test validation of find_text parameter."""
        with pytest.raises(ValueError, match="find_text must be a non-empty string"):
            await find_cells(mock_api_client, "test_token", "sheet123", "A1:Z100", "")

        with pytest.raises(ValueError, match="find_text cannot be empty or whitespace only"):
            await find_cells(mock_api_client, "test_token", "sheet123", "A1:Z100", "   ")

        with pytest.raises(ValueError, match="find_text must be a non-empty string"):
            await find_cells(mock_api_client, "test_token", "sheet123", "A1:Z100", None)

        with pytest.raises(ValueError, match="find_text must be a non-empty string"):
            await find_cells(mock_api_client, "test_token", "sheet123", "A1:Z100", 123)

    @pytest.mark.asyncio
    async def test_find_cells_invalid_boolean_parameters(self, mock_api_client):
        """Test validation of boolean parameters."""
        with pytest.raises(ValueError, match="match_case must be a boolean"):
            await find_cells(mock_api_client, "test_token", "sheet123", "A1:Z100", "text", match_case="true")

        with pytest.raises(ValueError, match="match_entire_cell must be a boolean"):
            await find_cells(mock_api_client, "test_token", "sheet123", "A1:Z100", "text", match_entire_cell="false")

        with pytest.raises(ValueError, match="search_by_regex must be a boolean"):
            await find_cells(mock_api_client, "test_token", "sheet123", "A1:Z100", "text", search_by_regex=1)

        with pytest.raises(ValueError, match="include_formulas must be a boolean"):
            await find_cells(mock_api_client, "test_token", "sheet123", "A1:Z100", "text", include_formulas=0)

    @pytest.mark.asyncio
    async def test_find_cells_invalid_regex_pattern(self, mock_api_client):
        """Test validation of regex pattern."""
        with pytest.raises(ValueError, match="Invalid regular expression"):
            await find_cells(
                mock_api_client,
                "test_token",
                "sheet123",
                "A1:Z100",
                "[invalid_regex",
                search_by_regex=True
            )

    @pytest.mark.asyncio
    async def test_find_cells_valid_regex_pattern(self, mock_api_client, sample_find_response):
        """Test valid regex patterns."""
        mock_api_client.find_cells.return_value = sample_find_response

        valid_patterns = [
            r"\d+",
            r"[A-Za-z]+",
            r"test.*pattern",
            r"^start",
            r"end$",
            r"(group1|group2)"
        ]

        for pattern in valid_patterns:
            result = await find_cells(
                mock_api_client,
                "test_token",
                "sheet123",
                "A1:Z100",
                pattern,
                search_by_regex=True
            )
            assert isinstance(result, FindResult)

    @pytest.mark.asyncio
    async def test_find_cells_spreadsheet_not_found(self, mock_api_client):
        """Test handling of spreadsheet not found error."""
        mock_api_client.find_cells.side_effect = FeishuAPIError(
            code=1310214,
            message="Spreadsheet not found",
            http_status=404
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await find_cells(mock_api_client, "invalid_token", "sheet123", "A1:Z100", "text")

        assert exc_info.value.code == 1310214
        assert "指定的电子表格不存在" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_find_cells_sheet_not_found(self, mock_api_client):
        """Test handling of sheet not found error."""
        mock_api_client.find_cells.side_effect = FeishuAPIError(
            code=1310215,
            message="Sheet not found",
            http_status=404
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await find_cells(mock_api_client, "test_token", "invalid_sheet", "A1:Z100", "text")

        assert exc_info.value.code == 1310215
        assert "指定的工作表不存在" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_find_cells_permission_error(self, mock_api_client):
        """Test handling of permission errors."""
        mock_api_client.find_cells.side_effect = FeishuAPIError(
            code=1310213,
            message="Permission denied",
            http_status=403
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await find_cells(mock_api_client, "test_token", "sheet123", "A1:Z100", "text")

        assert exc_info.value.code == 1310213
        assert "没有读取权限" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_find_cells_range_format_error(self, mock_api_client):
        """Test handling of range format errors."""
        mock_api_client.find_cells.side_effect = FeishuAPIError(
            code=1310216,
            message="Invalid range format",
            http_status=400
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await find_cells(mock_api_client, "test_token", "sheet123", "invalid_range", "text")

        assert exc_info.value.code == 1310216
        assert "范围格式无效" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_find_cells_invalid_regex_api_error(self, mock_api_client):
        """Test handling of invalid regex API error from server."""
        mock_api_client.find_cells.side_effect = FeishuAPIError(
            code=1310219,
            message="Invalid regex pattern",
            http_status=400
        )

        # Use a valid regex pattern that passes client validation but fails on server
        with pytest.raises(FeishuAPIError) as exc_info:
            await find_cells(mock_api_client, "test_token", "sheet123", "A1:Z100", r"\d+", search_by_regex=True)

        assert exc_info.value.code == 1310219
        assert "正则表达式格式无效" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_find_cells_authentication_error(self, mock_api_client):
        """Test handling of authentication errors."""
        mock_api_client.find_cells.side_effect = FeishuAPIError(
            code=99991663,
            message="Invalid access token",
            http_status=401
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await find_cells(mock_api_client, "test_token", "sheet123", "A1:Z100", "text")

        assert exc_info.value.code == 99991663
        assert "认证失败" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_find_cells_api_error(self, mock_api_client):
        """Test handling of other API errors."""
        mock_api_client.find_cells.side_effect = FeishuAPIError(
            code=1310217,
            message="Too many requests",
            http_status=429
        )

        with pytest.raises(FeishuAPIError) as exc_info:
            await find_cells(mock_api_client, "test_token", "sheet123", "A1:Z100", "text")

        assert exc_info.value.code == 1310217
        assert exc_info.value.message == "Too many requests"

    @pytest.mark.asyncio
    async def test_find_cells_unexpected_error(self, mock_api_client):
        """Test handling of unexpected errors."""
        mock_api_client.find_cells.side_effect = Exception("Unexpected error")

        with pytest.raises(FeishuAPIError) as exc_info:
            await find_cells(mock_api_client, "test_token", "sheet123", "A1:Z100", "text")

        assert exc_info.value.code == -1
        assert "查找单元格时发生错误" in exc_info.value.message


class TestSpreadsheetToolsOther:
    """Test other spreadsheet tool functions."""

    def test_get_worksheets_function_exists(self):
        """Test that get_worksheets function exists."""
        assert callable(get_worksheets)

    def test_read_range_function_exists(self):
        """Test that read_range function exists."""
        assert callable(read_range)

    def test_read_multiple_ranges_function_exists(self):
        """Test that read_multiple_ranges function exists."""
        assert callable(read_multiple_ranges)

    def test_find_cells_function_exists(self):
        """Test that find_cells function exists."""
        assert callable(find_cells)

    @pytest.mark.asyncio
    async def test_get_worksheets_signature(self):
        """Test get_worksheets function signature."""
        # Should require api_client and spreadsheet_token parameters
        mock_api_client = AsyncMock()
        mock_api_client.get_worksheets.return_value = {
            "code": 0,
            "msg": "success", 
            "data": {"sheets": []}
        }
        result = await get_worksheets(mock_api_client, "test_spreadsheet_token")
        assert result == []  # Empty list for empty response

    @pytest.mark.asyncio
    async def test_read_range_signature(self):
        """Test read_range function signature."""
        # Should require api_client, spreadsheet_token and range_spec
        mock_api_client = AsyncMock()
        mock_api_client.read_range.return_value = {
            "code": 0,
            "msg": "success",
            "data": {
                "valueRange": {
                    "range": "Sheet1!A1:B10",
                    "majorDimension": "ROWS",
                    "values": [],
                    "revision": 1
                }
            }
        }
        result = await read_range(mock_api_client, "test_spreadsheet_token", "Sheet1!A1:B10")
        assert isinstance(result, RangeData)

        # Should accept optional parameters
        result = await read_range(
            mock_api_client,
            "test_spreadsheet_token",
            "Sheet1!A1:B10",
            value_render_option="FormattedValue",
            date_time_render_option="FormattedString",
        )
        assert isinstance(result, RangeData)

    @pytest.mark.asyncio
    async def test_read_multiple_ranges_signature(self):
        """Test read_multiple_ranges function signature."""
        # Should require api_client, spreadsheet_token and ranges
        mock_api_client = AsyncMock()
        
        # First call with two ranges
        mock_api_client.read_multiple_ranges.return_value = {
            "code": 0,
            "msg": "success",
            "data": {
                "valueRanges": [
                    {
                        "range": "Sheet1!A1:B10",
                        "majorDimension": "ROWS",
                        "values": [],
                        "revision": 1
                    },
                    {
                        "range": "Sheet1!C1:D10",
                        "majorDimension": "ROWS",
                        "values": [],
                        "revision": 1
                    }
                ]
            }
        }
        result = await read_multiple_ranges(
            mock_api_client, "test_spreadsheet_token", ["Sheet1!A1:B10", "Sheet1!C1:D10"]
        )
        assert len(result) == 2
        assert all(isinstance(item, RangeData) for item in result)

        # Second call with one range
        mock_api_client.read_multiple_ranges.return_value = {
            "code": 0,
            "msg": "success",
            "data": {
                "valueRanges": [
                    {
                        "range": "Sheet1!A1:B10",
                        "majorDimension": "ROWS",
                        "values": [],
                        "revision": 1
                    }
                ]
            }
        }
        result = await read_multiple_ranges(
            mock_api_client,
            "test_spreadsheet_token",
            ["Sheet1!A1:B10"],
            value_render_option="FormattedValue",
            date_time_render_option="FormattedString",
        )
        assert len(result) == 1
        assert isinstance(result[0], RangeData)

    @pytest.mark.asyncio
    async def test_find_cells_signature(self):
        """Test find_cells function signature."""
        # Should require api_client and basic parameters
        mock_api_client = AsyncMock()
        mock_api_client.find_cells.return_value = {
            "code": 0,
            "msg": "success",
            "data": {
                "find_result": {
                    "matched_cells": [],
                    "matched_formula_cells": [],
                    "rows_count": 0
                }
            }
        }
        result = await find_cells(
            mock_api_client, "test_spreadsheet_token", "sheet123", "A1:Z100", "search_text"
        )
        assert isinstance(result, FindResult)

        # Should accept all optional parameters
        result = await find_cells(
            mock_api_client,
            "test_spreadsheet_token",
            "sheet123",
            "A1:Z100",
            "search_text",
            match_case=True,
            match_entire_cell=True,
            search_by_regex=True,
            include_formulas=True,
        )
        assert isinstance(result, FindResult)
