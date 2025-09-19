"""
MCP tools for spreadsheet operations.
"""

from typing import List, Optional

from ..models import FindResult, RangeData, SpreadsheetInfo, WorksheetInfo


async def list_spreadsheets(
    api_client, folder_token: Optional[str] = None, page_size: int = 50
) -> List[SpreadsheetInfo]:
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
        if not isinstance(folder_token, str) or not folder_token.strip():
            raise ValueError("folder_token must be a non-empty string if provided")
        folder_token = folder_token.strip()

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

        return spreadsheets
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


async def get_worksheets(api_client, spreadsheet_token: str) -> List[WorksheetInfo]:
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

        return worksheets

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
) -> RangeData:
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

        # Create RangeData object
        result = RangeData.from_api_response(range_data)

        return result

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
) -> List[RangeData]:
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
        # Call API to read multiple ranges
        response = await api_client.read_multiple_ranges(
            spreadsheet_token=spreadsheet_token,
            ranges=validated_ranges,
            value_render_option=value_render_option,
            date_time_render_option=date_time_render_option,
        )

        # Extract range data from response
        value_ranges = response.get("data", {}).get("valueRanges", [])

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
                results.append(
                    RangeData(
                        range=(
                            validated_ranges[i]
                            if i < len(validated_ranges)
                            else f"unknown_range_{i}"
                        ),
                        major_dimension="ROWS",
                        values=[],
                        revision=0,
                    )
                )

        return results

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
) -> FindResult:
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
    from ..models.data_models import FeishuAPIError
    import re

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
        # Call API to find cells
        response = await api_client.find_cells(
            spreadsheet_token=spreadsheet_token,
            sheet_id=sheet_id,
            range_spec=range_spec,
            find_text=find_text,
            match_case=match_case,
            match_entire_cell=match_entire_cell,
            search_by_regex=search_by_regex,
            include_formulas=include_formulas,
        )

        # Extract find result from response
        find_data = response.get("data", {}).get("find_result", {})

        # Create FindResult object
        result = FindResult.from_api_response(find_data)

        return result

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
                message="指定的工作表不存在。请检查sheet_id是否正确。",
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
                message="范围格式无效。请使用正确的格式，如 'A1:B10'。",
                http_status=e.http_status,
            ) from e
        elif e.code == 1310219:  # Invalid regex pattern
            raise FeishuAPIError(
                code=e.code,
                message="正则表达式格式无效。请检查正则表达式语法。",
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
            code=-1, message=f"查找单元格时发生错误: {str(e)}", http_status=500
        ) from e
