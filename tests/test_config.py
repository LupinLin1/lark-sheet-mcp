"""
Tests for configuration management.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.config import ConfigurationManager, ServerConfig


class TestServerConfig:
    """Test ServerConfig dataclass."""

    def test_server_config_defaults(self):
        """Test ServerConfig with default values."""
        config = ServerConfig(app_id="test_id", app_secret="test_secret")
        
        assert config.app_id == "test_id"
        assert config.app_secret == "test_secret"
        assert config.log_level == "INFO"
        assert config.host == "localhost"
        assert config.port == 8000
        assert config.max_retries == 3
        assert config.timeout == 30
        assert config.rate_limit_requests == 100
        assert config.rate_limit_window == 60.0

    def test_server_config_custom_values(self):
        """Test ServerConfig with custom values."""
        config = ServerConfig(
            app_id="custom_id",
            app_secret="custom_secret",
            log_level="DEBUG",
            host="0.0.0.0",
            port=9000,
            max_retries=5,
            timeout=60,
            rate_limit_requests=200,
            rate_limit_window=120.0
        )
        
        assert config.app_id == "custom_id"
        assert config.app_secret == "custom_secret"
        assert config.log_level == "DEBUG"
        assert config.host == "0.0.0.0"
        assert config.port == 9000
        assert config.max_retries == 5
        assert config.timeout == 60
        assert config.rate_limit_requests == 200
        assert config.rate_limit_window == 120.0


class TestConfigurationManager:
    """Test ConfigurationManager class."""

    def test_init(self):
        """Test ConfigurationManager initialization."""
        manager = ConfigurationManager()
        
        assert manager.config is None
        assert len(manager._config_files) == 3

    def test_load_config_from_args(self):
        """Test loading config from command line arguments."""
        manager = ConfigurationManager()
        
        config = manager.load_config(app_id="cli_id", app_secret="cli_secret")
        
        assert config.app_id == "cli_id"
        assert config.app_secret == "cli_secret"
        assert config.log_level == "INFO"  # default

    def test_load_config_from_env(self):
        """Test loading config from environment variables."""
        manager = ConfigurationManager()
        
        with patch.dict(os.environ, {
            "FEISHU_APP_ID": "env_id",
            "FEISHU_APP_SECRET": "env_secret",
            "FEISHU_LOG_LEVEL": "DEBUG",
            "FEISHU_PORT": "9000",
            "FEISHU_MAX_RETRIES": "5"
        }):
            config = manager.load_config()
            
            assert config.app_id == "env_id"
            assert config.app_secret == "env_secret"
            assert config.log_level == "DEBUG"
            assert config.port == 9000
            assert config.max_retries == 5

    def test_load_config_from_file(self):
        """Test loading config from JSON file."""
        manager = ConfigurationManager()
        
        config_data = {
            "app_id": "file_id",
            "app_secret": "file_secret",
            "log_level": "WARNING",
            "port": 8080,
            "timeout": 45
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = manager.load_config(config_file=temp_path)
            
            assert config.app_id == "file_id"
            assert config.app_secret == "file_secret"
            assert config.log_level == "WARNING"
            assert config.port == 8080
            assert config.timeout == 45
        finally:
            os.unlink(temp_path)

    def test_load_config_priority(self):
        """Test configuration priority: CLI > env > file."""
        manager = ConfigurationManager()
        
        # Create config file
        config_data = {
            "app_id": "file_id",
            "app_secret": "file_secret",
            "log_level": "WARNING"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            with patch.dict(os.environ, {
                "FEISHU_APP_ID": "env_id",
                "FEISHU_LOG_LEVEL": "DEBUG"
            }):
                # CLI args should override everything
                config = manager.load_config(
                    app_id="cli_id",
                    config_file=temp_path
                )
                
                assert config.app_id == "cli_id"  # CLI wins
                assert config.app_secret == "file_secret"  # From file
                assert config.log_level == "DEBUG"  # Env wins over file
        finally:
            os.unlink(temp_path)

    def test_load_config_missing_app_id(self):
        """Test error when app_id is missing."""
        manager = ConfigurationManager()
        
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="app_id is required"):
                manager.load_config()

    def test_load_config_missing_app_secret(self):
        """Test error when app_secret is missing."""
        manager = ConfigurationManager()
        
        with patch.dict(os.environ, {"FEISHU_APP_ID": "test_id"}, clear=True):
            with pytest.raises(ValueError, match="app_secret is required"):
                manager.load_config()

    def test_load_config_invalid_json(self):
        """Test handling of invalid JSON config file."""
        manager = ConfigurationManager()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_path = f.name
        
        try:
            # Should still work with env vars, just ignore the bad config file
            with patch.dict(os.environ, {
                "FEISHU_APP_ID": "env_id",
                "FEISHU_APP_SECRET": "env_secret"
            }):
                config = manager.load_config(config_file=temp_path)
                assert config.app_id == "env_id"
                assert config.app_secret == "env_secret"
        finally:
            os.unlink(temp_path)

    def test_validate_config_success(self):
        """Test successful config validation."""
        manager = ConfigurationManager()
        manager.config = ServerConfig(app_id="test_id", app_secret="test_secret")
        
        assert manager.validate_config() is True

    def test_validate_config_no_config(self):
        """Test validation with no config loaded."""
        manager = ConfigurationManager()
        
        assert manager.validate_config() is False

    def test_validate_config_missing_fields(self):
        """Test validation with missing required fields."""
        manager = ConfigurationManager()
        manager.config = ServerConfig(app_id="", app_secret="test_secret")
        
        assert manager.validate_config() is False

    def test_validate_config_invalid_port(self):
        """Test validation with invalid port."""
        manager = ConfigurationManager()
        manager.config = ServerConfig(
            app_id="test_id",
            app_secret="test_secret",
            port=70000  # Invalid port
        )
        
        assert manager.validate_config() is False

    def test_validate_config_invalid_log_level(self):
        """Test validation with invalid log level."""
        manager = ConfigurationManager()
        manager.config = ServerConfig(
            app_id="test_id",
            app_secret="test_secret",
            log_level="INVALID"
        )
        
        assert manager.validate_config() is False

    def test_setup_logging(self):
        """Test logging setup."""
        manager = ConfigurationManager()
        manager.config = ServerConfig(
            app_id="test_id",
            app_secret="test_secret",
            log_level="DEBUG"
        )
        
        # Should not raise any exceptions
        manager.setup_logging()

    def test_setup_logging_no_config(self):
        """Test logging setup with no config."""
        manager = ConfigurationManager()
        
        # Should not raise any exceptions
        manager.setup_logging()

    def test_get_config(self):
        """Test getting current config."""
        manager = ConfigurationManager()
        
        assert manager.get_config() is None
        
        config = ServerConfig(app_id="test_id", app_secret="test_secret")
        manager.config = config
        
        assert manager.get_config() == config

    def test_create_sample_config(self):
        """Test creating sample configuration file."""
        manager = ConfigurationManager()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            manager.create_sample_config(temp_path)
            
            # Verify file was created and has correct content
            with open(temp_path, 'r') as f:
                sample_config = json.load(f)
            
            assert sample_config["app_id"] == "your_feishu_app_id"
            assert sample_config["app_secret"] == "your_feishu_app_secret"
            assert sample_config["log_level"] == "INFO"
            assert sample_config["port"] == 8000
        finally:
            os.unlink(temp_path)

    def test_create_sample_config_io_error(self):
        """Test creating sample config with IO error."""
        manager = ConfigurationManager()
        
        # Try to write to an invalid path
        with pytest.raises(IOError):
            manager.create_sample_config("/invalid/path/config.json")