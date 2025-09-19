#!/usr/bin/env python3
"""
Simple test for API client to boost coverage.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from feishu_spreadsheet_mcp.services.api_client import FeishuAPIClient, RateLimiter
from feishu_spreadsheet_mcp.services.auth_manager import AuthenticationManager


def test_rate_limiter_init():
    """Test RateLimiter initialization."""
    limiter = RateLimiter(max_requests=50, time_window=30)
    
    assert limiter.max_requests == 50
    assert limiter.time_window == 30
    assert limiter.requests == []


def test_rate_limiter_init_defaults():
    """Test RateLimiter with default values."""
    limiter = RateLimiter()
    
    assert limiter.max_requests == 100
    assert limiter.time_window == 60.0
    assert limiter.requests == []


def test_rate_limiter_get_current_usage_empty():
    """Test rate limiter usage with no requests."""
    limiter = RateLimiter()
    
    usage = limiter.get_current_usage()
    
    assert usage["current_requests"] == 0
    assert usage["max_requests"] == 100
    assert usage["time_window"] == 60.0
    assert usage["usage_percentage"] == 0.0


def test_api_client_init():
    """Test FeishuAPIClient initialization."""
    auth_manager = AuthenticationManager("test_id", "test_secret")
    client = FeishuAPIClient(auth_manager)
    
    assert client.auth_manager == auth_manager
    assert client.base_url == "https://open.feishu.cn/open-apis"
    assert client.session is None
    assert isinstance(client.rate_limiter, RateLimiter)


def test_api_client_init_with_custom_rate_limiter():
    """Test FeishuAPIClient with custom rate limiter."""
    auth_manager = AuthenticationManager("test_id", "test_secret")
    custom_limiter = RateLimiter(max_requests=50)
    client = FeishuAPIClient(auth_manager, rate_limiter=custom_limiter)
    
    assert client.rate_limiter == custom_limiter


def test_api_client_get_rate_limiter_stats():
    """Test getting rate limiter stats."""
    auth_manager = AuthenticationManager("test_id", "test_secret")
    client = FeishuAPIClient(auth_manager)
    
    stats = client.get_rate_limiter_stats()
    
    assert "current_requests" in stats
    assert "max_requests" in stats
    assert "time_window" in stats
    assert "usage_percentage" in stats


@pytest.mark.asyncio
async def test_api_client_context_manager():
    """Test async context manager."""
    auth_manager = AuthenticationManager("test_id", "test_secret")
    
    async with FeishuAPIClient(auth_manager) as client:
        # Should have created a session
        assert client.session is not None
    
    # Session should be closed after context exit
    assert client.session is None


@pytest.mark.asyncio
async def test_api_client_close():
    """Test close method."""
    auth_manager = AuthenticationManager("test_id", "test_secret")
    client = FeishuAPIClient(auth_manager)
    
    # Should not error when no session exists
    await client.close()
    
    # Create session then close
    session = await client._get_session()
    assert client.session is not None
    
    await client.close()
    assert client.session is None


@pytest.mark.asyncio
async def test_prepare_headers_basic():
    """Test basic header preparation."""
    auth_manager = AsyncMock()
    auth_manager.get_tenant_access_token.return_value = "test_token"
    
    client = FeishuAPIClient(auth_manager)
    
    headers = await client._prepare_headers()
    
    assert headers["Content-Type"] == "application/json"
    assert headers["User-Agent"] == "feishu-spreadsheet-mcp/1.0.0"
    assert headers["Authorization"] == "Bearer test_token"


@pytest.mark.asyncio
async def test_prepare_headers_with_additional():
    """Test header preparation with additional headers."""
    auth_manager = AsyncMock()
    auth_manager.get_tenant_access_token.return_value = "test_token"
    
    client = FeishuAPIClient(auth_manager)
    
    additional = {"X-Custom": "custom_value"}
    headers = await client._prepare_headers(additional)
    
    assert headers["X-Custom"] == "custom_value"
    assert headers["Authorization"] == "Bearer test_token"


@pytest.mark.asyncio
async def test_prepare_headers_auth_error():
    """Test header preparation when auth fails."""
    auth_manager = AsyncMock()
    auth_manager.get_tenant_access_token.side_effect = Exception("Auth failed")
    
    client = FeishuAPIClient(auth_manager)
    
    with pytest.raises(Exception, match="Auth failed"):
        await client._prepare_headers()


@pytest.mark.asyncio
async def test_get_session_creates_new():
    """Test _get_session creates new session when none exists."""
    auth_manager = AuthenticationManager("test_id", "test_secret")
    client = FeishuAPIClient(auth_manager)
    
    assert client.session is None
    
    session = await client._get_session()
    
    assert session is not None
    assert client.session is session


@pytest.mark.asyncio
async def test_get_session_returns_existing():
    """Test _get_session returns existing session."""
    auth_manager = AuthenticationManager("test_id", "test_secret")
    client = FeishuAPIClient(auth_manager)
    
    # Create first session
    session1 = await client._get_session()
    
    # Should return same session
    session2 = await client._get_session()
    
    assert session1 is session2


if __name__ == "__main__":
    pytest.main([__file__])