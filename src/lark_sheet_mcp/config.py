"""
Configuration management for Feishu Spreadsheet MCP server.
"""

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    """服务器配置"""

    app_id: str
    app_secret: str
    log_level: str = "INFO"
    host: str = "localhost"
    port: int = 8000
    max_retries: int = 3
    timeout: int = 30
    rate_limit_requests: int = 100
    rate_limit_window: float = 60.0


class ConfigurationManager:
    """配置管理器"""

    def __init__(self):
        """初始化配置管理器"""
        self.config: Optional[ServerConfig] = None
        self._config_files = [
            "feishu_mcp_config.json",
            "~/.feishu_mcp_config.json",
            "/etc/feishu_mcp/config.json",
        ]

    def load_config(
        self,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        config_file: Optional[str] = None,
    ) -> ServerConfig:
        """
        加载配置

        Args:
            app_id: 命令行指定的app_id，优先级最高
            app_secret: 命令行指定的app_secret，优先级最高
            config_file: 指定配置文件路径

        Returns:
            ServerConfig: 服务器配置对象

        Raises:
            ValueError: 如果必需配置缺失
        """
        config_data = {}

        # 1. 首先尝试从配置文件加载
        if config_file:
            config_files = [config_file]
        else:
            config_files = self._config_files

        for file_path in config_files:
            expanded_path = Path(file_path).expanduser()
            if expanded_path.exists():
                try:
                    with open(expanded_path, "r", encoding="utf-8") as f:
                        file_config = json.load(f)
                        config_data.update(file_config)
                        logger.info(f"Loaded configuration from {expanded_path}")
                        break
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Failed to load config from {expanded_path}: {e}")
                    continue

        # 2. 从环境变量加载，会覆盖配置文件中的值
        env_config = self._load_from_env()
        config_data.update(env_config)

        # 3. 命令行参数具有最高优先级
        if app_id:
            config_data["app_id"] = app_id
        if app_secret:
            config_data["app_secret"] = app_secret

        # 4. 验证必需配置
        if not config_data.get("app_id"):
            raise ValueError(
                "app_id is required. Set it via command line argument, "
                "environment variable FEISHU_APP_ID, or configuration file."
            )

        if not config_data.get("app_secret"):
            raise ValueError(
                "app_secret is required. Set it via command line argument, "
                "environment variable FEISHU_APP_SECRET, or configuration file."
            )

        # 5. 创建配置对象
        self.config = ServerConfig(
            app_id=config_data["app_id"],
            app_secret=config_data["app_secret"],
            log_level=config_data.get("log_level", "INFO"),
            host=config_data.get("host", "localhost"),
            port=int(config_data.get("port", 8000)),
            max_retries=int(config_data.get("max_retries", 3)),
            timeout=int(config_data.get("timeout", 30)),
            rate_limit_requests=int(config_data.get("rate_limit_requests", 100)),
            rate_limit_window=float(config_data.get("rate_limit_window", 60.0)),
        )

        return self.config

    def _load_from_env(self) -> Dict[str, Any]:
        """从环境变量加载配置"""
        env_config = {}

        # 映射环境变量到配置项
        env_mapping = {
            "FEISHU_APP_ID": "app_id",
            "FEISHU_APP_SECRET": "app_secret",
            "FEISHU_LOG_LEVEL": "log_level",
            "FEISHU_HOST": "host",
            "FEISHU_PORT": "port",
            "FEISHU_MAX_RETRIES": "max_retries",
            "FEISHU_TIMEOUT": "timeout",
            "FEISHU_RATE_LIMIT_REQUESTS": "rate_limit_requests",
            "FEISHU_RATE_LIMIT_WINDOW": "rate_limit_window",
        }

        for env_key, config_key in env_mapping.items():
            value = os.getenv(env_key)
            if value:
                env_config[config_key] = value
                logger.debug(f"Loaded {config_key} from environment variable {env_key}")

        return env_config

    def validate_config(self) -> bool:
        """
        验证配置的有效性

        Returns:
            bool: 配置是否有效
        """
        if not self.config:
            return False

        # 验证必需字段
        if not self.config.app_id or not self.config.app_secret:
            return False

        # 验证数值范围
        if self.config.port < 1 or self.config.port > 65535:
            logger.error(f"Invalid port number: {self.config.port}")
            return False

        if self.config.max_retries < 0:
            logger.error(f"Invalid max_retries: {self.config.max_retries}")
            return False

        if self.config.timeout <= 0:
            logger.error(f"Invalid timeout: {self.config.timeout}")
            return False

        if self.config.rate_limit_requests <= 0:
            logger.error(
                f"Invalid rate_limit_requests: {self.config.rate_limit_requests}"
            )
            return False

        if self.config.rate_limit_window <= 0:
            logger.error(f"Invalid rate_limit_window: {self.config.rate_limit_window}")
            return False

        # 验证日志级别
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.config.log_level.upper() not in valid_log_levels:
            logger.error(f"Invalid log_level: {self.config.log_level}")
            return False

        return True

    def setup_logging(self) -> None:
        """设置日志配置"""
        if not self.config:
            return

        # 配置根日志记录器
        logging.basicConfig(
            level=getattr(logging, self.config.log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(),
            ],
        )

        # 设置特定模块的日志级别
        logging.getLogger("feishu_spreadsheet_mcp").setLevel(
            getattr(logging, self.config.log_level.upper())
        )
        logging.getLogger("aiohttp").setLevel(logging.WARNING)

        logger.info(f"Logging configured with level: {self.config.log_level}")

    def get_config(self) -> Optional[ServerConfig]:
        """获取当前配置"""
        return self.config

    def create_sample_config(self, file_path: str = "feishu_mcp_config.json") -> None:
        """
        创建示例配置文件

        Args:
            file_path: 配置文件路径
        """
        sample_config = {
            "app_id": "your_feishu_app_id",
            "app_secret": "your_feishu_app_secret",
            "log_level": "INFO",
            "host": "localhost",
            "port": 8000,
            "max_retries": 3,
            "timeout": 30,
            "rate_limit_requests": 100,
            "rate_limit_window": 60.0,
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(sample_config, f, indent=2, ensure_ascii=False)
            logger.info(f"Sample configuration file created at: {file_path}")
        except IOError as e:
            logger.error(f"Failed to create sample config file: {e}")
            raise


# 全局配置管理器实例
config_manager = ConfigurationManager()
