"""
Authentication manager for Feishu API.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional

import aiohttp

from ..models.data_models import FeishuAPIError
from ..models.error_handling import (
    AuthenticationError,
    ErrorCodeMapping,
    RetryConfig,
    RetryStrategy,
)


class AuthenticationManager:
    """飞书API认证管理器"""

    def __init__(
        self, app_id: str, app_secret: str, retry_config: Optional[RetryConfig] = None
    ):
        """
        Initialize authentication manager.

        Args:
            app_id: Feishu app ID
            app_secret: Feishu app secret
            retry_config: Optional retry configuration for authentication failures
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.tenant_access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self._lock = asyncio.Lock()
        self.retry_strategy = RetryStrategy(retry_config or RetryConfig(max_retries=2))

    async def get_tenant_access_token(self) -> str:
        """
        获取tenant_access_token

        Returns:
            Valid tenant access token

        Raises:
            AuthenticationError: If token cannot be obtained
        """
        async with self._lock:
            if self._is_token_expired():
                try:
                    await self._refresh_token()
                except FeishuAPIError as e:
                    raise AuthenticationError(
                        f"Failed to refresh token: {e.message}", error_code=e.code
                    ) from e
            return self.tenant_access_token

    async def refresh_token(self) -> None:
        """
        Public method to force token refresh.

        Raises:
            AuthenticationError: If token cannot be refreshed
        """
        async with self._lock:
            try:
                await self._refresh_token()
            except FeishuAPIError as e:
                raise AuthenticationError(
                    f"Failed to refresh token: {e.message}", error_code=e.code
                ) from e

    async def _refresh_token(self) -> None:
        """
        刷新访问令牌，支持重试机制

        Raises:
            FeishuAPIError: If token refresh fails after all retries
        """
        last_error = None

        for attempt in range(self.retry_strategy.get_max_attempts()):
            try:
                await self._attempt_token_refresh()
                return  # Success, exit retry loop

            except FeishuAPIError as e:
                last_error = e

                # Check if this error should be retried
                if not self.retry_strategy.should_retry(e.code, attempt):
                    raise e

                # If this is not the last attempt, wait before retrying
                if attempt < self.retry_strategy.get_max_attempts() - 1:
                    delay = self.retry_strategy.get_delay(attempt + 1)
                    await asyncio.sleep(delay)

        # If we get here, all retries failed
        if last_error:
            raise last_error
        else:
            raise FeishuAPIError(
                code=-1,
                message="Token refresh failed after all retries",
                http_status=500,
            )

    async def _attempt_token_refresh(self) -> None:
        """
        单次token刷新尝试

        Raises:
            FeishuAPIError: If token refresh attempt fails
        """
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json"}
        data = {"app_id": self.app_id, "app_secret": self.app_secret}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    data=json.dumps(data),
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    response_data = await response.json()

                    if response.status != 200:
                        raise FeishuAPIError(
                            code=response.status,
                            message=f"HTTP {response.status}: {response_data.get('msg', 'Unknown error')}",
                            http_status=response.status,
                        )

                    if response_data.get("code") != 0:
                        error_code = response_data.get("code", -1)
                        error_message = response_data.get("msg", "Unknown error")

                        # Use user-friendly message if available
                        friendly_message = ErrorCodeMapping.get_user_friendly_message(
                            error_code, error_message
                        )

                        raise FeishuAPIError(
                            code=error_code,
                            message=friendly_message,
                            http_status=response.status,
                        )

                    # Extract token and expiration
                    self.tenant_access_token = response_data.get("tenant_access_token")
                    expire_seconds = response_data.get(
                        "expire", 7200
                    )  # Default 2 hours

                    if not self.tenant_access_token:
                        raise FeishuAPIError(
                            code=-1,
                            message="No tenant_access_token in response",
                            http_status=response.status,
                        )

                    # Set expiration time
                    self.token_expires_at = datetime.now() + timedelta(
                        seconds=expire_seconds
                    )

        except aiohttp.ClientError as e:
            # Network errors are typically retryable
            raise FeishuAPIError(
                code=-1, message=f"Network error: {str(e)}", http_status=500
            ) from e
        except json.JSONDecodeError as e:
            # JSON decode errors are typically not retryable
            raise FeishuAPIError(
                code=-2,
                message=f"Invalid JSON response: {str(e)}",
                http_status=response.status if "response" in locals() else 0,
            ) from e

    def _is_token_expired(self) -> bool:
        """
        检查token是否过期

        Returns:
            True if token is expired or doesn't exist
        """
        if not self.tenant_access_token or not self.token_expires_at:
            return True

        # Add 5 minute buffer before expiration
        buffer_time = timedelta(minutes=5)
        return datetime.now() >= (self.token_expires_at - buffer_time)
