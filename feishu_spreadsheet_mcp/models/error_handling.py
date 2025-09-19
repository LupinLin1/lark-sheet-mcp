"""
Error handling and retry strategy configuration for Feishu API.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Set


class AuthenticationError(Exception):
    """认证错误异常"""

    def __init__(self, message: str, error_code: int = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class ErrorCategory(Enum):
    """飞书API错误分类"""

    AUTHENTICATION = "authentication"  # 认证错误
    PERMISSION = "permission"  # 权限错误
    NOT_FOUND = "not_found"  # 资源不存在
    RATE_LIMIT = "rate_limit"  # 频率限制
    TEMPORARY = "temporary"  # 临时错误
    PERMANENT = "permanent"  # 永久错误
    SERVER_ERROR = "server_error"  # 服务器错误


@dataclass
class RetryConfig:
    """重试配置"""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True  # 添加随机抖动


class ErrorCodeMapping:
    """飞书API错误码映射和分类"""

    # 错误码到错误分类的映射
    ERROR_CATEGORIES: Dict[int, ErrorCategory] = {
        # 认证错误
        401: ErrorCategory.AUTHENTICATION,
        # 权限错误
        1310213: ErrorCategory.PERMISSION,
        1061004: ErrorCategory.PERMISSION,
        # 资源不存在错误
        1310214: ErrorCategory.NOT_FOUND,
        1310215: ErrorCategory.NOT_FOUND,
        # 频率限制错误
        1310217: ErrorCategory.RATE_LIMIT,
        # 临时错误
        1310235: ErrorCategory.TEMPORARY,
        1310242: ErrorCategory.TEMPORARY,
        # 服务器错误
        1315201: ErrorCategory.SERVER_ERROR,
        1315203: ErrorCategory.SERVER_ERROR,
        # HTTP 服务器错误
        -1: ErrorCategory.SERVER_ERROR,  # Network errors (custom code)
        500: ErrorCategory.SERVER_ERROR,  # Internal Server Error
        502: ErrorCategory.SERVER_ERROR,  # Bad Gateway
        503: ErrorCategory.SERVER_ERROR,  # Service Unavailable
        504: ErrorCategory.SERVER_ERROR,  # Gateway Timeout
    }

    # 可重试的错误码
    RETRYABLE_ERRORS: Set[int] = {
        401,  # Unauthorized (can retry after token refresh)
        1310217,  # Too Many Request
        1310235,  # Retry Later
        1310242,  # In Mix state
        -1,  # Network errors (custom code)
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
    }

    # 需要认证刷新的错误码
    AUTH_REFRESH_ERRORS: Set[int] = {401}

    # 永久性错误码（不应重试）
    PERMANENT_ERRORS: Set[int] = {
        1310213,  # 权限不足
        1310214,  # 电子表格不存在
        1310215,  # 工作表不存在
        1061004,  # 权限不足
    }

    # 用户友好的错误消息映射
    USER_FRIENDLY_MESSAGES: Dict[int, str] = {
        1310213: "权限不足，请检查文档权限设置",
        1310214: "电子表格不存在或已被删除",
        1310215: "工作表不存在",
        1310217: "请求过于频繁，请稍后重试",
        1310235: "服务繁忙，请稍后重试",
        1310242: "数据正在恢复中，请稍后重试",
        1315201: "服务内部错误，请联系客服",
        1315203: "服务内部错误，请联系客服",
        1061004: "权限不足，请检查文档权限设置",
    }

    @classmethod
    def get_error_category(cls, error_code: int) -> ErrorCategory:
        """获取错误分类"""
        return cls.ERROR_CATEGORIES.get(error_code, ErrorCategory.PERMANENT)

    @classmethod
    def is_retryable(cls, error_code: int) -> bool:
        """判断错误是否可重试"""
        return error_code in cls.RETRYABLE_ERRORS

    @classmethod
    def needs_auth_refresh(cls, error_code: int) -> bool:
        """判断是否需要刷新认证"""
        return error_code in cls.AUTH_REFRESH_ERRORS

    @classmethod
    def is_permanent(cls, error_code: int) -> bool:
        """判断是否为永久性错误"""
        return error_code in cls.PERMANENT_ERRORS

    @classmethod
    def get_user_friendly_message(cls, error_code: int, default_message: str) -> str:
        """获取用户友好的错误消息"""
        return cls.USER_FRIENDLY_MESSAGES.get(error_code, default_message)

    @classmethod
    def get_retry_config_for_error(cls, error_code: int) -> RetryConfig:
        """根据错误码获取重试配置"""
        category = cls.get_error_category(error_code)

        if category == ErrorCategory.RATE_LIMIT:
            # 频率限制错误使用更长的延迟
            return RetryConfig(
                max_retries=3,
                base_delay=2.0,
                max_delay=120.0,
                exponential_base=2.0,
                jitter=True,
            )
        elif category == ErrorCategory.TEMPORARY:
            # 临时错误使用标准重试配置
            return RetryConfig(
                max_retries=3,
                base_delay=1.0,
                max_delay=60.0,
                exponential_base=2.0,
                jitter=True,
            )
        else:
            # 其他错误不重试
            return RetryConfig(max_retries=0)


class RetryStrategy:
    """重试策略实现"""

    def __init__(self, config: RetryConfig):
        self.config = config

    def should_retry(self, error_code: int, attempt: int) -> bool:
        """判断是否应该重试"""
        if attempt >= self.config.max_retries:
            return False

        return ErrorCodeMapping.is_retryable(error_code)

    def get_delay(self, attempt: int) -> float:
        """计算重试延迟时间"""
        import random

        if attempt <= 0:
            return 0

        # 指数退避
        delay = self.config.base_delay * (self.config.exponential_base ** (attempt - 1))

        # 限制最大延迟
        delay = min(delay, self.config.max_delay)

        # 添加随机抖动
        if self.config.jitter:
            jitter = random.uniform(0.1, 0.3) * delay
            delay += jitter

        return delay

    def get_max_attempts(self) -> int:
        """获取最大尝试次数"""
        return self.config.max_retries + 1  # 包括初始尝试


class MCPError(Exception):
    """MCP协议错误"""

    def __init__(self, code: int, message: str, data: any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


# 预定义的重试策略
DEFAULT_RETRY_STRATEGY = RetryStrategy(RetryConfig())
RATE_LIMIT_RETRY_STRATEGY = RetryStrategy(
    RetryConfig(max_retries=5, base_delay=2.0, max_delay=120.0)
)
TEMPORARY_ERROR_RETRY_STRATEGY = RetryStrategy(
    RetryConfig(max_retries=3, base_delay=1.0, max_delay=60.0)
)
