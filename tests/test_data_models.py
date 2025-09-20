"""
Tests for data models.
"""

import pytest
from datetime import datetime

from src.models import (
    FeishuAPIError,
    FindResult,
    MCPToolResult,
    RangeData,
    SpreadsheetInfo,
    WorksheetInfo,
    validate_token,
    validate_url,
    validate_range_spec,
    validate_positive_int,
    validate_non_negative_int,
)


class TestValidationFunctions:
    """Test validation functions."""

    def test_validate_token_valid(self):
        """Test validate_token with valid input."""
        assert validate_token("test_token") == "test_token"
        assert validate_token("  test_token  ") == "test_token"

    def test_validate_token_invalid(self):
        """Test validate_token with invalid input."""
        with pytest.raises(ValueError, match="Token must be a non-empty string"):
            validate_token("")

        with pytest.raises(ValueError, match="Token must be a non-empty string"):
            validate_token(None)

        with pytest.raises(
            ValueError, match="Token cannot be empty or whitespace only"
        ):
            validate_token("   ")

    def test_validate_url_valid(self):
        """Test validate_url with valid input."""
        assert validate_url("https://example.com") == "https://example.com"
        assert validate_url("http://example.com") == "http://example.com"
        assert validate_url("  https://example.com  ") == "https://example.com"

    def test_validate_url_invalid(self):
        """Test validate_url with invalid input."""
        with pytest.raises(ValueError, match="URL must be a non-empty string"):
            validate_url("")

        with pytest.raises(ValueError, match="URL must be a non-empty string"):
            validate_url(None)

        with pytest.raises(ValueError, match="URL must start with http:// or https://"):
            validate_url("ftp://example.com")

    def test_validate_range_spec_valid(self):
        """Test validate_range_spec with valid input."""
        assert validate_range_spec("Sheet1!A1:B10") == "Sheet1!A1:B10"
        assert validate_range_spec("Sheet1!A1") == "Sheet1!A1"
        assert validate_range_spec("  Sheet1!A1:B10  ") == "Sheet1!A1:B10"

    def test_validate_range_spec_invalid(self):
        """Test validate_range_spec with invalid input."""
        with pytest.raises(
            ValueError, match="Range specification must be a non-empty string"
        ):
            validate_range_spec("")

        with pytest.raises(
            ValueError, match="Range specification must include sheet ID"
        ):
            validate_range_spec("A1:B10")

        with pytest.raises(ValueError, match="Sheet ID cannot be empty"):
            validate_range_spec("!A1:B10")

        with pytest.raises(ValueError, match="Range part cannot be empty"):
            validate_range_spec("Sheet1!")

        with pytest.raises(ValueError, match="Invalid range format"):
            validate_range_spec("Sheet1!invalid")

    def test_validate_positive_int_valid(self):
        """Test validate_positive_int with valid input."""
        assert validate_positive_int(1, "test") == 1
        assert validate_positive_int(100, "test") == 100

    def test_validate_positive_int_invalid(self):
        """Test validate_positive_int with invalid input."""
        with pytest.raises(ValueError, match="test must be an integer"):
            validate_positive_int("1", "test")

        with pytest.raises(ValueError, match="test must be non-negative"):
            validate_positive_int(-1, "test")

    def test_validate_non_negative_int_valid(self):
        """Test validate_non_negative_int with valid input."""
        assert validate_non_negative_int(0, "test") == 0
        assert validate_non_negative_int(100, "test") == 100

    def test_validate_non_negative_int_invalid(self):
        """Test validate_non_negative_int with invalid input."""
        with pytest.raises(ValueError, match="test must be an integer"):
            validate_non_negative_int("0", "test")

        with pytest.raises(ValueError, match="test must be non-negative"):
            validate_non_negative_int(-1, "test")


