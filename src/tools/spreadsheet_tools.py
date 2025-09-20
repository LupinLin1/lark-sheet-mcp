"""
MCP tools for spreadsheet operations.
"""

from typing import List, Optional, Tuple

from ..models import FindResult, RangeData, SpreadsheetInfo, WorksheetInfo


def _parse_cell_position(cell_ref: str) -> Tuple[int, int]:
    """Parse cell reference like 'A1' to (column_index, row_index) (0-based)"""
    import re
    
    match = re.match(r'^([A-Z]+)(\d+)$', cell_ref.upper())
    if not match:
        raise ValueError(f"Invalid cell reference: {cell_ref}")
    
    col_str, row_str = match.groups()
    
    # Convert column letters to 0-based index
    col_index = 0
    for char in col_str:
        col_index = col_index * 26 + (ord(char) - ord('A') + 1)
    col_index -= 1
    
    # Convert row number to 0-based index
    row_index = int(row_str) - 1
    
    return col_index, row_index


def _position_to_cell_ref(col_index: int, row_index: int) -> str:
    """Convert (column_index, row_index) (0-based) to cell reference like 'A1'"""
    # Convert column index to letters
    col_str = ""
    col_index += 1  # Make it 1-based
    while col_index > 0:
        col_index -= 1
        col_str = chr(col_index % 26 + ord('A')) + col_str
        col_index //= 26
    
    # Convert row index to 1-based number
    row_str = str(row_index + 1)
    
    return col_str + row_str


async def list_spreadsheets(
    api_client, folder_token: Optional[str] = None, page_size: int = 50
) -> dict:
    """
    获取用户可访问的电子表格列表

    Args:
        api_client: FeishuAPIClient instance
        folder_token: 文件夹token，为空时获取根目录
        page_size: 每页返回的数量，最大200

    Returns:
        电子表格信息列表
    """
    from ..models.data_models import FeishuAPIError

    # Validate page_size
    if not isinstance(page_size, int) or page_size <= 0:
        raise ValueError("page_size must be a positive integer")
    if page_size > 200:
        page_size = 200  # API maximum

    # Validate folder_token if provided
    if folder_token is not None:
        if not isinstance(folder_token, str):
            raise ValueError("folder_token must be a string if provided")
        folder_token = folder_token.strip()
        # Allow empty string for root folder
        if len(folder_token) == 0:
            folder_token = None

    try:
        spreadsheets = []
        page_token = None

        # Handle pagination
        while True:
            params = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token

            # Call API
            response = await api_client.list_files(folder_token=folder_token, **params)

            # Extract files from response
            files = response.get("data", {}).get("files", [])

            # Filter for spreadsheets (type="sheet")
            for file_data in files:
                if file_data.get("type") == "sheet":
                    try:
                        spreadsheet = SpreadsheetInfo.from_api_response(file_data)
                        spreadsheets.append(spreadsheet)
                    except ValueError as e:
                        # Log invalid data but continue processing
                        import logging

                        logger = logging.getLogger(__name__)
                        logger.warning(f"Skipping invalid spreadsheet data: {e}")
                        continue

            # Check for next page
            page_token = response.get("data", {}).get("page_token")
            if not page_token:
                break

        # Convert to dictionary format for FastMCP compatibility
        spreadsheet_dicts = []
        for spreadsheet in spreadsheets:
            spreadsheet_dict = {
                "token": spreadsheet.token,
                "name": spreadsheet.name,
                "type": spreadsheet.type,
                "url": spreadsheet.url,
                "created_time": spreadsheet.created_time.isoformat(),
                "modified_time": spreadsheet.modified_time.isoformat(),
                "owner_id": spreadsheet.owner_id,
            }
            spreadsheet_dicts.append(spreadsheet_dict)

        return {
            "spreadsheets": spreadsheet_dicts,
            "total_count": len(spreadsheet_dicts),
        }
    except FeishuAPIError as e:
        # Handle specific API errors with user-friendly messages
        if e.code == 1061004:  # Permission error
            raise FeishuAPIError(
                code=e.code,
                message="没有访问权限。请检查文档权限设置或联系文档所有者。",
                http_status=e.http_status,
            ) from e
        elif e.is_authentication_error():
            raise FeishuAPIError(
                code=e.code,
                message="认证失败。请检查app_id和app_secret配置。",
                http_status=e.http_status,
            ) from e
        else:
            # Re-raise other API errors as-is
            raise
    except Exception as e:
        # Wrap unexpected errors
        raise FeishuAPIError(
            code=-1, message=f"获取电子表格列表时发生错误: {str(e)}", http_status=500
        ) from e


