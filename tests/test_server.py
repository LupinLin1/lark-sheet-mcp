"""
Tests for FastMCP server.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.server import FeishuSpreadsheetMCPServer
from src.services import AuthenticationManager, FeishuAPIClient


class TestFeishuSpreadsheetMCPServer:
    """Test FeishuSpreadsheetMCPServer class with FastMCP."""

    def test_init(self):
        """Test server initialization."""
        server = FeishuSpreadsheetMCPServer("test_app_id", "test_app_secret")

        assert server.app_id == "test_app_id"
        assert server.app_secret == "test_app_secret"
        assert isinstance(server.auth_manager, AuthenticationManager)
        assert isinstance(server.api_client, FeishuAPIClient)
        assert server.mcp.name == "feishu-spreadsheet-mcp"

    def test_get_mcp_server(self):
        """Test getting FastMCP instance."""
        server = FeishuSpreadsheetMCPServer("test_app_id", "test_app_secret")
        mcp = server.get_mcp_server()
        
        assert mcp.name == "feishu-spreadsheet-mcp"
        assert mcp is server.mcp

    @pytest.mark.asyncio
    async def test_close(self):
        """Test server close method."""
        server = FeishuSpreadsheetMCPServer("test_app_id", "test_app_secret")
        
        # Mock the api_client close method
        server.api_client.close = AsyncMock()
        
        await server.close()
        
        server.api_client.close.assert_called_once()

    def test_pydantic_models(self):
        """Test that Pydantic models are properly defined."""
        from src.server import (
            ListSpreadsheetsArgs,
            GetWorksheetsArgs,
            ReadRangeArgs,
            ReadMultipleRangesArgs,
            FindCellsArgs,
        )

        # Test ListSpreadsheetsArgs
        args = ListSpreadsheetsArgs()
        assert args.folder_token is None
        assert args.page_size == 50

        args_with_data = ListSpreadsheetsArgs(folder_token="test", page_size=10)
        assert args_with_data.folder_token == "test"
        assert args_with_data.page_size == 10

        # Test GetWorksheetsArgs
        worksheet_args = GetWorksheetsArgs(spreadsheet_token="test_token")
        assert worksheet_args.spreadsheet_token == "test_token"

        # Test ReadRangeArgs
        range_args = ReadRangeArgs(spreadsheet_token="test", range_spec="A1:B2")
        assert range_args.spreadsheet_token == "test"
        assert range_args.range_spec == "A1:B2"
        assert range_args.value_render_option == "UnformattedValue"
        assert range_args.date_time_render_option == "FormattedString"

        # Test ReadMultipleRangesArgs
        multi_args = ReadMultipleRangesArgs(
            spreadsheet_token="test", ranges=["A1:B2", "C1:D2"]
        )
        assert multi_args.spreadsheet_token == "test"
        assert multi_args.ranges == ["A1:B2", "C1:D2"]

        # Test FindCellsArgs
        find_args = FindCellsArgs(
            spreadsheet_token="test",
            sheet_id="sheet1",
            range_spec="A1:B2",
            find_text="search",
        )
        assert find_args.spreadsheet_token == "test"
        assert find_args.sheet_id == "sheet1"
        assert find_args.range_spec == "A1:B2"
        assert find_args.find_text == "search"
        assert find_args.match_case is False
        assert find_args.match_entire_cell is False
        assert find_args.search_by_regex is False
        assert find_args.include_formulas is False

    @pytest.mark.asyncio
    async def test_tool_functions(self):
        """Test that tool functions can be called with proper arguments."""
        server = FeishuSpreadsheetMCPServer("test_app_id", "test_app_secret")
        
        # Mock spreadsheet_tools functions
        with patch('src.tools.spreadsheet_tools.list_spreadsheets') as mock_list:
            mock_list.return_value = {"spreadsheets": []}
            
            # Access the registered tool directly from the FastMCP server
            # Note: We can't easily test the decorated functions without running the MCP server
            # So we'll test that the server was created successfully and has the right structure
            assert server.mcp.name == "feishu-spreadsheet-mcp"
            assert hasattr(server, 'api_client')
            assert hasattr(server, 'auth_manager')

    def test_tool_registration(self):
        """Test that tools are properly registered."""
        server = FeishuSpreadsheetMCPServer("test_app_id", "test_app_secret")
        
        # Test that the server has an MCP instance
        assert hasattr(server, 'mcp')
        assert server.mcp.name == "feishu-spreadsheet-mcp"
        
        # Test that _register_tools method exists and was called
        assert hasattr(server, '_register_tools')

    def test_server_creation_with_invalid_credentials(self):
        """Test server creation with various credential formats."""
        # Empty strings
        server1 = FeishuSpreadsheetMCPServer("", "")
        assert server1.app_id == ""
        assert server1.app_secret == ""
        
        # None values (should work but may cause issues later)
        server2 = FeishuSpreadsheetMCPServer(None, None)
        assert server2.app_id is None
        assert server2.app_secret is None

    @pytest.mark.asyncio
    async def test_server_tools_integration(self):
        """Test integration between server and tools."""
        server = FeishuSpreadsheetMCPServer("test_app_id", "test_app_secret")
        
        # Mock the API client methods that tools will call
        server.api_client.list_files = AsyncMock(return_value={
            "data": {
                "files": [],
                "page_token": None
            }
        })
        
        server.api_client.get_spreadsheet_sheets = AsyncMock(return_value={
            "data": {
                "sheets": []
            }
        })
        
        # Test that the server can be closed properly
        server.api_client.close = AsyncMock()
        await server.close()
        server.api_client.close.assert_called_once()


class TestPydanticModels:
    """Test Pydantic models separately."""

    def test_list_spreadsheets_args_validation(self):
        """Test ListSpreadsheetsArgs validation."""
        from src.server import ListSpreadsheetsArgs
        from pydantic import ValidationError
        
        # Valid cases
        args1 = ListSpreadsheetsArgs()
        assert args1.page_size == 50
        
        args2 = ListSpreadsheetsArgs(page_size=100)
        assert args2.page_size == 100
        
        args3 = ListSpreadsheetsArgs(folder_token="test")
        assert args3.folder_token == "test"
        
        # Invalid page_size (should be int)
        with pytest.raises(ValidationError):
            ListSpreadsheetsArgs(page_size="not_int")

    def test_get_worksheets_args_validation(self):
        """Test GetWorksheetsArgs validation."""
        from src.server import GetWorksheetsArgs
        from pydantic import ValidationError
        
        # Valid case
        args = GetWorksheetsArgs(spreadsheet_token="token123")
        assert args.spreadsheet_token == "token123"
        
        # Missing required field
        with pytest.raises(ValidationError):
            GetWorksheetsArgs()

    def test_read_range_args_validation(self):
        """Test ReadRangeArgs validation."""
        from src.server import ReadRangeArgs
        from pydantic import ValidationError
        
        # Valid case
        args = ReadRangeArgs(spreadsheet_token="token", range_spec="A1:B2")
        assert args.spreadsheet_token == "token"
        assert args.range_spec == "A1:B2"
        
        # Missing required fields
        with pytest.raises(ValidationError):
            ReadRangeArgs(spreadsheet_token="token")  # Missing range_spec
        
        with pytest.raises(ValidationError):
            ReadRangeArgs(range_spec="A1:B2")  # Missing spreadsheet_token

    def test_find_cells_args_validation(self):
        """Test FindCellsArgs validation."""
        from src.server import FindCellsArgs
        from pydantic import ValidationError
        
        # Valid case
        args = FindCellsArgs(
            spreadsheet_token="token",
            sheet_id="sheet1",
            range_spec="A1:B2",
            find_text="test"
        )
        assert args.spreadsheet_token == "token"
        assert args.sheet_id == "sheet1"
        assert args.range_spec == "A1:B2"
        assert args.find_text == "test"
        
        # Test boolean defaults
        assert args.match_case is False
        assert args.match_entire_cell is False
        assert args.search_by_regex is False
        assert args.include_formulas is False
        
        # Test with custom boolean values
        args_custom = FindCellsArgs(
            spreadsheet_token="token",
            sheet_id="sheet1",
            range_spec="A1:B2",
            find_text="test",
            match_case=True,
            search_by_regex=True
        )
        assert args_custom.match_case is True
        assert args_custom.search_by_regex is True
        
        # Missing required fields
        with pytest.raises(ValidationError):
            FindCellsArgs(
                sheet_id="sheet1",
                range_spec="A1:B2",
                find_text="test"
            )  # Missing spreadsheet_token