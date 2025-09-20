"""
Tests for authentication manager.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from src.models.data_models import FeishuAPIError
from src.models.error_handling import (
    AuthenticationError,
    RetryConfig,
)
from src.services import AuthenticationManager


class TestAuthenticationManager:
    """Test AuthenticationManager class."""

    def test_init(self):
        """Test AuthenticationManager initialization."""
        auth_manager = AuthenticationManager("test_app_id", "test_app_secret")

        assert auth_manager.app_id == "test_app_id"
        assert auth_manager.app_secret == "test_app_secret"
        assert auth_manager.tenant_access_token is None
        assert auth_manager.token_expires_at is None

    def test_is_token_expired_no_token(self):
        """Test token expiration check when no token exists."""
        auth_manager = AuthenticationManager("test_app_id", "test_app_secret")

        assert auth_manager._is_token_expired() is True

    def test_is_token_expired_no_expiry(self):
        """Test token expiration check when no expiry time exists."""
        auth_manager = AuthenticationManager("test_app_id", "test_app_secret")
        auth_manager.tenant_access_token = "test_token"

        assert auth_manager._is_token_expired() is True

    def test_is_token_expired_valid_token(self):
        """Test token expiration check with valid token."""
        auth_manager = AuthenticationManager("test_app_id", "test_app_secret")
        auth_manager.tenant_access_token = "test_token"
        auth_manager.token_expires_at = datetime.now() + timedelta(hours=1)

        assert auth_manager._is_token_expired() is False

    def test_is_token_expired_expired_token(self):
        """Test token expiration check with expired token."""
        auth_manager = AuthenticationManager("test_app_id", "test_app_secret")
        auth_manager.tenant_access_token = "test_token"
        auth_manager.token_expires_at = datetime.now() - timedelta(hours=1)

        assert auth_manager._is_token_expired() is True

    def test_is_token_expired_near_expiry(self):
        """Test token expiration check with token near expiry (within 5 min buffer)."""
        auth_manager = AuthenticationManager("test_app_id", "test_app_secret")
        auth_manager.tenant_access_token = "test_token"
        # Token expires in 3 minutes (within 5 minute buffer)
        auth_manager.token_expires_at = datetime.now() + timedelta(minutes=3)

        assert auth_manager._is_token_expired() is True

    @pytest.mark.asyncio
    async def test_get_tenant_access_token_valid(self):
        """Test getting valid tenant access token."""
        auth_manager = AuthenticationManager("test_app_id", "test_app_secret")
        auth_manager.tenant_access_token = "valid_token"
        auth_manager.token_expires_at = datetime.now() + timedelta(hours=1)

        token = await auth_manager.get_tenant_access_token()

        assert token == "valid_token"

    @pytest.mark.asyncio
    async def test_get_tenant_access_token_refresh_needed(self):
        """Test getting tenant access token when refresh is needed."""
        auth_manager = AuthenticationManager("test_app_id", "test_app_secret")

        # Mock the _refresh_token method
        with patch.object(
            auth_manager, "_refresh_token", new_callable=AsyncMock
        ) as mock_refresh:
            auth_manager.tenant_access_token = "refreshed_token"

            token = await auth_manager.get_tenant_access_token()

            mock_refresh.assert_called_once()
            assert token == "refreshed_token"

    @pytest.mark.asyncio
    async def test_get_tenant_access_token_concurrent_calls(self):
        """Test concurrent calls to get_tenant_access_token use lock properly."""
        auth_manager = AuthenticationManager("test_app_id", "test_app_secret")

        refresh_call_count = 0

        async def mock_refresh():
            nonlocal refresh_call_count
            refresh_call_count += 1
            auth_manager.tenant_access_token = f"token_{refresh_call_count}"
            auth_manager.token_expires_at = datetime.now() + timedelta(hours=1)

        with patch.object(auth_manager, "_refresh_token", side_effect=mock_refresh):
            # Make concurrent calls
            import asyncio

            results = await asyncio.gather(
                auth_manager.get_tenant_access_token(),
                auth_manager.get_tenant_access_token(),
                auth_manager.get_tenant_access_token(),
            )

            # Should only refresh once due to lock
            assert refresh_call_count == 1
            # All calls should return the same token
            assert all(token == "token_1" for token in results)

    @pytest.mark.asyncio
    async def test_refresh_token_success(self):
        """Test successful token refresh."""
        auth_manager = AuthenticationManager("test_app_id", "test_app_secret")

        # Mock successful API response
        mock_response_data = {
            "code": 0,
            "msg": "ok",
            "tenant_access_token": "t-test_token_123",
            "expire": 7200,
        }

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_post.return_value.__aenter__.return_value = mock_response

            await auth_manager._refresh_token()

            assert auth_manager.tenant_access_token == "t-test_token_123"
            assert auth_manager.token_expires_at is not None
            # Token should expire in approximately 2 hours
            time_diff = auth_manager.token_expires_at - datetime.now()
            assert 7190 <= time_diff.total_seconds() <= 7200

    @pytest.mark.asyncio
    async def test_refresh_token_api_error(self):
        """Test token refresh with API error response."""
        auth_manager = AuthenticationManager("test_app_id", "test_app_secret")

        # Mock API error response
        mock_response_data = {"code": 99991663, "msg": "app not found"}

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_post.return_value.__aenter__.return_value = mock_response

            with pytest.raises(FeishuAPIError) as exc_info:
                await auth_manager._refresh_token()

            assert exc_info.value.code == 99991663
            assert "app not found" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_refresh_token_http_error(self):
        """Test token refresh with HTTP error."""
        auth_manager = AuthenticationManager("test_app_id", "test_app_secret")

        # Mock HTTP error response
        mock_response_data = {"msg": "Bad Request"}

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 400
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_post.return_value.__aenter__.return_value = mock_response

            with pytest.raises(FeishuAPIError) as exc_info:
                await auth_manager._refresh_token()

            assert exc_info.value.code == 400
            assert exc_info.value.http_status == 400

    @pytest.mark.asyncio
    async def test_refresh_token_network_error(self):
        """Test token refresh with network error."""
        auth_manager = AuthenticationManager("test_app_id", "test_app_secret")

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.side_effect = aiohttp.ClientError("Connection failed")

            with pytest.raises(FeishuAPIError) as exc_info:
                await auth_manager._refresh_token()

            assert "Network error" in exc_info.value.message
            assert exc_info.value.code == -1

    @pytest.mark.asyncio
    async def test_refresh_token_invalid_json(self):
        """Test token refresh with invalid JSON response."""
        auth_manager = AuthenticationManager("test_app_id", "test_app_secret")

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(
                side_effect=json.JSONDecodeError("Invalid JSON", "", 0)
            )
            mock_post.return_value.__aenter__.return_value = mock_response

            with pytest.raises(FeishuAPIError) as exc_info:
                await auth_manager._refresh_token()

            assert "Invalid JSON response" in exc_info.value.message
            assert exc_info.value.code == -2

    @pytest.mark.asyncio
    async def test_refresh_token_missing_token(self):
        """Test token refresh with missing token in response."""
        auth_manager = AuthenticationManager("test_app_id", "test_app_secret")

        # Mock response without tenant_access_token
        mock_response_data = {"code": 0, "msg": "ok", "expire": 7200}

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_post.return_value.__aenter__.return_value = mock_response

            with pytest.raises(FeishuAPIError) as exc_info:
                await auth_manager._refresh_token()

            assert "No tenant_access_token in response" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_get_tenant_access_token_authentication_error(self):
        """Test get_tenant_access_token raises AuthenticationError on refresh failure."""
        auth_manager = AuthenticationManager("test_app_id", "test_app_secret")

        with patch.object(
            auth_manager,
            "_refresh_token",
            side_effect=FeishuAPIError(
                code=99991663, message="app not found", http_status=200
            ),
        ):
            with pytest.raises(AuthenticationError) as exc_info:
                await auth_manager.get_tenant_access_token()

            assert "Failed to refresh token" in str(exc_info.value)
            assert exc_info.value.error_code == 99991663

    @pytest.mark.asyncio
    async def test_refresh_token_retry_success_on_second_attempt(self):
        """Test token refresh succeeds on second attempt after network error."""
        auth_manager = AuthenticationManager("test_app_id", "test_app_secret")

        # Mock first attempt fails with network error, second succeeds
        mock_response_data = {
            "code": 0,
            "msg": "ok",
            "tenant_access_token": "t-retry_success_token",
            "expire": 7200,
        }

        call_count = 0

        async def mock_attempt():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise FeishuAPIError(code=-1, message="Network error", http_status=500)
            # Second attempt succeeds
            auth_manager.tenant_access_token = "t-retry_success_token"
            auth_manager.token_expires_at = datetime.now() + timedelta(seconds=7200)

        with patch.object(
            auth_manager, "_attempt_token_refresh", side_effect=mock_attempt
        ):
            await auth_manager._refresh_token()

            assert call_count == 2
            assert auth_manager.tenant_access_token == "t-retry_success_token"

    @pytest.mark.asyncio
    async def test_refresh_token_retry_exhausted(self):
        """Test token refresh fails after exhausting all retries."""
        retry_config = RetryConfig(
            max_retries=2, base_delay=0.01
        )  # Fast retries for testing
        auth_manager = AuthenticationManager(
            "test_app_id", "test_app_secret", retry_config
        )

        call_count = 0

        async def mock_attempt():
            nonlocal call_count
            call_count += 1
            raise FeishuAPIError(code=-1, message="Network error", http_status=500)

        with patch.object(
            auth_manager, "_attempt_token_refresh", side_effect=mock_attempt
        ):
            with pytest.raises(FeishuAPIError) as exc_info:
                await auth_manager._refresh_token()

            assert call_count == 3  # Initial attempt + 2 retries
            assert exc_info.value.code == -1
            assert "Network error" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_refresh_token_no_retry_for_permanent_error(self):
        """Test token refresh doesn't retry for permanent errors."""
        auth_manager = AuthenticationManager("test_app_id", "test_app_secret")

        call_count = 0

        async def mock_attempt():
            nonlocal call_count
            call_count += 1
            raise FeishuAPIError(
                code=99991663, message="app not found", http_status=200
            )

        with patch.object(
            auth_manager, "_attempt_token_refresh", side_effect=mock_attempt
        ):
            with pytest.raises(FeishuAPIError) as exc_info:
                await auth_manager._refresh_token()

            assert call_count == 1  # No retries for permanent error
            assert exc_info.value.code == 99991663

    @pytest.mark.asyncio
    async def test_refresh_token_retry_with_delay(self):
        """Test token refresh respects retry delay."""
        retry_config = RetryConfig(max_retries=1, base_delay=0.1)
        auth_manager = AuthenticationManager(
            "test_app_id", "test_app_secret", retry_config
        )

        call_count = 0
        call_times = []

        async def mock_attempt():
            nonlocal call_count
            call_count += 1
            call_times.append(datetime.now())
            raise FeishuAPIError(code=-1, message="Network error", http_status=500)

        with patch.object(
            auth_manager, "_attempt_token_refresh", side_effect=mock_attempt
        ):
            start_time = datetime.now()

            with pytest.raises(FeishuAPIError):
                await auth_manager._refresh_token()

            end_time = datetime.now()

            assert call_count == 2
            # Should have taken at least the delay time
            assert (end_time - start_time).total_seconds() >= 0.1

    @pytest.mark.asyncio
    async def test_attempt_token_refresh_user_friendly_error(self):
        """Test _attempt_token_refresh uses user-friendly error messages."""
        auth_manager = AuthenticationManager("test_app_id", "test_app_secret")

        # Mock API error response with known error code
        mock_response_data = {
            "code": 1310217,  # Too Many Request
            "msg": "too many requests",
        }

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_post.return_value.__aenter__.return_value = mock_response

            with pytest.raises(FeishuAPIError) as exc_info:
                await auth_manager._attempt_token_refresh()

            # Should use user-friendly message from ErrorCodeMapping
            assert exc_info.value.code == 1310217
            assert "请求过于频繁" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_custom_retry_config(self):
        """Test authentication manager with custom retry configuration."""
        custom_retry_config = RetryConfig(max_retries=5, base_delay=0.01)
        auth_manager = AuthenticationManager(
            "test_app_id", "test_app_secret", custom_retry_config
        )

        assert auth_manager.retry_strategy.config.max_retries == 5
        assert auth_manager.retry_strategy.config.base_delay == 0.01

    @pytest.mark.asyncio
    async def test_refresh_token_fallback_error(self):
        """Test token refresh fallback error when no specific error is caught."""
        auth_manager = AuthenticationManager("test_app_id", "test_app_secret")

        # Mock _attempt_token_refresh to return None (shouldn't happen in practice)
        async def mock_attempt():
            return None

        with patch.object(
            auth_manager, "_attempt_token_refresh", side_effect=mock_attempt
        ):
            # This should trigger the fallback error case
            with patch.object(
                auth_manager.retry_strategy, "get_max_attempts", return_value=0
            ):
                with pytest.raises(FeishuAPIError) as exc_info:
                    await auth_manager._refresh_token()

                assert exc_info.value.code == -1
                assert (
                    "Token refresh failed after all retries" in exc_info.value.message
                )