class TestSpreadsheetInfo:
    """Test SpreadsheetInfo data model."""

    def test_spreadsheet_info_creation(self):
        """Test creating SpreadsheetInfo instance."""
        created_time = datetime.now()
        modified_time = datetime.now()

        info = SpreadsheetInfo(
            token="test_token",
            name="Test Spreadsheet",
            type="sheet",
            url="https://example.com/sheet",
            created_time=created_time,
            modified_time=modified_time,
            owner_id="user123",
        )

        assert info.token == "test_token"
        assert info.name == "Test Spreadsheet"
        assert info.type == "sheet"
        assert info.url == "https://example.com/sheet"
        assert info.created_time == created_time
        assert info.modified_time == modified_time
        assert info.owner_id == "user123"

    def test_spreadsheet_info_equality(self):
        """Test SpreadsheetInfo equality comparison."""
        created_time = datetime.now()
        modified_time = datetime.now()

        info1 = SpreadsheetInfo(
            token="test_token",
            name="Test Spreadsheet",
            type="sheet",
            url="https://example.com/sheet",
            created_time=created_time,
            modified_time=modified_time,
            owner_id="user123",
        )

        info2 = SpreadsheetInfo(
            token="test_token",
            name="Test Spreadsheet",
            type="sheet",
            url="https://example.com/sheet",
            created_time=created_time,
            modified_time=modified_time,
            owner_id="user123",
        )

        assert info1 == info2

    def test_spreadsheet_info_validation_invalid_token(self):
        """Test SpreadsheetInfo validation with invalid token."""
        with pytest.raises(ValueError, match="Token must be a non-empty string"):
            SpreadsheetInfo(
                token="",
                name="Test",
                type="sheet",
                url="https://example.com",
                created_time=datetime.now(),
                modified_time=datetime.now(),
                owner_id="user123",
            )

    def test_spreadsheet_info_validation_invalid_type(self):
        """Test SpreadsheetInfo validation with invalid type."""
        with pytest.raises(ValueError, match="Type must be 'sheet'"):
            SpreadsheetInfo(
                token="test_token",
                name="Test",
                type="document",
                url="https://example.com",
                created_time=datetime.now(),
                modified_time=datetime.now(),
                owner_id="user123",
            )

    def test_spreadsheet_info_validation_invalid_url(self):
        """Test SpreadsheetInfo validation with invalid URL."""
        with pytest.raises(ValueError, match="URL must start with http:// or https://"):
            SpreadsheetInfo(
                token="test_token",
                name="Test",
                type="sheet",
                url="ftp://example.com",
                created_time=datetime.now(),
                modified_time=datetime.now(),
                owner_id="user123",
            )

    def test_spreadsheet_info_from_api_response(self):
        """Test creating SpreadsheetInfo from API response."""
        api_data = {
            "token": "test_token",
            "name": "Test Spreadsheet",
            "type": "sheet",
            "url": "https://example.com/sheet",
            "created_time": "2023-01-01T00:00:00Z",
            "modified_time": "2023-01-02T00:00:00Z",
            "owner_id": "user123",
        }

        info = SpreadsheetInfo.from_api_response(api_data)

        assert info.token == "test_token"
        assert info.name == "Test Spreadsheet"
        assert info.type == "sheet"
        assert info.url == "https://example.com/sheet"
        assert info.owner_id == "user123"

    def test_spreadsheet_info_from_api_response_missing_field(self):
        """Test creating SpreadsheetInfo from API response with missing field."""
        api_data = {
            "token": "test_token",
            "name": "Test Spreadsheet",
            "type": "sheet",
            # missing url
            "created_time": "2023-01-01T00:00:00Z",
            "modified_time": "2023-01-02T00:00:00Z",
            "owner_id": "user123",
        }

        with pytest.raises(ValueError, match="Missing required field in API response"):
            SpreadsheetInfo.from_api_response(api_data)