async def get_worksheets(api_client, spreadsheet_token: str) -> dict:
    """
    获取指定电子表格的工作表列表

    Args:
        api_client: FeishuAPIClient instance
        spreadsheet_token: 电子表格token

    Returns:
        工作表信息列表
    """
    from ..models.data_models import FeishuAPIError

    # Validate spreadsheet_token
    if not spreadsheet_token or not isinstance(spreadsheet_token, str):
        raise ValueError("spreadsheet_token must be a non-empty string")
    spreadsheet_token = spreadsheet_token.strip()
    if not spreadsheet_token:
        raise ValueError("spreadsheet_token cannot be empty or whitespace only")

    try:
        # Call API to get worksheets
        response = await api_client.get_worksheets(spreadsheet_token)

        # Extract worksheets from response
        worksheets_data = response.get("data", {}).get("sheets", [])

        worksheets = []
        for worksheet_data in worksheets_data:
            try:
                worksheet = WorksheetInfo.from_api_response(worksheet_data)
                worksheets.append(worksheet)
            except ValueError as e:
                # Log invalid data but continue processing
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Skipping invalid worksheet data: {e}")
                continue

        # Convert to dictionary format for FastMCP compatibility
        worksheet_dicts = []
        for worksheet in worksheets:
            worksheet_dict = {
                "sheet_id": worksheet.sheet_id,
                "title": worksheet.title,
                "index": worksheet.index,
                "hidden": worksheet.hidden,
                "row_count": worksheet.row_count,
                "column_count": worksheet.column_count,
                "frozen_row_count": worksheet.frozen_row_count,
                "frozen_column_count": worksheet.frozen_column_count,
                "resource_type": worksheet.resource_type,
                "merges": worksheet.merges,
            }
            worksheet_dicts.append(worksheet_dict)

        return {"worksheets": worksheet_dicts, "total_count": len(worksheet_dicts)}

    except FeishuAPIError as e:
        # Handle specific API errors with user-friendly messages
        if e.code == 1310214:  # Spreadsheet not found
            raise FeishuAPIError(
                code=e.code,
                message="指定的电子表格不存在。请检查spreadsheet_token是否正确。",
                http_status=e.http_status,
            ) from e
        elif e.code == 1310213:  # Permission error
            raise FeishuAPIError(
                code=e.code,
                message="没有读取权限。请检查电子表格权限设置或联系文档所有者。",
                http_status=e.http_status,
            ) from e
        elif e.is_authentication_error():
            raise FeishuAPIError(
                code=e.code,
                message="认证失败。请检查app_id和app_secret配置。",
                http_status=e.http_status,
            ) from e
        else:
            # Re-raise other API errors as-is
            raise
    except Exception as e:
        # Wrap unexpected errors
        raise FeishuAPIError(
            code=-1, message=f"获取工作表列表时发生错误: {str(e)}", http_status=500
        ) from e


