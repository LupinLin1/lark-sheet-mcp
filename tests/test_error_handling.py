"""
Tests for error handling module.
"""

from unittest.mock import patch

from src.models.error_handling import (
    ErrorCategory,
    ErrorCodeMapping,
    RetryConfig,
    RetryStrategy,
    DEFAULT_RETRY_STRATEGY,
    RATE_LIMIT_RETRY_STRATEGY,
    TEMPORARY_ERROR_RETRY_STRATEGY,
)


class TestErrorCategory:
    """Test ErrorCategory enum."""

    def test_error_category_values(self):
        """Test ErrorCategory enum values."""
        assert ErrorCategory.AUTHENTICATION.value == "authentication"
        assert ErrorCategory.PERMISSION.value == "permission"
        assert ErrorCategory.NOT_FOUND.value == "not_found"
        assert ErrorCategory.RATE_LIMIT.value == "rate_limit"
        assert ErrorCategory.TEMPORARY.value == "temporary"
        assert ErrorCategory.PERMANENT.value == "permanent"
        assert ErrorCategory.SERVER_ERROR.value == "server_error"


class TestRetryConfig:
    """Test RetryConfig dataclass."""

    def test_retry_config_defaults(self):
        """Test RetryConfig default values."""
        config = RetryConfig()

        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_retry_config_custom_values(self):
        """Test RetryConfig with custom values."""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=False,
        )

        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.jitter is False


class TestErrorCodeMapping:
    """Test ErrorCodeMapping class."""

    def test_get_error_category_known_codes(self):
        """Test get_error_category with known error codes."""
        assert ErrorCodeMapping.get_error_category(401) == ErrorCategory.AUTHENTICATION
        assert ErrorCodeMapping.get_error_category(1310213) == ErrorCategory.PERMISSION
        assert ErrorCodeMapping.get_error_category(1310214) == ErrorCategory.NOT_FOUND
        assert ErrorCodeMapping.get_error_category(1310217) == ErrorCategory.RATE_LIMIT
        assert ErrorCodeMapping.get_error_category(1310235) == ErrorCategory.TEMPORARY
        assert (
            ErrorCodeMapping.get_error_category(1315201) == ErrorCategory.SERVER_ERROR
        )

    def test_get_error_category_unknown_code(self):
        """Test get_error_category with unknown error code."""
        assert ErrorCodeMapping.get_error_category(9999) == ErrorCategory.PERMANENT

    def test_is_retryable(self):
        """Test is_retryable method."""
        assert ErrorCodeMapping.is_retryable(1310217) is True  # Too Many Request
        assert ErrorCodeMapping.is_retryable(1310235) is True  # Retry Later
        assert ErrorCodeMapping.is_retryable(1310242) is True  # In Mix state
        assert ErrorCodeMapping.is_retryable(1310214) is False  # Not found
        assert ErrorCodeMapping.is_retryable(1310213) is False  # Permission denied

    def test_needs_auth_refresh(self):
        """Test needs_auth_refresh method."""
        assert ErrorCodeMapping.needs_auth_refresh(401) is True
        assert ErrorCodeMapping.needs_auth_refresh(1310213) is False

    def test_is_permanent(self):
        """Test is_permanent method."""
        assert ErrorCodeMapping.is_permanent(1310213) is True  # Permission denied
        assert ErrorCodeMapping.is_permanent(1310214) is True  # Not found
        assert ErrorCodeMapping.is_permanent(1310217) is False  # Rate limit

    def test_get_user_friendly_message(self):
        """Test get_user_friendly_message method."""
        assert (
            ErrorCodeMapping.get_user_friendly_message(1310213, "default")
            == "权限不足，请检查文档权限设置"
        )
        assert (
            ErrorCodeMapping.get_user_friendly_message(1310214, "default")
            == "电子表格不存在或已被删除"
        )
        assert ErrorCodeMapping.get_user_friendly_message(9999, "default") == "default"

    def test_get_retry_config_for_error_rate_limit(self):
        """Test get_retry_config_for_error for rate limit errors."""
        config = ErrorCodeMapping.get_retry_config_for_error(1310217)

        assert config.max_retries == 3
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0

    def test_get_retry_config_for_error_temporary(self):
        """Test get_retry_config_for_error for temporary errors."""
        config = ErrorCodeMapping.get_retry_config_for_error(1310235)

        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0

    def test_get_retry_config_for_error_permanent(self):
        """Test get_retry_config_for_error for permanent errors."""
        config = ErrorCodeMapping.get_retry_config_for_error(1310214)

        assert config.max_retries == 0