class TestWorksheetInfo:
    """Test WorksheetInfo data model."""

    def test_worksheet_info_creation(self):
        """Test creating WorksheetInfo instance."""
        info = WorksheetInfo(
            sheet_id="sheet123",
            title="Sheet1",
            index=0,
            hidden=False,
            row_count=100,
            column_count=26,
            frozen_row_count=1,
            frozen_column_count=0,
            resource_type="sheet",
        )

        assert info.sheet_id == "sheet123"
        assert info.title == "Sheet1"
        assert info.index == 0
        assert info.hidden is False
        assert info.row_count == 100
        assert info.column_count == 26
        assert info.frozen_row_count == 1
        assert info.frozen_column_count == 0
        assert info.resource_type == "sheet"
        assert info.merges is None

    def test_worksheet_info_with_merges(self):
        """Test WorksheetInfo with merge information."""
        merges = [
            {
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 0,
                "endColumnIndex": 2,
            }
        ]

        info = WorksheetInfo(
            sheet_id="sheet123",
            title="Sheet1",
            index=0,
            hidden=False,
            row_count=100,
            column_count=26,
            frozen_row_count=1,
            frozen_column_count=0,
            resource_type="sheet",
            merges=merges,
        )

        assert info.merges == merges

    def test_worksheet_info_validation_invalid_sheet_id(self):
        """Test WorksheetInfo validation with invalid sheet_id."""
        with pytest.raises(ValueError, match="Token must be a non-empty string"):
            WorksheetInfo(
                sheet_id="",
                title="Sheet1",
                index=0,
                hidden=False,
                row_count=100,
                column_count=26,
                frozen_row_count=1,
                frozen_column_count=0,
                resource_type="sheet",
            )

    def test_worksheet_info_validation_invalid_counts(self):
        """Test WorksheetInfo validation with invalid counts."""
        with pytest.raises(ValueError, match="Row count must be non-negative"):
            WorksheetInfo(
                sheet_id="sheet123",
                title="Sheet1",
                index=0,
                hidden=False,
                row_count=-1,
                column_count=26,
                frozen_row_count=1,
                frozen_column_count=0,
                resource_type="sheet",
            )

    def test_worksheet_info_validation_invalid_merges(self):
        """Test WorksheetInfo validation with invalid merges."""
        with pytest.raises(ValueError, match="Merges must be a list or None"):
            WorksheetInfo(
                sheet_id="sheet123",
                title="Sheet1",
                index=0,
                hidden=False,
                row_count=100,
                column_count=26,
                frozen_row_count=1,
                frozen_column_count=0,
                resource_type="sheet",
                merges="invalid",
            )

    def test_worksheet_info_from_api_response(self):
        """Test creating WorksheetInfo from API response."""
        api_data = {
            "sheet_id": "sheet123",
            "title": "Sheet1",
            "index": 0,
            "hidden": False,
            "row_count": 100,
            "column_count": 26,
            "resource_type": "sheet",
        }

        info = WorksheetInfo.from_api_response(api_data)

        assert info.sheet_id == "sheet123"
        assert info.title == "Sheet1"
        assert info.index == 0
        assert info.hidden is False
        assert info.row_count == 100
        assert info.column_count == 26
        assert info.frozen_row_count == 0  # default value
        assert info.frozen_column_count == 0  # default value
        assert info.resource_type == "sheet"


class TestRangeData:
    """Test RangeData data model."""

    def test_range_data_creation(self):
        """Test creating RangeData instance."""
        values = [["A1", "B1"], ["A2", "B2"]]

        data = RangeData(
            range="Sheet1!A1:B2", major_dimension="ROWS", values=values, revision=1
        )

        assert data.range == "Sheet1!A1:B2"
        assert data.major_dimension == "ROWS"
        assert data.values == values
        assert data.revision == 1

    def test_range_data_empty_values(self):
        """Test RangeData with empty values."""
        data = RangeData(
            range="Sheet1!A1:A1", major_dimension="ROWS", values=[], revision=1
        )

        assert data.values == []

    def test_range_data_validation_invalid_range(self):
        """Test RangeData validation with invalid range."""
        with pytest.raises(
            ValueError, match="Range specification must include sheet ID"
        ):
            RangeData(
                range="A1:B2", major_dimension="ROWS", values=[["A1", "B1"]], revision=1
            )

    def test_range_data_validation_invalid_major_dimension(self):
        """Test RangeData validation with invalid major_dimension."""
        with pytest.raises(
            ValueError, match="Major dimension must be 'ROWS' or 'COLUMNS'"
        ):
            RangeData(
                range="Sheet1!A1:B2",
                major_dimension="INVALID",
                values=[["A1", "B1"]],
                revision=1,
            )

    def test_range_data_validation_invalid_values(self):
        """Test RangeData validation with invalid values."""
        with pytest.raises(ValueError, match="Values must be a list"):
            RangeData(
                range="Sheet1!A1:B2",
                major_dimension="ROWS",
                values="invalid",
                revision=1,
            )

    def test_range_data_get_cell_value(self):
        """Test RangeData get_cell_value method."""
        values = [["A1", "B1"], ["A2", "B2"]]
        data = RangeData(
            range="Sheet1!A1:B2", major_dimension="ROWS", values=values, revision=1
        )

        assert data.get_cell_value(0, 0) == "A1"
        assert data.get_cell_value(0, 1) == "B1"
        assert data.get_cell_value(1, 0) == "A2"
        assert data.get_cell_value(1, 1) == "B2"
        assert data.get_cell_value(2, 0) is None  # out of bounds
        assert data.get_cell_value(0, 2) is None  # out of bounds

    def test_range_data_get_cell_value_invalid_indices(self):
        """Test RangeData get_cell_value with invalid indices."""
        data = RangeData(
            range="Sheet1!A1:B2", major_dimension="ROWS", values=[["A1"]], revision=1
        )

        with pytest.raises(
            ValueError, match="Row and column indices must be non-negative"
        ):
            data.get_cell_value(-1, 0)

    def test_range_data_is_empty(self):
        """Test RangeData is_empty method."""
        empty_data = RangeData(
            range="Sheet1!A1:A1", major_dimension="ROWS", values=[], revision=1
        )
        assert empty_data.is_empty() is True

        non_empty_data = RangeData(
            range="Sheet1!A1:A1", major_dimension="ROWS", values=[["A1"]], revision=1
        )
        assert non_empty_data.is_empty() is False

    def test_range_data_from_api_response(self):
        """Test creating RangeData from API response."""
        api_data = {
            "range": "Sheet1!A1:B2",
            "majorDimension": "ROWS",
            "values": [["A1", "B1"], ["A2", "B2"]],
            "revision": 1,
        }

        data = RangeData.from_api_response(api_data)

        assert data.range == "Sheet1!A1:B2"
        assert data.major_dimension == "ROWS"
        assert data.values == [["A1", "B1"], ["A2", "B2"]]
        assert data.revision == 1


