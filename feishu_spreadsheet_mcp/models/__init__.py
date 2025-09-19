"""
Data models for Feishu Spreadsheet MCP server.
"""

from .data_models import (
    FeishuAPIError,
    FindResult,
    MCPToolResult,
    RangeData,
    SpreadsheetInfo,
    WorksheetInfo,
    validate_non_negative_int,
    validate_positive_int,
    validate_range_spec,
    validate_token,
    validate_url,
)
from .error_handling import (
    DEFAULT_RETRY_STRATEGY,
    RATE_LIMIT_RETRY_STRATEGY,
    TEMPORARY_ERROR_RETRY_STRATEGY,
    ErrorCategory,
    ErrorCodeMapping,
    RetryConfig,
    RetryStrategy,
)

__all__ = [
    "SpreadsheetInfo",
    "WorksheetInfo",
    "RangeData",
    "FindResult",
    "MCPToolResult",
    "FeishuAPIError",
    "validate_token",
    "validate_url",
    "validate_range_spec",
    "validate_positive_int",
    "validate_non_negative_int",
    "ErrorCategory",
    "ErrorCodeMapping",
    "RetryConfig",
    "RetryStrategy",
    "DEFAULT_RETRY_STRATEGY",
    "RATE_LIMIT_RETRY_STRATEGY",
    "TEMPORARY_ERROR_RETRY_STRATEGY",
]
