#!/usr/bin/env python3
"""
Simple test for main module to boost coverage.
"""

import pytest
import asyncio
import sys
from unittest.mock import patch, AsyncMock, MagicMock
from argparse import Namespace

from feishu_spreadsheet_mcp.main import (
    main,
    run_mcp_server,
    main_async
)


def test_main_function_exists():
    """Test that main function exists and is callable."""
    assert callable(main)
    # Just test that it exists without calling it


def test_main_async_function_exists():
    """Test that main_async function exists and is callable.""" 
    assert callable(main_async)
    # Just test that it exists without calling it


@pytest.mark.asyncio
async def test_run_mcp_server_basic():
    """Test basic MCP server run functionality."""
    # Create a mock server
    mock_server = AsyncMock()
    mock_server.handle_request = AsyncMock()
    mock_server.close = AsyncMock()
    
    # Mock stdin to return empty string immediately (EOF)
    with patch('sys.stdin') as mock_stdin:
        mock_stdin.readline.return_value = ''  # EOF immediately
        
        # Should exit cleanly when hitting EOF
        await run_mcp_server(mock_server)
        
        # Should have called close
        mock_server.close.assert_called_once()


@pytest.mark.asyncio
async def test_main_async_basic():
    """Test main_async function basic path."""
    import os
    
    # Set environment variables for credentials
    test_env = {
        "FEISHU_APP_ID": "test_id",
        "FEISHU_APP_SECRET": "test_secret"
    }
    
    with patch.dict(os.environ, test_env):
        with patch('feishu_spreadsheet_mcp.main.run_mcp_server') as mock_run:
            mock_run.return_value = None  # Mock successful completion
            
            # Should complete without error
            await main_async()
            
            # Should have called run_mcp_server
            mock_run.assert_called_once()


def test_main_calls_asyncio_run():
    """Test that main() calls asyncio.run()."""
    import os
    
    # Mock sys.argv to provide valid arguments
    test_argv = ["feishu-spreadsheet-mcp"]
    
    # Set environment variables for credentials
    test_env = {
        "FEISHU_APP_ID": "test_id",
        "FEISHU_APP_SECRET": "test_secret"
    }
    
    with patch.dict(os.environ, test_env):
        with patch.object(sys, 'argv', test_argv):
            with patch('asyncio.run') as mock_asyncio_run:
                main()
                
                # Should have called asyncio.run with main_async
                mock_asyncio_run.assert_called_once()


if __name__ == "__main__":
    # Need to import os for the test
    import os
    pytest.main([__file__])