class TestFindResult:
    """Test FindResult data model."""

    def test_find_result_creation(self):
        """Test creating FindResult instance."""
        result = FindResult(
            matched_cells=["A1", "B2"], matched_formula_cells=["C3"], rows_count=10
        )

        assert result.matched_cells == ["A1", "B2"]
        assert result.matched_formula_cells == ["C3"]
        assert result.rows_count == 10

    def test_find_result_empty(self):
        """Test FindResult with no matches."""
        result = FindResult(matched_cells=[], matched_formula_cells=[], rows_count=0)

        assert result.matched_cells == []
        assert result.matched_formula_cells == []
        assert result.rows_count == 0

    def test_find_result_validation_invalid_matched_cells(self):
        """Test FindResult validation with invalid matched_cells."""
        with pytest.raises(ValueError, match="Matched cells must be a list"):
            FindResult(matched_cells="invalid", matched_formula_cells=[], rows_count=0)

    def test_find_result_validation_invalid_cell_type(self):
        """Test FindResult validation with invalid cell type."""
        with pytest.raises(ValueError, match="Each matched cell must be a string"):
            FindResult(matched_cells=[123], matched_formula_cells=[], rows_count=0)

    def test_find_result_has_matches(self):
        """Test FindResult has_matches method."""
        empty_result = FindResult(
            matched_cells=[], matched_formula_cells=[], rows_count=0
        )
        assert empty_result.has_matches() is False

        result_with_cells = FindResult(
            matched_cells=["A1"], matched_formula_cells=[], rows_count=1
        )
        assert result_with_cells.has_matches() is True

        result_with_formulas = FindResult(
            matched_cells=[], matched_formula_cells=["B1"], rows_count=1
        )
        assert result_with_formulas.has_matches() is True

    def test_find_result_total_matches(self):
        """Test FindResult total_matches method."""
        result = FindResult(
            matched_cells=["A1", "A2"], matched_formula_cells=["B1"], rows_count=3
        )
        assert result.total_matches() == 3

    def test_find_result_from_api_response(self):
        """Test creating FindResult from API response."""
        api_data = {
            "matched_cells": ["A1", "A2"],
            "matched_formula_cells": ["B1"],
            "rows_count": 3,
        }

        result = FindResult.from_api_response(api_data)

        assert result.matched_cells == ["A1", "A2"]
        assert result.matched_formula_cells == ["B1"]
        assert result.rows_count == 3


