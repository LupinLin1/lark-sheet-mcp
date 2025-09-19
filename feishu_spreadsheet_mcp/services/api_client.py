"""
Feishu API client for making HTTP requests.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import aiohttp

from ..models.data_models import FeishuAPIError
from ..models.error_handling import (
    DEFAULT_RETRY_STRATEGY,
    ErrorCodeMapping,
    RetryStrategy,
)
from .auth_manager import AuthenticationManager

logger = logging.getLogger(__name__)


class RateLimiter:
    """API调用频率限制器"""

    def __init__(self, max_requests: int = 100, time_window: float = 60.0):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum number of requests allowed in time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []  # List of request timestamps
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """
        Acquire permission to make a request.
        Blocks if rate limit would be exceeded.
        """
        async with self._lock:
            now = time.time()

            # Remove old requests outside the time window
            self.requests = [
                req_time
                for req_time in self.requests
                if now - req_time < self.time_window
            ]

            # Check if we can make a request
            if len(self.requests) >= self.max_requests:
                # Calculate how long to wait
                oldest_request = min(self.requests)
                wait_time = self.time_window - (now - oldest_request)

                if wait_time > 0:
                    logger.info("Rate limit reached, waiting %.2f seconds", wait_time)
                    await asyncio.sleep(wait_time)

                    # Retry after waiting
                    await self.acquire()
                    return

            # Record this request
            self.requests.append(now)

    def get_current_usage(self) -> Dict[str, Any]:
        """
        Get current rate limiter usage statistics.

        Returns:
            Dictionary with usage statistics
        """
        now = time.time()
        recent_requests = [
            req_time for req_time in self.requests if now - req_time < self.time_window
        ]

        return {
            "current_requests": len(recent_requests),
            "max_requests": self.max_requests,
            "time_window": self.time_window,
            "usage_percentage": (len(recent_requests) / self.max_requests) * 100,
        }


class FeishuAPIClient:
    """飞书API客户端"""

    def __init__(
        self,
        auth_manager: AuthenticationManager,
        rate_limiter: Optional[RateLimiter] = None,
        retry_strategy: Optional[RetryStrategy] = None,
    ):
        """
        Initialize Feishu API client.

        Args:
            auth_manager: Authentication manager instance
            rate_limiter: Rate limiter instance, creates default if None
            retry_strategy: Retry strategy instance, uses default if None
        """
        self.auth_manager = auth_manager
        self.base_url = "https://open.feishu.cn/open-apis"
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = rate_limiter or RateLimiter()
        self.retry_strategy = retry_strategy or DEFAULT_RETRY_STRATEGY

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=100, limit_per_host=30),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
            self.session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                connector=aiohttp.TCPConnector(limit=100, limit_per_host=30),
            )
        return self.session

    async def _prepare_headers(
        self, additional_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Prepare HTTP headers with authentication token.

        Args:
            additional_headers: Additional headers to include

        Returns:
            Complete headers dictionary with authentication
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "feishu-spreadsheet-mcp/1.0.0",
        }

        # Add authentication token
        try:
            token = await self.auth_manager.get_tenant_access_token()
            headers["Authorization"] = f"Bearer {token}"
        except Exception as e:
            logger.error(f"Failed to get authentication token: {e}")
            raise

        # Add any additional headers
        if additional_headers:
            headers.update(additional_headers)

        return headers

    async def _make_request_with_retry(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        additional_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic and rate limiting.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            data: Request body data
            additional_headers: Additional headers

        Returns:
            API response data

        Raises:
            FeishuAPIError: If API request fails after all retries
        """
        max_attempts = self.retry_strategy.get_max_attempts()

        for attempt in range(max_attempts):
            try:
                # Apply rate limiting
                await self.rate_limiter.acquire()

                # Make the actual request
                return await self._make_request(
                    method, endpoint, params, data, additional_headers
                )

            except FeishuAPIError as e:
                # Check if we should retry
                if not self.retry_strategy.should_retry(e.code, attempt):
                    logger.error(
                        "Request failed permanently after %d attempts: %s",
                        attempt + 1,
                        e,
                    )
                    raise

                # Check if we need to refresh authentication
                if ErrorCodeMapping.needs_auth_refresh(e.code):
                    logger.info("Refreshing authentication token due to auth error")
                    try:
                        await self.auth_manager.refresh_token()
                    except Exception as auth_error:
                        logger.error("Failed to refresh token: %s", auth_error)
                        # Continue with retry anyway

                # Calculate delay for next attempt
                if attempt < max_attempts - 1:  # Don't delay on last attempt
                    delay = self.retry_strategy.get_delay(attempt + 1)
                    logger.warning(
                        "Request failed (attempt %d/%d), retrying in %.2fs. Error: %d - %s",
                        attempt + 1,
                        max_attempts,
                        delay,
                        e.code,
                        e.message,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Request failed after all %d attempts: %s", max_attempts, e
                    )
                    raise

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        additional_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Feishu API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            data: Request body data
            additional_headers: Additional headers

        Returns:
            API response data

        Raises:
            FeishuAPIError: If API request fails
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = await self._prepare_headers(additional_headers)
        session = await self._get_session()

        # Log request details
        logger.info(f"Making {method} request to {url}")
        logger.debug(f"Request headers: {headers}")
        if params:
            logger.debug(f"Request params: {params}")
        if data:
            logger.debug(f"Request data: {data}")

        try:
            request_kwargs = {"headers": headers, "params": params}

            if data is not None:
                request_kwargs["data"] = json.dumps(data)

            async with session.request(method, url, **request_kwargs) as response:
                response_text = await response.text()

                # Log response details
                logger.info(f"Response status: {response.status}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                logger.debug(f"Response body: {response_text}")

                # Parse JSON response
                try:
                    response_data = json.loads(response_text) if response_text else {}
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    raise FeishuAPIError(
                        code=-2,
                        message=f"Invalid JSON response: {str(e)}",
                        http_status=response.status,
                    ) from e

                # Check for HTTP errors
                if response.status >= 400:
                    error_message = response_data.get("msg", f"HTTP {response.status}")
                    error_code = response_data.get("code", response.status)

                    logger.error(f"HTTP error {response.status}: {error_message}")
                    raise FeishuAPIError(
                        code=error_code,
                        message=error_message,
                        http_status=response.status,
                    )

                # Check for API errors
                if response_data.get("code", 0) != 0:
                    error_code = response_data.get("code", -1)
                    error_message = response_data.get("msg", "Unknown API error")

                    logger.error(f"API error {error_code}: {error_message}")
                    raise FeishuAPIError(
                        code=error_code,
                        message=error_message,
                        http_status=response.status,
                    )

                return response_data

        except aiohttp.ClientError as e:
            logger.error(f"Network error during request to {url}: {e}")
            raise FeishuAPIError(
                code=-1, message=f"Network error: {str(e)}", http_status=500
            ) from e

    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None

    def get_rate_limiter_stats(self) -> Dict[str, Any]:
        """
        Get current rate limiter statistics.

        Returns:
            Dictionary with rate limiter usage statistics
        """
        return self.rate_limiter.get_current_usage()

    async def list_files(
        self, folder_token: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """
        获取文件列表

        Args:
            folder_token: Folder token, None for root directory
            **kwargs: Additional parameters like page_size, page_token

        Returns:
            API response data
        """
        endpoint = "drive/v1/files"
        params = {}

        if folder_token:
            params["folder_token"] = folder_token

        # Add additional parameters
        if "page_size" in kwargs:
            params["page_size"] = min(kwargs["page_size"], 200)  # Max 200 per API docs
        if "page_token" in kwargs:
            params["page_token"] = kwargs["page_token"]

        return await self._make_request_with_retry("GET", endpoint, params=params)

    async def get_worksheets(self, spreadsheet_token: str) -> Dict[str, Any]:
        """
        获取工作表列表

        Args:
            spreadsheet_token: Spreadsheet token

        Returns:
            API response data
        """
        endpoint = f"sheets/v3/spreadsheets/{spreadsheet_token}/sheets/query"
        return await self._make_request_with_retry("GET", endpoint)

    async def read_range(
        self, spreadsheet_token: str, range_spec: str, **kwargs
    ) -> Dict[str, Any]:
        """
        读取单个范围

        Args:
            spreadsheet_token: Spreadsheet token
            range_spec: Range specification like "sheetId!A1:B10"
            **kwargs: Additional parameters like value_render_option, date_time_render_option, user_id_type

        Returns:
            API response data
        """
        # URL encode the range_spec properly for the sheets API
        # Handle both escaped and unescaped exclamation marks
        encoded_range = range_spec.replace("\\!", "%21").replace("!", "%21").replace(":", "%3A")
        endpoint = f"sheets/v2/spreadsheets/{spreadsheet_token}/values/{encoded_range}"
        
        params = {}

        # Add optional parameters
        if "value_render_option" in kwargs:
            params["valueRenderOption"] = kwargs["value_render_option"]
        if "date_time_render_option" in kwargs:
            params["dateTimeRenderOption"] = kwargs["date_time_render_option"]
        if "user_id_type" in kwargs:
            params["user_id_type"] = kwargs["user_id_type"]

        return await self._make_request_with_retry("GET", endpoint, params=params)

    async def read_multiple_ranges(
        self, spreadsheet_token: str, ranges: List[str], **kwargs
    ) -> Dict[str, Any]:
        """
        读取多个范围

        Args:
            spreadsheet_token: Spreadsheet token
            ranges: List of range specifications
            **kwargs: Additional parameters like value_render_option, date_time_render_option, user_id_type

        Returns:
            API response data
        """
        endpoint = f"sheets/v2/spreadsheets/{spreadsheet_token}/values_batch_get"
        # Let aiohttp handle URL encoding automatically by passing raw ranges
        # The client will properly encode special characters in query parameters
        params = {"ranges": ",".join(ranges)}

        # Add optional parameters
        if "value_render_option" in kwargs:
            params["valueRenderOption"] = kwargs["value_render_option"]
        if "date_time_render_option" in kwargs:
            params["dateTimeRenderOption"] = kwargs["date_time_render_option"]
        if "user_id_type" in kwargs:
            params["user_id_type"] = kwargs["user_id_type"]

        return await self._make_request_with_retry("GET", endpoint, params=params)

    async def find_cells(
        self, spreadsheet_token: str, sheet_id: str, **kwargs
    ) -> Dict[str, Any]:
        """
        查找单元格

        Args:
            spreadsheet_token: Spreadsheet token
            sheet_id: Sheet ID
            **kwargs: Additional parameters like range_spec, find_text, match_case, match_entire_cell,
                     search_by_regex, include_formulas

        Returns:
            API response data
        """
        endpoint = f"sheets/v3/spreadsheets/{spreadsheet_token}/sheets/{sheet_id}/find"

        # Build request body according to Feishu API documentation
        if "range_spec" not in kwargs:
            raise ValueError("range_spec is required for find_cells")
        if "find_text" not in kwargs:
            raise ValueError("find_text is required for find_cells")

        # Construct the range in the correct format: "sheetId!A1:C5"
        range_spec = kwargs["range_spec"]
        if "!" not in range_spec:
            # If range_spec doesn't include sheet_id, prepend it
            range_with_sheet = f"{sheet_id}!{range_spec}"
        else:
            # Range already includes sheet_id
            range_with_sheet = range_spec
            
        find_condition = {
            "range": range_with_sheet,
            "match_case": kwargs.get("match_case", False),
            "match_entire_cell": kwargs.get("match_entire_cell", False),
            "search_by_regex": kwargs.get("search_by_regex", False),
            "include_formulas": kwargs.get("include_formulas", False),
        }

        data = {"find_condition": find_condition, "find": kwargs["find_text"]}

        return await self._make_request_with_retry("POST", endpoint, data=data)