async def read_range(
    api_client,
    spreadsheet_token: str,
    range_spec: str,
    value_render_option: str = "UnformattedValue",
    date_time_render_option: str = "FormattedString",
) -> dict:
    """
    读取指定范围的单元格数据

    Args:
        api_client: FeishuAPIClient instance
        spreadsheet_token: 电子表格token
        range_spec: 范围规格，格式为 "sheetId!A1:B10"
        value_render_option: 数据渲染选项
        date_time_render_option: 日期时间渲染选项

    Returns:
        范围数据
    """
    from ..models.data_models import FeishuAPIError, validate_range_spec

    # Validate parameters
    if not spreadsheet_token or not isinstance(spreadsheet_token, str):
        raise ValueError("spreadsheet_token must be a non-empty string")
    spreadsheet_token = spreadsheet_token.strip()
    if not spreadsheet_token:
        raise ValueError("spreadsheet_token cannot be empty or whitespace only")

    # Validate range specification
    range_spec = validate_range_spec(range_spec)

    # Validate value render option
    valid_value_options = ["ToString", "Formula", "FormattedValue", "UnformattedValue"]
    if value_render_option not in valid_value_options:
        raise ValueError(f"value_render_option must be one of {valid_value_options}")

    # Validate date time render option
    valid_datetime_options = ["FormattedString"]
    if date_time_render_option not in valid_datetime_options:
        raise ValueError(
            f"date_time_render_option must be one of {valid_datetime_options}"
        )

    try:
        # Call API to read range
        response = await api_client.read_range(
            spreadsheet_token=spreadsheet_token,
            range_spec=range_spec,
            value_render_option=value_render_option,
            date_time_render_option=date_time_render_option,
        )

        # Extract range data from response
        range_data = response.get("data", {}).get("valueRange", {})

        # Create RangeData object and convert to dict
        result = RangeData.from_api_response(range_data)

        return {
            "range": result.range,
            "major_dimension": result.major_dimension,
            "values": result.values,
            "revision": result.revision,
            "is_empty": result.is_empty(),
        }

    except FeishuAPIError as e:
        # Handle specific API errors with user-friendly messages
        if e.code == 1310214:  # Spreadsheet not found
            raise FeishuAPIError(
                code=e.code,
                message="指定的电子表格不存在。请检查spreadsheet_token是否正确。",
                http_status=e.http_status,
            ) from e
        elif e.code == 1310215:  # Sheet not found
            raise FeishuAPIError(
                code=e.code,
                message="指定的工作表不存在。请检查range_spec中的工作表ID是否正确。",
                http_status=e.http_status,
            ) from e
        elif e.code == 1310213:  # Permission error
            raise FeishuAPIError(
                code=e.code,
                message="没有读取权限。请检查电子表格权限设置或联系文档所有者。",
                http_status=e.http_status,
            ) from e
        elif e.code == 1310216:  # Range format error
            raise FeishuAPIError(
                code=e.code,
                message="范围格式无效。请使用正确的格式，如 'sheetId!A1:B10'。",
                http_status=e.http_status,
            ) from e
        elif e.code == 1310218:  # Data size limit exceeded
            raise FeishuAPIError(
                code=e.code,
                message="返回数据超过10MB限制。请缩小查询范围。",
                http_status=e.http_status,
            ) from e
        elif e.is_authentication_error():
            raise FeishuAPIError(
                code=e.code,
                message="认证失败。请检查app_id和app_secret配置。",
                http_status=e.http_status,
            ) from e
        else:
            # Re-raise other API errors as-is
            raise
    except Exception as e:
        # Wrap unexpected errors
        raise FeishuAPIError(
            code=-1, message=f"读取范围数据时发生错误: {str(e)}", http_status=500
        ) from e