class TestRetryStrategy:
    """Test RetryStrategy class."""

    def test_should_retry_within_limit(self):
        """Test should_retry within retry limit."""
        config = RetryConfig(max_retries=3)
        strategy = RetryStrategy(config)

        assert strategy.should_retry(1310217, 0) is True
        assert strategy.should_retry(1310217, 1) is True
        assert strategy.should_retry(1310217, 2) is True

    def test_should_retry_exceed_limit(self):
        """Test should_retry when exceeding retry limit."""
        config = RetryConfig(max_retries=3)
        strategy = RetryStrategy(config)

        assert strategy.should_retry(1310217, 3) is False
        assert strategy.should_retry(1310217, 4) is False

    def test_should_retry_non_retryable_error(self):
        """Test should_retry with non-retryable error."""
        config = RetryConfig(max_retries=3)
        strategy = RetryStrategy(config)

        assert strategy.should_retry(1310214, 0) is False
        assert strategy.should_retry(1310214, 1) is False

    def test_get_delay_first_attempt(self):
        """Test get_delay for first attempt."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        strategy = RetryStrategy(config)

        assert strategy.get_delay(0) == 0

    def test_get_delay_exponential_backoff(self):
        """Test get_delay with exponential backoff."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        strategy = RetryStrategy(config)

        assert strategy.get_delay(1) == 1.0
        assert strategy.get_delay(2) == 2.0
        assert strategy.get_delay(3) == 4.0

    def test_get_delay_max_delay_limit(self):
        """Test get_delay respects max_delay limit."""
        config = RetryConfig(
            base_delay=1.0, exponential_base=2.0, max_delay=3.0, jitter=False
        )
        strategy = RetryStrategy(config)

        assert strategy.get_delay(5) == 3.0  # Should be capped at max_delay

    @patch("random.uniform")
    def test_get_delay_with_jitter(self, mock_uniform):
        """Test get_delay with jitter."""
        mock_uniform.return_value = 0.2  # 20% jitter

        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=True)
        strategy = RetryStrategy(config)

        delay = strategy.get_delay(1)
        expected_jitter = 0.2 * 1.0  # 20% of base delay
        assert delay == 1.0 + expected_jitter

    def test_get_max_attempts(self):
        """Test get_max_attempts method."""
        config = RetryConfig(max_retries=3)
        strategy = RetryStrategy(config)

        assert strategy.get_max_attempts() == 4  # 3 retries + 1 initial attempt


class TestPredefinedStrategies:
    """Test predefined retry strategies."""

    def test_default_retry_strategy(self):
        """Test DEFAULT_RETRY_STRATEGY configuration."""
        assert DEFAULT_RETRY_STRATEGY.config.max_retries == 3
        assert DEFAULT_RETRY_STRATEGY.config.base_delay == 1.0
        assert DEFAULT_RETRY_STRATEGY.config.max_delay == 60.0

    def test_rate_limit_retry_strategy(self):
        """Test RATE_LIMIT_RETRY_STRATEGY configuration."""
        assert RATE_LIMIT_RETRY_STRATEGY.config.max_retries == 5
        assert RATE_LIMIT_RETRY_STRATEGY.config.base_delay == 2.0
        assert RATE_LIMIT_RETRY_STRATEGY.config.max_delay == 120.0

    def test_temporary_error_retry_strategy(self):
        """Test TEMPORARY_ERROR_RETRY_STRATEGY configuration."""
        assert TEMPORARY_ERROR_RETRY_STRATEGY.config.max_retries == 3
        assert TEMPORARY_ERROR_RETRY_STRATEGY.config.base_delay == 1.0
        assert TEMPORARY_ERROR_RETRY_STRATEGY.config.max_delay == 60.0


class TestErrorCodeMappingIntegration:
    """Integration tests for ErrorCodeMapping."""

    def test_all_retryable_errors_have_categories(self):
        """Test that all retryable errors have proper categories."""
        for error_code in ErrorCodeMapping.RETRYABLE_ERRORS:
            category = ErrorCodeMapping.get_error_category(error_code)
            assert category in [ErrorCategory.RATE_LIMIT, ErrorCategory.TEMPORARY, ErrorCategory.AUTHENTICATION, ErrorCategory.SERVER_ERROR]

    def test_all_permanent_errors_have_categories(self):
        """Test that all permanent errors have proper categories."""
        for error_code in ErrorCodeMapping.PERMANENT_ERRORS:
            category = ErrorCodeMapping.get_error_category(error_code)
            assert category in [ErrorCategory.PERMISSION, ErrorCategory.NOT_FOUND]

    def test_auth_refresh_errors_have_categories(self):
        """Test that auth refresh errors have proper categories."""
        for error_code in ErrorCodeMapping.AUTH_REFRESH_ERRORS:
            category = ErrorCodeMapping.get_error_category(error_code)
            assert category == ErrorCategory.AUTHENTICATION

    def test_user_friendly_messages_exist(self):
        """Test that user friendly messages exist for important error codes."""
        important_codes = [1310213, 1310214, 1310215, 1310217, 1310235, 1310242]

        for code in important_codes:
            message = ErrorCodeMapping.get_user_friendly_message(code, "default")
            assert message != "default"
            assert len(message) > 0
