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
        async def list_spreadsheets(args: ListSpreadsheetsArgs) -> Dict[str, Any]:
            """获取用户可访问的电子表格列表"""
            return await spreadsheet_tools.list_spreadsheets(
                self.api_client,
                folder_token=args.folder_token,
                page_size=args.page_size,
            )

        @self.mcp.tool()
        async def get_worksheets(args: GetWorksheetsArgs) -> Dict[str, Any]:
            """获取指定电子表格的工作表列表"""
            return await spreadsheet_tools.get_worksheets(
                self.api_client, spreadsheet_token=args.spreadsheet_token
            )

        @self.mcp.tool()
        async def read_range(args: ReadRangeArgs) -> Dict[str, Any]:
            """读取指定范围的单元格数据"""
            return await spreadsheet_tools.read_range(
                self.api_client,
                spreadsheet_token=args.spreadsheet_token,
                range_spec=args.range_spec,
                value_render_option=args.value_render_option,
                date_time_render_option=args.date_time_render_option,
            )

        @self.mcp.tool()
        async def read_multiple_ranges(args: ReadMultipleRangesArgs) -> Dict[str, Any]:
            """批量读取多个范围的数据"""
            return await spreadsheet_tools.read_multiple_ranges(
                self.api_client,
                spreadsheet_token=args.spreadsheet_token,
                ranges=args.ranges,
                value_render_option=args.value_render_option,
                date_time_render_option=args.date_time_render_option,
            )

        @self.mcp.tool()
        async def find_cells(args: FindCellsArgs) -> Dict[str, Any]:
            """在指定范围内查找单元格"""
            return await spreadsheet_tools.find_cells(
                self.api_client,
                spreadsheet_token=args.spreadsheet_token,
                sheet_id=args.sheet_id,
                range_spec=args.range_spec,
                find_text=args.find_text,
                match_case=args.match_case,
                match_entire_cell=args.match_entire_cell,
                search_by_regex=args.search_by_regex,
                include_formulas=args.include_formulas,
            )

    def get_mcp_server(self) -> FastMCP:
        """获取 FastMCP 实例"""
        return self.mcp

    async def close(self):
        """关闭服务器和清理资源"""
        await self.api_client.close()
