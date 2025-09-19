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
    validate_token,
    validate_url,
    validate_range_spec,
    validate_positive_int,
    validate_non_negative_int,
)
from .error_handling import (
    ErrorCategory,
    ErrorCodeMapping,
    RetryConfig,
    RetryStrategy,
    DEFAULT_RETRY_STRATEGY,
    RATE_LIMIT_RETRY_STRATEGY,
    TEMPORARY_ERROR_RETRY_STRATEGY,
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
