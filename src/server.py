"""
MCP server implementation for Feishu Spreadsheet using fastmcp.
"""

import logging
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from pydantic import BaseModel

from .services import AuthenticationManager, FeishuAPIClient
from .tools import spreadsheet_tools

logger = logging.getLogger(__name__)


class ListSpreadsheetsArgs(BaseModel):
    folder_token: Optional[str] = None
    page_size: int = 50


class GetWorksheetsArgs(BaseModel):
    spreadsheet_token: str


class ReadRangeArgs(BaseModel):
    spreadsheet_token: str
    range_spec: str
    value_render_option: str = "UnformattedValue"
    date_time_render_option: str = "FormattedString"


class ReadMultipleRangesArgs(BaseModel):
    spreadsheet_token: str
    ranges: List[str]
    value_render_option: str = "UnformattedValue"
    date_time_render_option: str = "FormattedString"


class FindCellsArgs(BaseModel):
    spreadsheet_token: str
    sheet_id: str
    range_spec: str
    find_text: str
    match_case: bool = False
    match_entire_cell: bool = False
    search_by_regex: bool = False
    include_formulas: bool = False


class FeishuSpreadsheetMCPServer:
    """飞书电子表格MCP服务器主类"""

    def __init__(self, app_id: str, app_secret: str):
        """
        Initialize MCP server.

        Args:
            app_id: Feishu app ID
            app_secret: Feishu app secret
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.auth_manager = AuthenticationManager(app_id, app_secret)
        self.api_client = FeishuAPIClient(self.auth_manager)

        # Initialize FastMCP
        self.mcp = FastMCP("feishu-spreadsheet-mcp")

        # Register tools
        self._register_tools()

    def _register_tools(self):
        """注册所有工具"""

        @self.mcp.tool()
        async def list_spreadsheets(folder_token: Optional[str] = None, page_size: int = 50) -> Dict[str, Any]:
            """
            获取用户可访问的电子表格列表
            
            参数:
                folder_token (str, 可选): 目标文件夹的token。为空或None时获取根目录下的文件
                page_size (int): 每页返回的数量，默认50，最大200
            
            返回:
                包含电子表格列表的字典，包括token、名称、类型、URL等信息
            
            示例:
                - 获取根目录下的电子表格: list_spreadsheets()
                - 获取指定文件夹下的电子表格: list_spreadsheets(folder_token="fldcnSGx1fZ7mjJXuHWJBqWzqKh")
            """
            return await spreadsheet_tools.list_spreadsheets(
                self.api_client,
                folder_token=folder_token,
                page_size=page_size,
            )

        @self.mcp.tool()
        async def get_worksheets(spreadsheet_token: str) -> Dict[str, Any]:
            """
            获取指定电子表格的工作表列表
            
            参数:
                spreadsheet_token (str): 电子表格的token，必填参数
            
            返回:
                包含工作表列表的字典，每个工作表包含sheet_id、title、index等信息
            
            示例:
                get_worksheets(spreadsheet_token="shtcnmBA9r6dFU8cWHnGrOJnMWe")
            """
            return await spreadsheet_tools.get_worksheets(
                self.api_client, spreadsheet_token=spreadsheet_token
            )

        @self.mcp.tool()
        async def read_range(
            spreadsheet_token: str, 
            range_spec: str,
            value_render_option: str = "UnformattedValue",
            date_time_render_option: str = "FormattedString"
        ) -> Dict[str, Any]:
            """
            读取指定范围的单元格数据
            
            参数:
                spreadsheet_token (str): 电子表格的token，必填参数
                range_spec (str): 范围规格，格式为 "工作表ID!起始单元格:结束单元格"
                    例如: "1DZyHm!A1:C10"。工作表ID是类似"1DZyHm"的短字符串，不是工作表名称
                value_render_option (str): 数据渲染选项，可选值:
                    - "UnformattedValue" (默认): 未格式化的值
                    - "FormattedValue": 格式化的值
                    - "Formula": 公式
                    - "ToString": 转为字符串
                date_time_render_option (str): 日期时间渲染选项，当前仅支持 "FormattedString"
            
            返回:
                包含范围数据的字典，包括range、values等信息
            
            示例:
                - read_range(spreadsheet_token="NYSgsgSKAhKE7ntp133cvpjtnUg", range_spec="1DZyHm!A1:C5")
                - read_range(spreadsheet_token="NYSgsgSKAhKE7ntp133cvpjtnUg", range_spec="rJClyP!B2:D10", value_render_option="FormattedValue")
            """
            return await spreadsheet_tools.read_range(
                self.api_client,
                spreadsheet_token=spreadsheet_token,
                range_spec=range_spec,
                value_render_option=value_render_option,
                date_time_render_option=date_time_render_option,
            )

        @self.mcp.tool()
        async def read_multiple_ranges(
            spreadsheet_token: str,
            ranges: List[str],
            value_render_option: str = "UnformattedValue",
            date_time_render_option: str = "FormattedString"
        ) -> Dict[str, Any]:
            """
            批量读取多个范围的数据
            
            参数:
                spreadsheet_token (str): 电子表格的token，必填参数
                ranges (List[str]): 范围列表，每个范围格式为 "工作表ID!起始单元格:结束单元格"
                    最多支持100个范围。例如: ["1DZyHm!A1:C5", "rJClyP!B2:D10"]
                value_render_option (str): 数据渲染选项，可选值:
                    - "UnformattedValue" (默认): 未格式化的值
                    - "FormattedValue": 格式化的值
                    - "Formula": 公式
                    - "ToString": 转为字符串
                date_time_render_option (str): 日期时间渲染选项，当前仅支持 "FormattedString"
            
            返回:
                包含多个范围数据的字典，每个范围的数据包含range、values等信息
            
            示例:
                read_multiple_ranges(
                    spreadsheet_token="NYSgsgSKAhKE7ntp133cvpjtnUg", 
                    ranges=["1DZyHm!A1:C5", "1DZyHm!E1:G3", "rJClyP!A1:B10"]
                )
            """
            return await spreadsheet_tools.read_multiple_ranges(
                self.api_client,
                spreadsheet_token=spreadsheet_token,
                ranges=ranges,
                value_render_option=value_render_option,
                date_time_render_option=date_time_render_option,
            )

        @self.mcp.tool()
        async def find_cells(
            spreadsheet_token: str,
            sheet_id: str,
            range_spec: str,
            find_text: str,
            match_case: bool = False,
            match_entire_cell: bool = False,
            search_by_regex: bool = False,
            include_formulas: bool = False
        ) -> Dict[str, Any]:
            """
            在指定范围内查找单元格
            
            参数:
                spreadsheet_token (str): 电子表格的token，必填参数
                sheet_id (str): 工作表ID，类似"1DZyHm"的短字符串，必填参数（不是工作表名称）
                range_spec (str): 搜索范围，格式为 "起始单元格:结束单元格"
                    例如: "A1:C10" 或 "B2:E5"。注意：这里不需要包含工作表ID前缀
                find_text (str): 要查找的文本或正则表达式
                match_case (bool): 是否区分大小写，默认False
                match_entire_cell (bool): 是否完全匹配整个单元格内容，默认False
                search_by_regex (bool): 是否使用正则表达式搜索，默认False
                include_formulas (bool): 是否搜索公式内容，默认False
            
            返回:
                包含匹配结果的字典，包括matched_cells、total_matches等信息
            
            示例:
                - find_cells(spreadsheet_token="NYSgsgSKAhKE7ntp133cvpjtnUg", sheet_id="1DZyHm", range_spec="A1:C10", find_text="产品")
                - find_cells(spreadsheet_token="NYSgsgSKAhKE7ntp133cvpjtnUg", sheet_id="rJClyP", range_spec="A1:Z100", find_text="\\d+", search_by_regex=True)
            """
            return await spreadsheet_tools.find_cells(
                self.api_client,
                spreadsheet_token=spreadsheet_token,
                sheet_id=sheet_id,
                range_spec=range_spec,
                find_text=find_text,
                match_case=match_case,
                match_entire_cell=match_entire_cell,
                search_by_regex=search_by_regex,
                include_formulas=include_formulas,
            )

    def get_mcp_server(self) -> FastMCP:
        """获取 FastMCP 实例"""
        return self.mcp

    async def close(self):
        """关闭服务器和清理资源"""
        await self.api_client.close()
