"""
Tests for main entry point.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from src.main import main, main_async


class TestMainAsync:
    """Test async main function."""

    @pytest.mark.asyncio
    async def test_main_async_with_params(self):
        """Test main_async with provided parameters."""
        with patch("src.main.run_server") as mock_run_server:
            await main_async("test_app_id", "test_app_secret")
            mock_run_server.assert_called_once_with("test_app_id", "test_app_secret", None)

    @pytest.mark.asyncio
    async def test_main_async_with_config_file(self):
        """Test main_async with config file."""
        with patch("src.main.run_server") as mock_run_server:
            await main_async(config_file="test_config.json")
            mock_run_server.assert_called_once_with(None, None, "test_config.json")

    @pytest.mark.asyncio
    async def test_main_async_invalid_config(self):
        """Test main_async with invalid configuration."""
        with patch("src.main.config_manager") as mock_config_manager:
            mock_config_manager.load_config.return_value = MagicMock()
            mock_config_manager.validate_config.return_value = False
            
            with pytest.raises(ValueError, match="Invalid configuration"):
                await main_async()

    @pytest.mark.asyncio 
    async def test_main_async_config_error(self):
        """Test main_async with configuration loading error."""
        with patch("src.main.config_manager") as mock_config_manager:
            mock_config_manager.load_config.side_effect = ValueError("Missing app_id")
            
            with pytest.raises(ValueError):
                await main_async()


class TestMain:
    """Test main entry point function."""

    def test_main_function_exists(self):
        """Test that main function exists."""
        assert callable(main)

    @patch("src.main.run_server")
    @patch("src.main.argparse.ArgumentParser")
    def test_main_with_args(self, mock_parser, mock_run_server):
        """Test main function with command line arguments."""
        # Mock argument parser
        mock_args = mock_parser.return_value.parse_args.return_value
        mock_args.app_id = "cli_app_id"
        mock_args.app_secret = "cli_app_secret"
        mock_args.config = None
        mock_args.create_config = None
        mock_args.log_level = None

        main()

        mock_run_server.assert_called_once_with("cli_app_id", "cli_app_secret", None)

    @patch("src.main.run_server")
    @patch("src.main.argparse.ArgumentParser")
    def test_main_no_args(self, mock_parser, mock_run_server):
        """Test main function without command line arguments."""
        # Mock argument parser with no args
        mock_args = mock_parser.return_value.parse_args.return_value
        mock_args.app_id = None
        mock_args.app_secret = None
        mock_args.config = None
        mock_args.create_config = None
        mock_args.log_level = None

        main()

        mock_run_server.assert_called_once_with(None, None, None)

    @patch("src.main.sys.exit")
    @patch("src.main.config_manager")
    @patch("src.main.argparse.ArgumentParser")
    def test_main_create_config(self, mock_parser, mock_config_manager, mock_exit):
        """Test main function with create-config option."""
        mock_args = mock_parser.return_value.parse_args.return_value
        mock_args.create_config = "test_config.json"
        mock_args.app_id = None
        mock_args.app_secret = None
        mock_args.config = None
        mock_args.log_level = None

        # Make sys.exit actually raise SystemExit to stop execution
        mock_exit.side_effect = SystemExit

        with pytest.raises(SystemExit):
            main()

        mock_config_manager.create_sample_config.assert_called_once_with("test_config.json")
        mock_exit.assert_called_once_with(0)

    @patch("src.main.sys.exit")
    @patch("src.main.run_server")
    @patch("src.main.argparse.ArgumentParser")
    def test_main_config_error(self, mock_parser, mock_run_server, mock_exit):
        """Test main function with configuration error."""
        mock_args = mock_parser.return_value.parse_args.return_value
        mock_args.app_id = None
        mock_args.app_secret = None
        mock_args.config = None
        mock_args.create_config = None
        mock_args.log_level = None

        # Mock run_server to raise ValueError
        mock_run_server.side_effect = ValueError("Configuration error")

        main()

        mock_exit.assert_called_once_with(1)

    @patch("src.main.sys.exit")
    @patch("src.main.run_server")
    @patch("src.main.argparse.ArgumentParser")
    def test_main_keyboard_interrupt(self, mock_parser, mock_run_server, mock_exit):
        """Test main function with keyboard interrupt."""
        mock_args = mock_parser.return_value.parse_args.return_value
        mock_args.app_id = None
        mock_args.app_secret = None
        mock_args.config = None
        mock_args.create_config = None
        mock_args.log_level = None

        # Mock run_server to raise KeyboardInterrupt
        mock_run_server.side_effect = KeyboardInterrupt()

        main()

        mock_exit.assert_called_once_with(0)