"""
Core data models for Feishu Spreadsheet MCP server.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


def validate_token(token: str) -> str:
    """验证token格式"""
    if not token or not isinstance(token, str):
        raise ValueError("Token must be a non-empty string")
    if len(token.strip()) == 0:
        raise ValueError("Token cannot be empty or whitespace only")
    return token.strip()


def validate_url(url: str) -> str:
    """验证URL格式"""
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")
    return url


def validate_range_spec(range_spec: str) -> str:
    """验证范围规格格式，如 'sheetId!A1:B10'"""
    if not range_spec or not isinstance(range_spec, str):
        raise ValueError("Range specification must be a non-empty string")

    range_spec = range_spec.strip()

    # 检查是否包含工作表ID和范围
    if "!" not in range_spec:
        raise ValueError(
            "Range specification must include sheet ID (format: 'sheetId!A1:B10')"
        )

    sheet_id, range_part = range_spec.split("!", 1)

    if not sheet_id:
        raise ValueError("Sheet ID cannot be empty")

    if not range_part:
        raise ValueError("Range part cannot be empty")

    # 验证范围格式 (简单验证，支持 A1:B10 或 A1 格式)
    range_pattern = r"^[A-Z]+\d+(:[A-Z]+\d+)?$"
    if not re.match(range_pattern, range_part):
        raise ValueError(
            f"Invalid range format: {range_part}. Expected format like 'A1:B10' or 'A1'"
        )

    return range_spec


def validate_positive_int(value: int, field_name: str) -> int:
    """验证正整数"""
    if not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value


def validate_non_negative_int(value: int, field_name: str) -> int:
    """验证非负整数"""
    if not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value


@dataclass
class SpreadsheetInfo:
    """电子表格信息"""

    token: str
    name: str
    type: str  # "sheet"
    url: str
    created_time: datetime
    modified_time: datetime
    owner_id: str

    def __post_init__(self):
        """数据验证"""
        self.token = validate_token(self.token)

        if not self.name or not isinstance(self.name, str):
            raise ValueError("Name must be a non-empty string")
        self.name = self.name.strip()

        if self.type != "sheet":
            raise ValueError("Type must be 'sheet'")

        self.url = validate_url(self.url)

        if not isinstance(self.created_time, datetime):
            raise ValueError("Created time must be a datetime object")

        if not isinstance(self.modified_time, datetime):
            raise ValueError("Modified time must be a datetime object")

        if not self.owner_id or not isinstance(self.owner_id, str):
            raise ValueError("Owner ID must be a non-empty string")
        self.owner_id = self.owner_id.strip()

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "SpreadsheetInfo":
        """从飞书API响应创建实例"""
        try:
            return cls(
                token=data["token"],
                name=data["name"],
                type=data["type"],
                url=data["url"],
                created_time=datetime.fromisoformat(
                    data["created_time"].replace("Z", "+00:00")
                ),
                modified_time=datetime.fromisoformat(
                    data["modified_time"].replace("Z", "+00:00")
                ),
                owner_id=data["owner_id"],
            )
        except KeyError as e:
            raise ValueError(f"Missing required field in API response: {e}")
        except ValueError as e:
            raise ValueError(f"Invalid data format in API response: {e}")


@dataclass
class WorksheetInfo:
    """工作表信息"""

    sheet_id: str
    title: str
    index: int
    hidden: bool
    row_count: int
    column_count: int
    frozen_row_count: int
    frozen_column_count: int
    resource_type: str
    merges: Optional[List[Dict]] = None

    def __post_init__(self):
        """数据验证"""
        self.sheet_id = validate_token(self.sheet_id)

        if not self.title or not isinstance(self.title, str):
            raise ValueError("Title must be a non-empty string")
        self.title = self.title.strip()

        self.index = validate_non_negative_int(self.index, "Index")

        if not isinstance(self.hidden, bool):
            raise ValueError("Hidden must be a boolean")

        self.row_count = validate_positive_int(self.row_count, "Row count")
        self.column_count = validate_positive_int(self.column_count, "Column count")
        self.frozen_row_count = validate_non_negative_int(
            self.frozen_row_count, "Frozen row count"
        )
        self.frozen_column_count = validate_non_negative_int(
            self.frozen_column_count, "Frozen column count"
        )

        if not self.resource_type or not isinstance(self.resource_type, str):
            raise ValueError("Resource type must be a non-empty string")
        self.resource_type = self.resource_type.strip()

        if self.merges is not None:
            if not isinstance(self.merges, list):
                raise ValueError("Merges must be a list or None")
            for merge in self.merges:
                if not isinstance(merge, dict):
                    raise ValueError("Each merge must be a dictionary")

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "WorksheetInfo":
        """从飞书API响应创建实例"""
        try:
            # Extract grid properties - handle both direct fields and nested grid_properties
            grid_props = data.get("grid_properties", {})

            # Try to get from direct fields first, then from grid_properties
            row_count = data.get("row_count", grid_props.get("row_count", 0))
            column_count = data.get("column_count", grid_props.get("column_count", 0))
            frozen_row_count = data.get(
                "frozen_row_count", grid_props.get("frozen_row_count", 0)
            )
            frozen_column_count = data.get(
                "frozen_column_count", grid_props.get("frozen_column_count", 0)
            )

            return cls(
                sheet_id=data["sheet_id"],
                title=data["title"],
                index=data["index"],
                hidden=data.get("hidden", False),
                row_count=row_count,
                column_count=column_count,
                frozen_row_count=frozen_row_count,
                frozen_column_count=frozen_column_count,
                resource_type=data["resource_type"],
                merges=data.get("merges"),
            )
        except KeyError as e:
            raise ValueError(f"Missing required field in API response: {e}")
        except ValueError as e:
            raise ValueError(f"Invalid data format in API response: {e}")


@dataclass
class RangeData:
    """范围数据"""

    range: str
    major_dimension: str  # "ROWS"
    values: List[List[Any]]
    revision: int

    def __post_init__(self):
        """数据验证"""
        self.range = validate_range_spec(self.range)

        if self.major_dimension not in ["ROWS", "COLUMNS"]:
            raise ValueError("Major dimension must be 'ROWS' or 'COLUMNS'")

        if not isinstance(self.values, list):
            raise ValueError("Values must be a list")

        for i, row in enumerate(self.values):
            if not isinstance(row, list):
                raise ValueError(f"Row {i} must be a list")

        self.revision = validate_non_negative_int(self.revision, "Revision")

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "RangeData":
        """从飞书API响应创建实例"""
        try:
            return cls(
                range=data["range"],
                major_dimension=data.get("majorDimension", "ROWS"),
                values=data.get("values", []),
                revision=data["revision"],
            )
        except KeyError as e:
            raise ValueError(f"Missing required field in API response: {e}")
        except ValueError as e:
            raise ValueError(f"Invalid data format in API response: {e}")

    def get_cell_value(self, row: int, col: int) -> Any:
        """获取指定位置的单元格值"""
        if row < 0 or col < 0:
            raise ValueError("Row and column indices must be non-negative")

        if row >= len(self.values):
            return None

        if col >= len(self.values[row]):
            return None

        return self.values[row][col]

    def is_empty(self) -> bool:
        """检查范围数据是否为空"""
        return len(self.values) == 0 or all(len(row) == 0 for row in self.values)


@dataclass
class FindResult:
    """查找结果"""

    matched_cells: List[str]
    matched_formula_cells: List[str]
    rows_count: int

    def __post_init__(self):
        """数据验证"""
        if not isinstance(self.matched_cells, list):
            raise ValueError("Matched cells must be a list")

        for cell in self.matched_cells:
            if not isinstance(cell, str):
                raise ValueError("Each matched cell must be a string")

        if not isinstance(self.matched_formula_cells, list):
            raise ValueError("Matched formula cells must be a list")

        for cell in self.matched_formula_cells:
            if not isinstance(cell, str):
                raise ValueError("Each matched formula cell must be a string")

        self.rows_count = validate_non_negative_int(self.rows_count, "Rows count")

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "FindResult":
        """从飞书API响应创建实例"""
        try:
            return cls(
                matched_cells=data.get("matched_cells", []),
                matched_formula_cells=data.get("matched_formula_cells", []),
                rows_count=data.get("rows_count", 0),
            )
        except ValueError as e:
            raise ValueError(f"Invalid data format in API response: {e}")

    def has_matches(self) -> bool:
        """检查是否有匹配结果"""
        return len(self.matched_cells) > 0 or len(self.matched_formula_cells) > 0

    def total_matches(self) -> int:
        """获取总匹配数量"""
        return len(self.matched_cells) + len(self.matched_formula_cells)


@dataclass
class MCPToolResult:
    """MCP工具调用结果"""

    content: List[Dict]
    is_error: bool = False

    def __post_init__(self):
        """数据验证"""
        if not isinstance(self.content, list):
            raise ValueError("Content must be a list")

        for item in self.content:
            if not isinstance(item, dict):
                raise ValueError("Each content item must be a dictionary")
            if "type" not in item:
                raise ValueError("Each content item must have a 'type' field")

        if not isinstance(self.is_error, bool):
            raise ValueError("is_error must be a boolean")

    @classmethod
    def success(cls, data: Any, message: str = None) -> "MCPToolResult":
        """创建成功结果"""
        if message:
            content = [
                {"type": "text", "text": message},
                {"type": "text", "text": str(data)},
            ]
        else:
            content = [{"type": "text", "text": str(data)}]

        return cls(content=content, is_error=False)

    @classmethod
    def error(cls, message: str, error_code: int = None) -> "MCPToolResult":
        """创建错误结果"""
        text = f"Error {error_code}: {message}" if error_code else f"Error: {message}"
        content = [{"type": "text", "text": text}]
        return cls(content=content, is_error=True)


@dataclass
class FeishuAPIError(Exception):
    """飞书API错误"""

    code: int
    message: str
    http_status: int

    def __post_init__(self):
        """数据验证"""
        if not isinstance(self.code, int):
            raise ValueError("Error code must be an integer")

        if not self.message or not isinstance(self.message, str):
            raise ValueError("Error message must be a non-empty string")
        self.message = self.message.strip()

        if not isinstance(self.http_status, int):
            raise ValueError("HTTP status must be an integer")

        if self.http_status < 100 or self.http_status >= 600:
            raise ValueError("HTTP status must be between 100 and 599")

    def to_mcp_error(self) -> Dict:
        """转换为MCP错误格式"""
        return {
            "content": [
                {"type": "text", "text": f"飞书API错误 {self.code}: {self.message}"}
            ],
            "isError": True,
        }

    @classmethod
    def from_api_response(
        cls, response_data: Dict[str, Any], http_status: int
    ) -> "FeishuAPIError":
        """从飞书API错误响应创建实例"""
        try:
            return cls(
                code=response_data["code"],
                message=response_data["msg"],
                http_status=http_status,
            )
        except KeyError as e:
            raise ValueError(f"Missing required field in error response: {e}")

    def is_retryable(self) -> bool:
        """判断错误是否可重试"""
        from .error_handling import ErrorCodeMapping

        return ErrorCodeMapping.is_retryable(self.code)

    def is_authentication_error(self) -> bool:
        """判断是否为认证错误"""
        from .error_handling import ErrorCategory, ErrorCodeMapping

        return (
            self.http_status == 401
            or ErrorCodeMapping.get_error_category(self.code)
            == ErrorCategory.AUTHENTICATION
        )

    def is_permission_error(self) -> bool:
        """判断是否为权限错误"""
        from .error_handling import ErrorCategory, ErrorCodeMapping

        return (
            self.http_status == 403
            or ErrorCodeMapping.get_error_category(self.code)
            == ErrorCategory.PERMISSION
        )

    def is_not_found_error(self) -> bool:
        """判断是否为资源不存在错误"""
        from .error_handling import ErrorCategory, ErrorCodeMapping

        return (
            self.http_status == 404
            or ErrorCodeMapping.get_error_category(self.code) == ErrorCategory.NOT_FOUND
        )

    def needs_auth_refresh(self) -> bool:
        """判断是否需要刷新认证"""
        from .error_handling import ErrorCodeMapping

        return ErrorCodeMapping.needs_auth_refresh(self.code)

    def is_permanent(self) -> bool:
        """判断是否为永久性错误"""
        from .error_handling import ErrorCodeMapping

        return ErrorCodeMapping.is_permanent(self.code)

    def get_error_category(self):
        """获取错误分类"""
        from .error_handling import ErrorCodeMapping

        return ErrorCodeMapping.get_error_category(self.code)

    def get_retry_config(self):
        """获取重试配置"""
        from .error_handling import ErrorCodeMapping

        return ErrorCodeMapping.get_retry_config_for_error(self.code)

    def get_user_friendly_message(self) -> str:
        """获取用户友好的错误消息"""
        from .error_handling import ErrorCodeMapping

        return ErrorCodeMapping.get_user_friendly_message(self.code, self.message)