async def read_multiple_ranges(
    api_client,
    spreadsheet_token: str,
    ranges: List[str],
    value_render_option: str = "UnformattedValue",
    date_time_render_option: str = "FormattedString",
) -> dict:
    """
    批量读取多个范围的数据

    Args:
        api_client: FeishuAPIClient instance
        spreadsheet_token: 电子表格token
        ranges: 范围列表
        value_render_option: 数据渲染选项
        date_time_render_option: 日期时间渲染选项

    Returns:
        多个范围的数据列表
    """
    from ..models.data_models import FeishuAPIError, validate_range_spec

    # Validate parameters
    if not spreadsheet_token or not isinstance(spreadsheet_token, str):
        raise ValueError("spreadsheet_token must be a non-empty string")
    spreadsheet_token = spreadsheet_token.strip()
    if not spreadsheet_token:
        raise ValueError("spreadsheet_token cannot be empty or whitespace only")

    # Validate ranges parameter
    if not isinstance(ranges, list):
        raise ValueError("ranges must be a list")
    if len(ranges) == 0:
        raise ValueError("ranges cannot be empty")
    if len(ranges) > 100:  # API limitation
        raise ValueError("ranges cannot contain more than 100 items")

    # Validate each range specification
    validated_ranges = []
    for i, range_spec in enumerate(ranges):
        try:
            validated_range = validate_range_spec(range_spec)
            validated_ranges.append(validated_range)
        except ValueError as e:
            raise ValueError(f"Invalid range at index {i}: {e}")

    # Validate value render option
    valid_value_options = ["ToString", "Formula", "FormattedValue", "UnformattedValue"]
    if value_render_option not in valid_value_options:
        raise ValueError(f"value_render_option must be one of {valid_value_options}")

    # Validate date time render option
    valid_datetime_options = ["FormattedString"]
    if date_time_render_option not in valid_datetime_options:
        raise ValueError(
            f"date_time_render_option must be one of {valid_datetime_options}"
        )

    try:
        # Fallback implementation: use multiple single read_range calls
        # This works around API issues with the batch endpoint
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Using fallback implementation for read_multiple_ranges")
        
        value_ranges = []
        for range_spec in validated_ranges:
            try:
                single_response = await api_client.read_range(
                    spreadsheet_token=spreadsheet_token,
                    range_spec=range_spec,
                    value_render_option=value_render_option,
                    date_time_render_option=date_time_render_option,
                )
                # Extract the valueRange from single response
                single_range = single_response.get("data", {}).get("valueRange", {})
                value_ranges.append(single_range)
            except Exception as e:
                logger.warning(f"Failed to read range {range_spec}: {e}")
                # Add empty range as placeholder
                empty_range = {
                    "range": range_spec,
                    "majorDimension": "ROWS", 
                    "values": [],
                    "revision": 0
                }
                value_ranges.append(empty_range)

        results = []
        for i, range_data in enumerate(value_ranges):
            try:
                result = RangeData.from_api_response(range_data)
                results.append(result)
            except ValueError as e:
                # Log invalid data but continue processing
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Skipping invalid range data at index {i}: {e}")
                # Add empty range data as placeholder
                empty_range = {
                    "range": (
                        validated_ranges[i]
                        if i < len(validated_ranges)
                        else f"unknown_range_{i}"
                    ),
                    "major_dimension": "ROWS",
                    "values": [],
                    "revision": 0,
                    "is_empty": True,
                }
                results.append(empty_range)

        # Convert results to dictionary format
        range_dicts = []
        for result in results:
            if isinstance(result, RangeData):
                range_dict = {
                    "range": result.range,
                    "major_dimension": result.major_dimension,
                    "values": result.values,
                    "revision": result.revision,
                    "is_empty": result.is_empty(),
                }
            else:
                range_dict = result  # Already a dict (empty range)
            range_dicts.append(range_dict)

        return {"ranges": range_dicts, "total_count": len(range_dicts)}

    except FeishuAPIError as e:
        # Handle specific API errors with user-friendly messages
        if e.code == 1310214:  # Spreadsheet not found
            raise FeishuAPIError(
                code=e.code,
                message="指定的电子表格不存在。请检查spreadsheet_token是否正确。",
                http_status=e.http_status,
            ) from e
        elif e.code == 1310215:  # Sheet not found
            raise FeishuAPIError(
                code=e.code,
                message="指定的工作表不存在。请检查ranges中的工作表ID是否正确。",
                http_status=e.http_status,
            ) from e
        elif e.code == 1310213:  # Permission error
            raise FeishuAPIError(
                code=e.code,
                message="没有读取权限。请检查电子表格权限设置或联系文档所有者。",
                http_status=e.http_status,
            ) from e
        elif e.code == 1310216:  # Range format error
            raise FeishuAPIError(
                code=e.code,
                message="范围格式无效。请使用正确的格式，如 'sheetId!A1:B10'。",
                http_status=e.http_status,
            ) from e
        elif e.code == 1310218:  # Data size limit exceeded
            raise FeishuAPIError(
                code=e.code,
                message="返回数据超过10MB限制。请减少查询范围的数量或大小。",
                http_status=e.http_status,
            ) from e
        elif e.is_authentication_error():
            raise FeishuAPIError(
                code=e.code,
                message="认证失败。请检查app_id和app_secret配置。",
                http_status=e.http_status,
            ) from e
        else:
            # Re-raise other API errors as-is
            raise
    except Exception as e:
        # Wrap unexpected errors
        raise FeishuAPIError(
            code=-1, message=f"批量读取范围数据时发生错误: {str(e)}", http_status=500
        ) from e