class TestMCPToolResult:
    """Test MCPToolResult data model."""

    def test_mcp_tool_result_success(self):
        """Test successful MCPToolResult."""
        content = [{"type": "text", "text": "Success"}]

        result = MCPToolResult(content=content)

        assert result.content == content
        assert result.is_error is False

    def test_mcp_tool_result_error(self):
        """Test error MCPToolResult."""
        content = [{"type": "text", "text": "Error occurred"}]

        result = MCPToolResult(content=content, is_error=True)

        assert result.content == content
        assert result.is_error is True

    def test_mcp_tool_result_validation_invalid_content(self):
        """Test MCPToolResult validation with invalid content."""
        with pytest.raises(ValueError, match="Content must be a list"):
            MCPToolResult(content="invalid")

    def test_mcp_tool_result_validation_invalid_content_item(self):
        """Test MCPToolResult validation with invalid content item."""
        with pytest.raises(ValueError, match="Each content item must be a dictionary"):
            MCPToolResult(content=["invalid"])

    def test_mcp_tool_result_validation_missing_type(self):
        """Test MCPToolResult validation with missing type field."""
        with pytest.raises(
            ValueError, match="Each content item must have a 'type' field"
        ):
            MCPToolResult(content=[{"text": "missing type"}])

    def test_mcp_tool_result_success_factory(self):
        """Test MCPToolResult success factory method."""
        result = MCPToolResult.success("test data", "Success message")

        assert result.is_error is False
        assert len(result.content) == 2
        assert result.content[0]["text"] == "Success message"
        assert result.content[1]["text"] == "test data"

    def test_mcp_tool_result_success_factory_no_message(self):
        """Test MCPToolResult success factory method without message."""
        result = MCPToolResult.success("test data")

        assert result.is_error is False
        assert len(result.content) == 1
        assert result.content[0]["text"] == "test data"

    def test_mcp_tool_result_error_factory(self):
        """Test MCPToolResult error factory method."""
        result = MCPToolResult.error("Something went wrong", 500)

        assert result.is_error is True
        assert len(result.content) == 1
        assert result.content[0]["text"] == "Error 500: Something went wrong"

    def test_mcp_tool_result_error_factory_no_code(self):
        """Test MCPToolResult error factory method without error code."""
        result = MCPToolResult.error("Something went wrong")

        assert result.is_error is True
        assert len(result.content) == 1
        assert result.content[0]["text"] == "Error: Something went wrong"


