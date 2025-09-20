"""
Tests for Feishu API client.
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest

from src.models.data_models import FeishuAPIError
from src.models.error_handling import RetryStrategy, RetryConfig
from src.services import AuthenticationManager, FeishuAPIClient
from src.services.api_client import RateLimiter


class TestFeishuAPIClient:
    """Test FeishuAPIClient class."""

    def test_init(self):
        """Test FeishuAPIClient initialization."""
        auth_manager = Mock(spec=AuthenticationManager)
        client = FeishuAPIClient(auth_manager)

        assert client.auth_manager is auth_manager
        assert client.base_url == "https://open.feishu.cn/open-apis"
        assert client.session is None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        auth_manager = Mock(spec=AuthenticationManager)

        async with FeishuAPIClient(auth_manager) as client:
            assert client.session is not None
            assert isinstance(client.session, aiohttp.ClientSession)

        # Session should be closed after exiting context
        assert client.session is None

    @pytest.mark.asyncio
    async def test_get_session_creates_session(self):
        """Test that _get_session creates a session if none exists."""
        auth_manager = Mock(spec=AuthenticationManager)
        client = FeishuAPIClient(auth_manager)

        assert client.session is None
        session = await client._get_session()

        assert session is not None
        assert isinstance(session, aiohttp.ClientSession)
        assert client.session is session

        # Cleanup
        await client.close()

    @pytest.mark.asyncio
    async def test_get_session_returns_existing(self):
        """Test that _get_session returns existing session."""
        auth_manager = Mock(spec=AuthenticationManager)

        async with FeishuAPIClient(auth_manager) as client:
            session1 = await client._get_session()
            session2 = await client._get_session()

            assert session1 is session2

    @pytest.mark.asyncio
    async def test_prepare_headers_basic(self):
        """Test basic header preparation."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(return_value="test_token")

        client = FeishuAPIClient(auth_manager)
        headers = await client._prepare_headers()

        expected_headers = {
            "Content-Type": "application/json",
            "User-Agent": "feishu-spreadsheet-mcp/1.0.0",
            "Authorization": "Bearer test_token",
        }

        assert headers == expected_headers
        auth_manager.get_tenant_access_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_prepare_headers_with_additional(self):
        """Test header preparation with additional headers."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(return_value="test_token")

        client = FeishuAPIClient(auth_manager)
        additional_headers = {"X-Custom-Header": "custom_value"}
        headers = await client._prepare_headers(additional_headers)

        expected_headers = {
            "Content-Type": "application/json",
            "User-Agent": "feishu-spreadsheet-mcp/1.0.0",
            "Authorization": "Bearer test_token",
            "X-Custom-Header": "custom_value",
        }

        assert headers == expected_headers

    @pytest.mark.asyncio
    async def test_prepare_headers_auth_failure(self):
        """Test header preparation when authentication fails."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(
            side_effect=Exception("Auth failed")
        )

        client = FeishuAPIClient(auth_manager)

        with pytest.raises(Exception, match="Auth failed"):
            await client._prepare_headers()

    @pytest.mark.asyncio
    async def test_make_request_success(self):
        """Test successful HTTP request."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(return_value="test_token")

        # Mock response
        mock_response_data = {"code": 0, "msg": "success", "data": {"result": "test"}}
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
        mock_response.headers = {"Content-Type": "application/json"}

        # Mock session with proper async context manager
        mock_session = Mock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = Mock(return_value=mock_context_manager)

        client = FeishuAPIClient(auth_manager)
        client.session = mock_session

        result = await client._make_request("GET", "/test/endpoint")

        assert result == mock_response_data
        mock_session.request.assert_called_once()

        # Verify request parameters
        call_args = mock_session.request.call_args
        assert call_args[0][0] == "GET"  # method
        assert (
            call_args[0][1] == "https://open.feishu.cn/open-apis/test/endpoint"
        )  # url
        assert "Authorization" in call_args[1]["headers"]
        assert call_args[1]["headers"]["Authorization"] == "Bearer test_token"

    @pytest.mark.asyncio
    async def test_make_request_with_params_and_data(self):
        """Test HTTP request with parameters and data."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(return_value="test_token")

        # Mock response
        mock_response_data = {"code": 0, "msg": "success"}
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
        mock_response.headers = {}

        # Mock session with proper async context manager
        mock_session = Mock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = Mock(return_value=mock_context_manager)

        client = FeishuAPIClient(auth_manager)
        client.session = mock_session

        params = {"page_size": 50}
        data = {"test": "value"}

        result = await client._make_request(
            "POST", "/test/endpoint", params=params, data=data
        )

        assert result == mock_response_data

        # Verify request parameters
        call_args = mock_session.request.call_args
        assert call_args[1]["params"] == params
        assert call_args[1]["data"] == json.dumps(data)

    @pytest.mark.asyncio
    async def test_make_request_http_error(self):
        """Test HTTP request with HTTP error status."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(return_value="test_token")

        # Mock error response
        mock_response_data = {"code": 1001, "msg": "Invalid request"}
        mock_response = Mock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
        mock_response.headers = {}

        # Mock session with proper async context manager
        mock_session = Mock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = Mock(return_value=mock_context_manager)

        client = FeishuAPIClient(auth_manager)
        client.session = mock_session

        with pytest.raises(FeishuAPIError) as exc_info:
            await client._make_request("GET", "/test/endpoint")

        error = exc_info.value
        assert error.code == 1001
        assert error.message == "Invalid request"
        assert error.http_status == 400

    @pytest.mark.asyncio
    async def test_make_request_api_error(self):
        """Test HTTP request with API error code."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(return_value="test_token")

        # Mock API error response
        mock_response_data = {"code": 1310214, "msg": "Spreadsheet not found"}
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
        mock_response.headers = {}

        # Mock session with proper async context manager
        mock_session = Mock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = Mock(return_value=mock_context_manager)

        client = FeishuAPIClient(auth_manager)
        client.session = mock_session

        with pytest.raises(FeishuAPIError) as exc_info:
            await client._make_request("GET", "/test/endpoint")

        error = exc_info.value
        assert error.code == 1310214
        assert error.message == "Spreadsheet not found"
        assert error.http_status == 200

    @pytest.mark.asyncio
    async def test_make_request_json_decode_error(self):
        """Test HTTP request with invalid JSON response."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(return_value="test_token")

        # Mock invalid JSON response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="invalid json")
        mock_response.headers = {}

        # Mock session with proper async context manager
        mock_session = Mock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = Mock(return_value=mock_context_manager)

        client = FeishuAPIClient(auth_manager)
        client.session = mock_session

        with pytest.raises(FeishuAPIError) as exc_info:
            await client._make_request("GET", "/test/endpoint")

        error = exc_info.value
        assert error.code == -2
        assert "Invalid JSON response" in error.message
        assert error.http_status == 200

    @pytest.mark.asyncio
    async def test_make_request_network_error(self):
        """Test HTTP request with network error."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(return_value="test_token")

        # Mock session with network error
        mock_session = Mock()
        mock_session.request = Mock(
            side_effect=aiohttp.ClientError("Connection failed")
        )

        client = FeishuAPIClient(auth_manager)
        client.session = mock_session

        with pytest.raises(FeishuAPIError) as exc_info:
            await client._make_request("GET", "/test/endpoint")

        error = exc_info.value
        assert error.code == -1
        assert "Network error" in error.message
        assert error.http_status == 0

    @pytest.mark.asyncio
    async def test_close_session(self):
        """Test closing HTTP session."""
        auth_manager = Mock(spec=AuthenticationManager)
        client = FeishuAPIClient(auth_manager)

        # Create a session
        await client._get_session()
        assert client.session is not None

        # Close the session
        await client.close()
        assert client.session is None

    @pytest.mark.asyncio
    async def test_close_no_session(self):
        """Test closing when no session exists."""
        auth_manager = Mock(spec=AuthenticationManager)
        client = FeishuAPIClient(auth_manager)

        # Should not raise error
        await client.close()
        assert client.session is None

    # Test method signatures (implementations in task 4.2)
    def test_list_files_method_exists(self):
        """Test that list_files method exists."""
        auth_manager = Mock(spec=AuthenticationManager)
        client = FeishuAPIClient(auth_manager)

        assert hasattr(client, "list_files")
        assert callable(client.list_files)

    def test_get_worksheets_method_exists(self):
        """Test that get_worksheets method exists."""
        auth_manager = Mock(spec=AuthenticationManager)
        client = FeishuAPIClient(auth_manager)

        assert hasattr(client, "get_worksheets")
        assert callable(client.get_worksheets)

    def test_read_range_method_exists(self):
        """Test that read_range method exists."""
        auth_manager = Mock(spec=AuthenticationManager)
        client = FeishuAPIClient(auth_manager)

        assert hasattr(client, "read_range")
        assert callable(client.read_range)

    def test_read_multiple_ranges_method_exists(self):
        """Test that read_multiple_ranges method exists."""
        auth_manager = Mock(spec=AuthenticationManager)
        client = FeishuAPIClient(auth_manager)

        assert hasattr(client, "read_multiple_ranges")
        assert callable(client.read_multiple_ranges)

    def test_find_cells_method_exists(self):
        """Test that find_cells method exists."""
        auth_manager = Mock(spec=AuthenticationManager)
        client = FeishuAPIClient(auth_manager)

        assert hasattr(client, "find_cells")
        assert callable(client.find_cells)

    @pytest.mark.asyncio
    async def test_list_files_success(self):
        """Test successful list_files call."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(return_value="test_token")

        # Mock response
        mock_response_data = {
            "code": 0,
            "msg": "success",
            "data": {
                "files": [
                    {"token": "test_token", "name": "test_sheet", "type": "sheet"}
                ]
            },
        }
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
        mock_response.headers = {}

        # Mock session
        mock_session = Mock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = Mock(return_value=mock_context_manager)

        client = FeishuAPIClient(auth_manager)
        client.session = mock_session

        result = await client.list_files(folder_token="test_folder", page_size=50)

        assert result == mock_response_data
        mock_session.request.assert_called_once()

        # Verify request parameters
        call_args = mock_session.request.call_args
        assert call_args[0][0] == "GET"
        assert "drive/v1/files" in call_args[0][1]
        assert call_args[1]["params"]["folder_token"] == "test_folder"
        assert call_args[1]["params"]["page_size"] == 50

    @pytest.mark.asyncio
    async def test_get_worksheets_success(self):
        """Test successful get_worksheets call."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(return_value="test_token")

        # Mock response
        mock_response_data = {
            "code": 0,
            "msg": "success",
            "data": {
                "sheets": [
                    {
                        "sheet_id": "test_sheet_id",
                        "title": "Sheet1",
                        "index": 0,
                        "hidden": False,
                        "grid_properties": {"row_count": 100, "column_count": 26},
                    }
                ]
            },
        }
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
        mock_response.headers = {}

        # Mock session
        mock_session = Mock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = Mock(return_value=mock_context_manager)

        client = FeishuAPIClient(auth_manager)
        client.session = mock_session

        result = await client.get_worksheets("test_spreadsheet_token")

        assert result == mock_response_data
        mock_session.request.assert_called_once()

        # Verify request parameters
        call_args = mock_session.request.call_args
        assert call_args[0][0] == "GET"
        assert (
            "sheets/v3/spreadsheets/test_spreadsheet_token/sheets/query"
            in call_args[0][1]
        )

    @pytest.mark.asyncio
    async def test_read_range_success(self):
        """Test successful read_range call."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(return_value="test_token")

        # Mock response
        mock_response_data = {
            "code": 0,
            "msg": "success",
            "data": {
                "valueRange": {
                    "range": "Sheet1!A1:B2",
                    "majorDimension": "ROWS",
                    "values": [["A1", "B1"], ["A2", "B2"]],
                }
            },
        }
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
        mock_response.headers = {}

        # Mock session
        mock_session = Mock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = Mock(return_value=mock_context_manager)

        client = FeishuAPIClient(auth_manager)
        client.session = mock_session

        result = await client.read_range(
            "test_spreadsheet_token",
            "Sheet1!A1:B2",
            value_render_option="UnformattedValue",
        )

        assert result == mock_response_data
        mock_session.request.assert_called_once()

        # Verify request parameters
        call_args = mock_session.request.call_args
        assert call_args[0][0] == "GET"
        assert (
            "sheets/v2/spreadsheets/test_spreadsheet_token/values/Sheet1!A1:B2"
            in call_args[0][1]
        )
        assert call_args[1]["params"]["valueRenderOption"] == "UnformattedValue"

    @pytest.mark.asyncio
    async def test_read_multiple_ranges_success(self):
        """Test successful read_multiple_ranges call."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(return_value="test_token")

        # Mock response
        mock_response_data = {
            "code": 0,
            "msg": "success",
            "data": {
                "valueRanges": [
                    {
                        "range": "Sheet1!A1:B2",
                        "majorDimension": "ROWS",
                        "values": [["A1", "B1"], ["A2", "B2"]],
                    },
                    {
                        "range": "Sheet1!C1:D2",
                        "majorDimension": "ROWS",
                        "values": [["C1", "D1"], ["C2", "D2"]],
                    },
                ]
            },
        }
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
        mock_response.headers = {}

        # Mock session
        mock_session = Mock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = Mock(return_value=mock_context_manager)

        client = FeishuAPIClient(auth_manager)
        client.session = mock_session

        result = await client.read_multiple_ranges(
            "test_spreadsheet_token", ["Sheet1!A1:B2", "Sheet1!C1:D2"]
        )

        assert result == mock_response_data
        mock_session.request.assert_called_once()

        # Verify request parameters
        call_args = mock_session.request.call_args
        assert call_args[0][0] == "GET"
        assert (
            "sheets/v2/spreadsheets/test_spreadsheet_token/values_batch_get"
            in call_args[0][1]
        )
        assert call_args[1]["params"]["ranges"] == "Sheet1!A1:B2,Sheet1!C1:D2"

    @pytest.mark.asyncio
    async def test_find_cells_success(self):
        """Test successful find_cells call."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(return_value="test_token")

        # Mock response
        mock_response_data = {
            "code": 0,
            "msg": "success",
            "data": {
                "find_result": {
                    "matched_cells": ["A1", "B2"],
                    "matched_formula_cells": ["C3"],
                    "rows_count": 3,
                }
            },
        }
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
        mock_response.headers = {}

        # Mock session
        mock_session = Mock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = Mock(return_value=mock_context_manager)

        client = FeishuAPIClient(auth_manager)
        client.session = mock_session

        result = await client.find_cells(
            "test_spreadsheet_token",
            "sheet123",
            range_spec="sheet123!A1:C10",
            find_text="test",
            match_case=True,
        )

        assert result == mock_response_data
        mock_session.request.assert_called_once()

        # Verify request parameters
        call_args = mock_session.request.call_args
        assert call_args[0][0] == "POST"
        assert (
            "sheets/v3/spreadsheets/test_spreadsheet_token/sheets/sheet123/find"
            in call_args[0][1]
        )

        # Verify request body
        expected_data = {
            "find_condition": {
                "range": "sheet123!A1:C10",
                "match_case": True,
                "match_entire_cell": False,
                "search_by_regex": False,
                "include_formulas": False,
            },
            "find": "test",
        }
        assert call_args[1]["data"] == json.dumps(expected_data)

    @pytest.mark.asyncio
    async def test_find_cells_missing_range_spec(self):
        """Test find_cells with missing range_spec parameter."""
        auth_manager = Mock(spec=AuthenticationManager)
        client = FeishuAPIClient(auth_manager)

        with pytest.raises(ValueError, match="range_spec is required for find_cells"):
            await client.find_cells(
                "test_spreadsheet_token", "sheet123", find_text="test"
            )

    @pytest.mark.asyncio
    async def test_find_cells_missing_find_text(self):
        """Test find_cells with missing find_text parameter."""
        auth_manager = Mock(spec=AuthenticationManager)
        client = FeishuAPIClient(auth_manager)

        with pytest.raises(ValueError, match="find_text is required for find_cells"):
            await client.find_cells(
                "test_spreadsheet_token", "sheet123", range_spec="sheet123!A1:C10"
            )


class TestRateLimiter:
    """Test RateLimiter class."""

    def test_init(self):
        """Test RateLimiter initialization."""
        limiter = RateLimiter(max_requests=100, time_window=60.0)
        
        assert limiter.max_requests == 100
        assert limiter.time_window == 60.0
        assert limiter.requests == []

    def test_init_defaults(self):
        """Test RateLimiter initialization with defaults."""
        limiter = RateLimiter()
        
        assert limiter.max_requests == 100
        assert limiter.time_window == 60.0

    @pytest.mark.asyncio
    async def test_acquire_first_request(self):
        """Test acquiring permission for first request."""
        limiter = RateLimiter(max_requests=5, time_window=60.0)
        
        start_time = time.time()
        await limiter.acquire()
        end_time = time.time()
        
        # Should not block
        assert end_time - start_time < 0.1
        assert len(limiter.requests) == 1

    @pytest.mark.asyncio
    async def test_acquire_within_limit(self):
        """Test acquiring permission when within rate limit."""
        limiter = RateLimiter(max_requests=5, time_window=60.0)
        
        # Make 4 requests quickly
        for _ in range(4):
            await limiter.acquire()
        
        # 5th request should still be allowed
        start_time = time.time()
        await limiter.acquire()
        end_time = time.time()
        
        assert end_time - start_time < 0.1
        assert len(limiter.requests) == 5

    @pytest.mark.asyncio
    async def test_acquire_rate_limit_exceeded(self):
        """Test acquiring permission when rate limit is exceeded."""
        limiter = RateLimiter(max_requests=2, time_window=1.0)
        
        # Make 2 requests to reach limit
        await limiter.acquire()
        await limiter.acquire()
        
        # Mock sleep to avoid actual waiting
        with patch('asyncio.sleep') as mock_sleep:
            mock_sleep.return_value = None
            await limiter.acquire()
        
        # Should have called sleep
        mock_sleep.assert_called()
        assert len(limiter.requests) == 3

    @pytest.mark.asyncio
    async def test_acquire_old_requests_cleaned(self):
        """Test that old requests are cleaned up."""
        limiter = RateLimiter(max_requests=3, time_window=0.5)
        
        # Make 2 requests
        await limiter.acquire()
        await limiter.acquire()
        
        # Simulate time passing by manually setting old timestamps
        now = time.time()
        limiter.requests = [now - 1.0, now - 0.8]  # Both outside 0.5s window
        
        # Make another request - should not block as old requests are cleaned
        start_time = time.time()
        await limiter.acquire()
        end_time = time.time()
        
        assert end_time - start_time < 0.1
        # Should only have 1 request (the recent one)
        assert len(limiter.requests) == 1

    def test_get_current_usage_empty(self):
        """Test getting usage statistics when no requests made."""
        limiter = RateLimiter(max_requests=100, time_window=60.0)
        
        stats = limiter.get_current_usage()
        
        assert stats["current_requests"] == 0
        assert stats["max_requests"] == 100
        assert stats["time_window"] == 60.0
        assert stats["usage_percentage"] == 0.0

    def test_get_current_usage_with_requests(self):
        """Test getting usage statistics with active requests."""
        limiter = RateLimiter(max_requests=10, time_window=60.0)
        
        # Simulate 3 recent requests
        now = time.time()
        limiter.requests = [now - 10, now - 5, now - 1]
        
        stats = limiter.get_current_usage()
        
        assert stats["current_requests"] == 3
        assert stats["max_requests"] == 10
        assert stats["time_window"] == 60.0
        assert stats["usage_percentage"] == 30.0

    def test_get_current_usage_filters_old_requests(self):
        """Test that usage statistics filter out old requests."""
        limiter = RateLimiter(max_requests=10, time_window=30.0)
        
        # Simulate mix of old and recent requests
        now = time.time()
        limiter.requests = [
            now - 60,  # Old request (outside window)
            now - 40,  # Old request (outside window)
            now - 10,  # Recent request
            now - 5,   # Recent request
        ]
        
        stats = limiter.get_current_usage()
        
        # Should only count the 2 recent requests
        assert stats["current_requests"] == 2
        assert stats["usage_percentage"] == 20.0


class TestFeishuAPIClientRateLimit:
    """Test FeishuAPIClient rate limiting and retry functionality."""

    def test_init_with_rate_limiter(self):
        """Test FeishuAPIClient initialization with custom rate limiter."""
        auth_manager = Mock(spec=AuthenticationManager)
        rate_limiter = RateLimiter(max_requests=50, time_window=30.0)
        retry_strategy = RetryStrategy(RetryConfig(max_retries=5))
        
        client = FeishuAPIClient(
            auth_manager, 
            rate_limiter=rate_limiter, 
            retry_strategy=retry_strategy
        )
        
        assert client.rate_limiter is rate_limiter
        assert client.retry_strategy is retry_strategy

    def test_init_with_defaults(self):
        """Test FeishuAPIClient initialization with default rate limiter and retry strategy."""
        auth_manager = Mock(spec=AuthenticationManager)
        client = FeishuAPIClient(auth_manager)
        
        assert isinstance(client.rate_limiter, RateLimiter)
        assert isinstance(client.retry_strategy, RetryStrategy)

    def test_get_rate_limiter_stats(self):
        """Test getting rate limiter statistics."""
        auth_manager = Mock(spec=AuthenticationManager)
        rate_limiter = Mock(spec=RateLimiter)
        rate_limiter.get_current_usage.return_value = {
            "current_requests": 5,
            "max_requests": 100,
            "usage_percentage": 5.0
        }
        
        client = FeishuAPIClient(auth_manager, rate_limiter=rate_limiter)
        stats = client.get_rate_limiter_stats()
        
        assert stats["current_requests"] == 5
        assert stats["max_requests"] == 100
        assert stats["usage_percentage"] == 5.0
        rate_limiter.get_current_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_with_retry_success_first_attempt(self):
        """Test successful request on first attempt."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(return_value="test_token")
        
        rate_limiter = Mock(spec=RateLimiter)
        rate_limiter.acquire = AsyncMock()
        
        client = FeishuAPIClient(auth_manager, rate_limiter=rate_limiter)
        
        # Mock successful response
        mock_response_data = {"code": 0, "msg": "success", "data": {"result": "test"}}
        client._make_request = AsyncMock(return_value=mock_response_data)
        
        result = await client._make_request_with_retry("GET", "/test")
        
        assert result == mock_response_data
        rate_limiter.acquire.assert_called_once()
        client._make_request.assert_called_once_with("GET", "/test", None, None, None)

    @pytest.mark.asyncio
    async def test_make_request_with_retry_retryable_error(self):
        """Test retry on retryable error."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(return_value="test_token")
        auth_manager.refresh_token = AsyncMock()
        
        rate_limiter = Mock(spec=RateLimiter)
        rate_limiter.acquire = AsyncMock()
        
        retry_config = RetryConfig(max_retries=2, base_delay=0.1)
        retry_strategy = RetryStrategy(retry_config)
        
        client = FeishuAPIClient(
            auth_manager, 
            rate_limiter=rate_limiter, 
            retry_strategy=retry_strategy
        )
        
        # Mock first call fails with retryable error, second succeeds
        mock_error = FeishuAPIError(code=1310217, message="Too Many Request", http_status=429)
        mock_success = {"code": 0, "msg": "success", "data": {"result": "test"}}
        
        client._make_request = AsyncMock(side_effect=[mock_error, mock_success])
        
        with patch('asyncio.sleep') as mock_sleep:
            result = await client._make_request_with_retry("GET", "/test")
        
        assert result == mock_success
        assert rate_limiter.acquire.call_count == 2
        assert client._make_request.call_count == 2
        mock_sleep.assert_called_once()  # Should have slept before retry

    @pytest.mark.asyncio
    async def test_make_request_with_retry_auth_refresh(self):
        """Test authentication refresh on auth error."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(return_value="test_token")
        auth_manager.refresh_token = AsyncMock()
        
        rate_limiter = Mock(spec=RateLimiter)
        rate_limiter.acquire = AsyncMock()
        
        retry_config = RetryConfig(max_retries=2, base_delay=0.1)
        retry_strategy = RetryStrategy(retry_config)
        
        client = FeishuAPIClient(
            auth_manager, 
            rate_limiter=rate_limiter, 
            retry_strategy=retry_strategy
        )
        
        # Mock first call fails with auth error, second succeeds
        mock_error = FeishuAPIError(code=401, message="Unauthorized", http_status=401)
        mock_success = {"code": 0, "msg": "success", "data": {"result": "test"}}
        
        client._make_request = AsyncMock(side_effect=[mock_error, mock_success])
        
        with patch('asyncio.sleep') as mock_sleep:
            result = await client._make_request_with_retry("GET", "/test")
        
        assert result == mock_success
        auth_manager.refresh_token.assert_called_once()
        mock_sleep.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_with_retry_permanent_error(self):
        """Test no retry on permanent error."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(return_value="test_token")
        
        rate_limiter = Mock(spec=RateLimiter)
        rate_limiter.acquire = AsyncMock()
        
        client = FeishuAPIClient(auth_manager, rate_limiter=rate_limiter)
        
        # Mock permanent error (not retryable)
        mock_error = FeishuAPIError(code=1310214, message="Spreadsheet not found", http_status=404)
        client._make_request = AsyncMock(side_effect=mock_error)
        
        with pytest.raises(FeishuAPIError) as exc_info:
            await client._make_request_with_retry("GET", "/test")
        
        assert exc_info.value.code == 1310214
        rate_limiter.acquire.assert_called_once()
        client._make_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_with_retry_max_attempts_exceeded(self):
        """Test failure after max retry attempts."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(return_value="test_token")
        auth_manager.refresh_token = AsyncMock()
        
        rate_limiter = Mock(spec=RateLimiter)
        rate_limiter.acquire = AsyncMock()
        
        retry_config = RetryConfig(max_retries=2, base_delay=0.1)
        retry_strategy = RetryStrategy(retry_config)
        
        client = FeishuAPIClient(
            auth_manager, 
            rate_limiter=rate_limiter, 
            retry_strategy=retry_strategy
        )
        
        # Mock all attempts fail with retryable error
        mock_error = FeishuAPIError(code=1310217, message="Too Many Request", http_status=429)
        client._make_request = AsyncMock(side_effect=mock_error)
        
        with patch('asyncio.sleep') as mock_sleep:
            with pytest.raises(FeishuAPIError) as exc_info:
                await client._make_request_with_retry("GET", "/test")
        
        assert exc_info.value.code == 1310217
        # Should have made 3 attempts (initial + 2 retries)
        assert client._make_request.call_count == 3
        assert rate_limiter.acquire.call_count == 3
        # Should have slept 2 times (before each retry)
        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_make_request_with_retry_auth_refresh_failure(self):
        """Test handling of auth refresh failure."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(return_value="test_token")
        auth_manager.refresh_token = AsyncMock(side_effect=Exception("Refresh failed"))
        
        rate_limiter = Mock(spec=RateLimiter)
        rate_limiter.acquire = AsyncMock()
        
        retry_config = RetryConfig(max_retries=2, base_delay=0.1)
        retry_strategy = RetryStrategy(retry_config)
        
        client = FeishuAPIClient(
            auth_manager, 
            rate_limiter=rate_limiter, 
            retry_strategy=retry_strategy
        )
        
        # Mock auth error, then success (should continue despite refresh failure)
        mock_error = FeishuAPIError(code=401, message="Unauthorized", http_status=401)
        mock_success = {"code": 0, "msg": "success", "data": {"result": "test"}}
        
        client._make_request = AsyncMock(side_effect=[mock_error, mock_success])
        
        with patch('asyncio.sleep') as mock_sleep:
            result = await client._make_request_with_retry("GET", "/test")
        
        assert result == mock_success
        auth_manager.refresh_token.assert_called_once()
        mock_sleep.assert_called_once()

    @pytest.mark.asyncio
    async def test_integration_list_files_with_retry(self):
        """Test list_files method uses retry mechanism."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(return_value="test_token")
        
        rate_limiter = Mock(spec=RateLimiter)
        rate_limiter.acquire = AsyncMock()
        
        client = FeishuAPIClient(auth_manager, rate_limiter=rate_limiter)
        
        # Mock successful response
        mock_response_data = {"code": 0, "msg": "success", "data": {"files": []}}
        client._make_request = AsyncMock(return_value=mock_response_data)
        
        result = await client.list_files()
        
        assert result == mock_response_data
        rate_limiter.acquire.assert_called_once()

    @pytest.mark.asyncio
    async def test_integration_get_worksheets_with_retry(self):
        """Test get_worksheets method uses retry mechanism."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(return_value="test_token")
        
        rate_limiter = Mock(spec=RateLimiter)
        rate_limiter.acquire = AsyncMock()
        
        client = FeishuAPIClient(auth_manager, rate_limiter=rate_limiter)
        
        # Mock successful response
        mock_response_data = {"code": 0, "msg": "success", "data": {"sheets": []}}
        client._make_request = AsyncMock(return_value=mock_response_data)
        
        result = await client.get_worksheets("test_token")
        
        assert result == mock_response_data
        rate_limiter.acquire.assert_called_once()

    @pytest.mark.asyncio
    async def test_integration_read_range_with_retry(self):
        """Test read_range method uses retry mechanism."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(return_value="test_token")
        
        rate_limiter = Mock(spec=RateLimiter)
        rate_limiter.acquire = AsyncMock()
        
        client = FeishuAPIClient(auth_manager, rate_limiter=rate_limiter)
        
        # Mock successful response
        mock_response_data = {"code": 0, "msg": "success", "data": {"valueRange": {}}}
        client._make_request = AsyncMock(return_value=mock_response_data)
        
        result = await client.read_range("test_token", "Sheet1!A1:B2")
        
        assert result == mock_response_data
        rate_limiter.acquire.assert_called_once()

    @pytest.mark.asyncio
    async def test_integration_read_multiple_ranges_with_retry(self):
        """Test read_multiple_ranges method uses retry mechanism."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(return_value="test_token")
        
        rate_limiter = Mock(spec=RateLimiter)
        rate_limiter.acquire = AsyncMock()
        
        client = FeishuAPIClient(auth_manager, rate_limiter=rate_limiter)
        
        # Mock successful response
        mock_response_data = {"code": 0, "msg": "success", "data": {"valueRanges": []}}
        client._make_request = AsyncMock(return_value=mock_response_data)
        
        result = await client.read_multiple_ranges("test_token", ["Sheet1!A1:B2"])
        
        assert result == mock_response_data
        rate_limiter.acquire.assert_called_once()

    @pytest.mark.asyncio
    async def test_integration_find_cells_with_retry(self):
        """Test find_cells method uses retry mechanism."""
        auth_manager = Mock(spec=AuthenticationManager)
        auth_manager.get_tenant_access_token = AsyncMock(return_value="test_token")
        
        rate_limiter = Mock(spec=RateLimiter)
        rate_limiter.acquire = AsyncMock()
        
        client = FeishuAPIClient(auth_manager, rate_limiter=rate_limiter)
        
        # Mock successful response
        mock_response_data = {"code": 0, "msg": "success", "data": {"find_result": {}}}
        client._make_request = AsyncMock(return_value=mock_response_data)
        
        result = await client.find_cells(
            "test_token", "sheet123", range_spec="Sheet1!A1:B2", find_text="test"
        )
        
        assert result == mock_response_data
        rate_limiter.acquire.assert_called_once()