async def find_cells(
    api_client,
    spreadsheet_token: str,
    sheet_id: str,
    range_spec: str,
    find_text: str,
    match_case: bool = False,
    match_entire_cell: bool = False,
    search_by_regex: bool = False,
    include_formulas: bool = False,
) -> dict:
    """
    在指定范围内查找单元格

    Args:
        api_client: FeishuAPIClient instance
        spreadsheet_token: 电子表格token
        sheet_id: 工作表ID
        range_spec: 搜索范围
        find_text: 查找文本或正则表达式
        match_case: 是否区分大小写
        match_entire_cell: 是否完全匹配单元格
        search_by_regex: 是否使用正则表达式
        include_formulas: 是否仅搜索公式

    Returns:
        查找结果
    """
    import re

    from ..models.data_models import FeishuAPIError

    # Validate parameters
    if not spreadsheet_token or not isinstance(spreadsheet_token, str):
        raise ValueError("spreadsheet_token must be a non-empty string")
    spreadsheet_token = spreadsheet_token.strip()
    if not spreadsheet_token:
        raise ValueError("spreadsheet_token cannot be empty or whitespace only")

    if not sheet_id or not isinstance(sheet_id, str):
        raise ValueError("sheet_id must be a non-empty string")
    sheet_id = sheet_id.strip()
    if not sheet_id:
        raise ValueError("sheet_id cannot be empty or whitespace only")

    if not range_spec or not isinstance(range_spec, str):
        raise ValueError("range_spec must be a non-empty string")
    range_spec = range_spec.strip()
    if not range_spec:
        raise ValueError("range_spec cannot be empty or whitespace only")

    if not find_text or not isinstance(find_text, str):
        raise ValueError("find_text must be a non-empty string")
    find_text = find_text.strip()
    if not find_text:
        raise ValueError("find_text cannot be empty or whitespace only")

    # Validate boolean parameters
    if not isinstance(match_case, bool):
        raise ValueError("match_case must be a boolean")
    if not isinstance(match_entire_cell, bool):
        raise ValueError("match_entire_cell must be a boolean")
    if not isinstance(search_by_regex, bool):
        raise ValueError("search_by_regex must be a boolean")
    if not isinstance(include_formulas, bool):
        raise ValueError("include_formulas must be a boolean")

    # Validate regex pattern if search_by_regex is True
    if search_by_regex:
        try:
            re.compile(find_text)
        except re.error as e:
            raise ValueError(f"Invalid regular expression: {e}")

    try:
        # Fallback implementation: read data and search locally
        # This avoids the API issues with find_cells endpoint
        import logging
        import re

        logger = logging.getLogger(__name__)
        logger.debug(
            f"Using local search fallback for: spreadsheet_token={spreadsheet_token}, sheet_id={sheet_id}, range_spec={range_spec}, find_text={find_text}"
        )

        # Construct range with sheet_id if not present
        if "!" not in range_spec:
            full_range_spec = f"{sheet_id}!{range_spec}"
        else:
            full_range_spec = range_spec

        # Read the data from the range
        range_data = await read_range(
            api_client,
            spreadsheet_token,
            full_range_spec,
        )

        # Perform local search
        matched_cells = []
        matched_formula_cells = []  # We don't have formula info in read_range
        rows_count = 0

        if range_data and range_data.get("values"):
            # Parse the range to get starting position
            range_part = full_range_spec.split("!")[-1]
            start_col, start_row = _parse_cell_position(range_part.split(":")[0])

            for row_idx, row in enumerate(range_data["values"]):
                row_has_match = False
                for col_idx, cell_value in enumerate(row):
                    if cell_value is None:
                        continue
                    
                    cell_str = str(cell_value)
                    found = False

                    if search_by_regex:
                        # Use regex search
                        try:
                            pattern = re.compile(find_text, re.IGNORECASE if not match_case else 0)
                            found = bool(pattern.search(cell_str))
                        except re.error:
                            # Invalid regex, skip
                            continue
                    else:
                        # String search
                        search_text = find_text if match_case else find_text.lower()
                        search_in = cell_str if match_case else cell_str.lower()
                        
                        if match_entire_cell:
                            found = search_in == search_text
                        else:
                            found = search_text in search_in

                    if found:
                        # Convert to cell reference (A1, B2, etc.)
                        cell_ref = _position_to_cell_ref(start_col + col_idx, start_row + row_idx)
                        matched_cells.append(cell_ref)
                        row_has_match = True

                if row_has_match:
                    rows_count += 1

        return {
            "matched_cells": matched_cells,
            "matched_formula_cells": matched_formula_cells,
            "rows_count": rows_count,
            "has_matches": len(matched_cells) > 0,
            "total_matches": len(matched_cells),
        }

    except FeishuAPIError as e:
        # Handle specific API errors with user-friendly messages and return error dict instead of raising
        error_message = ""
        if e.code == 1310214:  # Spreadsheet not found
            error_message = "指定的电子表格不存在。请检查spreadsheet_token是否正确。"
        elif e.code == 1310215:  # Sheet not found
            error_message = "指定的工作表不存在。请检查sheet_id是否正确。"
        elif e.code == 1310213:  # Permission error
            error_message = "没有读取权限。请检查电子表格权限设置或联系文档所有者。"
        elif e.code == 1310216:  # Range format error
            error_message = "范围格式无效。请使用正确的格式，如 'A1:B10'。"
        elif e.code == 1310219:  # Invalid regex pattern
            error_message = "正则表达式格式无效。请检查正则表达式语法。"
        elif e.is_authentication_error():
            error_message = "认证失败。请检查app_id和app_secret配置。"
        else:
            error_message = e.message

        # Return error as dict instead of raising exception
        return {
            "error": True,
            "error_code": e.code,
            "error_message": error_message,
            "matched_cells": [],
            "matched_formula_cells": [],
            "rows_count": 0,
            "has_matches": False,
            "total_matches": 0,
        }
    except Exception as e:
        # Log the full exception for debugging
        import logging
        import traceback

        logger = logging.getLogger(__name__)
        logger.error(f"Exception in find_cells: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        # Return error as dict instead of raising exception
        return {
            "error": True,
            "error_code": -1,
            "error_message": f"查找单元格时发生错误: {str(e)}",
            "matched_cells": [],
            "matched_formula_cells": [],
            "rows_count": 0,
            "has_matches": False,
            "total_matches": 0,
        }