class TestFeishuAPIError:
    """Test FeishuAPIError data model."""

    def test_feishu_api_error_creation(self):
        """Test creating FeishuAPIError instance."""
        error = FeishuAPIError(
            code=1310214, message="Spreadsheet not found", http_status=404
        )

        assert error.code == 1310214
        assert error.message == "Spreadsheet not found"
        assert error.http_status == 404

    def test_to_mcp_error(self):
        """Test converting to MCP error format."""
        error = FeishuAPIError(
            code=1310214, message="Spreadsheet not found", http_status=404
        )

        mcp_error = error.to_mcp_error()

        expected = {
            "content": [
                {"type": "text", "text": "飞书API错误 1310214: Spreadsheet not found"}
            ],
            "isError": True,
        }

        assert mcp_error == expected

    def test_to_mcp_error_with_chinese_message(self):
        """Test converting Chinese error message to MCP format."""
        error = FeishuAPIError(code=1310213, message="权限不足", http_status=403)

        mcp_error = error.to_mcp_error()

        expected = {
            "content": [{"type": "text", "text": "飞书API错误 1310213: 权限不足"}],
            "isError": True,
        }

        assert mcp_error == expected

    def test_feishu_api_error_validation_invalid_code(self):
        """Test FeishuAPIError validation with invalid code."""
        with pytest.raises(ValueError, match="Error code must be an integer"):
            FeishuAPIError(code="invalid", message="Test error", http_status=400)

    def test_feishu_api_error_validation_invalid_message(self):
        """Test FeishuAPIError validation with invalid message."""
        with pytest.raises(
            ValueError, match="Error message must be a non-empty string"
        ):
            FeishuAPIError(code=1000, message="", http_status=400)

    def test_feishu_api_error_validation_invalid_http_status(self):
        """Test FeishuAPIError validation with invalid HTTP status."""
        with pytest.raises(ValueError, match="HTTP status must be between 100 and 599"):
            FeishuAPIError(code=1000, message="Test error", http_status=99)

    def test_feishu_api_error_from_api_response(self):
        """Test creating FeishuAPIError from API response."""
        response_data = {"code": 1310214, "msg": "Spreadsheet not found"}

        error = FeishuAPIError.from_api_response(response_data, 404)

        assert error.code == 1310214
        assert error.message == "Spreadsheet not found"
        assert error.http_status == 404

    def test_feishu_api_error_from_api_response_missing_field(self):
        """Test creating FeishuAPIError from API response with missing field."""
        response_data = {
            "code": 1310214
            # missing 'msg'
        }

        with pytest.raises(
            ValueError, match="Missing required field in error response"
        ):
            FeishuAPIError.from_api_response(response_data, 404)

    def test_feishu_api_error_is_retryable(self):
        """Test FeishuAPIError is_retryable method."""
        retryable_error = FeishuAPIError(
            code=1310217, message="Too many requests", http_status=429
        )
        assert retryable_error.is_retryable() is True

        non_retryable_error = FeishuAPIError(
            code=1310214, message="Not found", http_status=404
        )
        assert non_retryable_error.is_retryable() is False

    def test_feishu_api_error_is_authentication_error(self):
        """Test FeishuAPIError is_authentication_error method."""
        auth_error = FeishuAPIError(code=1000, message="Unauthorized", http_status=401)
        assert auth_error.is_authentication_error() is True

        non_auth_error = FeishuAPIError(
            code=1000, message="Bad request", http_status=400
        )
        assert non_auth_error.is_authentication_error() is False

    def test_feishu_api_error_is_permission_error(self):
        """Test FeishuAPIError is_permission_error method."""
        permission_error = FeishuAPIError(
            code=1310213, message="Permission denied", http_status=403
        )
        assert permission_error.is_permission_error() is True

        non_permission_error = FeishuAPIError(
            code=1000, message="Bad request", http_status=400
        )
        assert non_permission_error.is_permission_error() is False

    def test_feishu_api_error_is_not_found_error(self):
        """Test FeishuAPIError is_not_found_error method."""
        not_found_error = FeishuAPIError(
            code=1310214, message="Not found", http_status=404
        )
        assert not_found_error.is_not_found_error() is True

        other_error = FeishuAPIError(code=1000, message="Bad request", http_status=400)
        assert other_error.is_not_found_error() is False

    def test_feishu_api_error_get_user_friendly_message(self):
        """Test FeishuAPIError get_user_friendly_message method."""
        permission_error = FeishuAPIError(
            code=1310213, message="Permission denied", http_status=403
        )
        assert (
            permission_error.get_user_friendly_message()
            == "权限不足，请检查文档权限设置"
        )

        unknown_error = FeishuAPIError(
            code=9999, message="Unknown error", http_status=500
        )
        assert unknown_error.get_user_friendly_message() == "Unknown error"

    def test_feishu_api_error_needs_auth_refresh(self):
        """Test FeishuAPIError needs_auth_refresh method."""
        auth_error = FeishuAPIError(code=401, message="Unauthorized", http_status=401)
        assert auth_error.needs_auth_refresh() is True

        other_error = FeishuAPIError(code=1310214, message="Not found", http_status=404)
        assert other_error.needs_auth_refresh() is False

    def test_feishu_api_error_is_permanent(self):
        """Test FeishuAPIError is_permanent method."""
        permanent_error = FeishuAPIError(code=1310214, message="Not found", http_status=404)
        assert permanent_error.is_permanent() is True

        retryable_error = FeishuAPIError(code=1310217, message="Too many requests", http_status=429)
        assert retryable_error.is_permanent() is False

    def test_feishu_api_error_get_error_category(self):
        """Test FeishuAPIError get_error_category method."""
        from src.models.error_handling import ErrorCategory

        permission_error = FeishuAPIError(code=1310213, message="Permission denied", http_status=403)
        assert permission_error.get_error_category() == ErrorCategory.PERMISSION

        rate_limit_error = FeishuAPIError(code=1310217, message="Too many requests", http_status=429)
        assert rate_limit_error.get_error_category() == ErrorCategory.RATE_LIMIT

    def test_feishu_api_error_get_retry_config(self):
        """Test FeishuAPIError get_retry_config method."""
        rate_limit_error = FeishuAPIError(code=1310217, message="Too many requests", http_status=429)
        config = rate_limit_error.get_retry_config()
        
        assert config.max_retries == 3
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0

        permanent_error = FeishuAPIError(code=1310214, message="Not found", http_status=404)
        config = permanent_error.get_retry_config()
        
        assert config.max_retries == 0
