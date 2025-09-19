# Requirements Document

## Introduction

本功能旨在创建一个MCP（Model Context Protocol）服务，用于读取飞书（Lark/Feishu）电子表格数据。该服务将作为一个独立的MCP服务器运行，允许AI助手通过标准化的接口访问和读取飞书电子表格中的数据，为用户提供便捷的数据查询和分析能力。基于飞书开放平台的电子表格API，该服务支持读取单个范围、多个范围的数据，获取工作表信息，以及查找单元格等功能。

## Requirements

### Requirement 1

**User Story:** 作为开发者，我希望能够通过MCP协议连接到飞书电子表格服务，以便AI助手可以访问我的电子表格数据。

#### Acceptance Criteria

1. WHEN 用户配置MCP服务器时 THEN 系统 SHALL 提供飞书API认证配置选项（app_id、app_secret）
2. WHEN MCP客户端连接到服务器时 THEN 系统 SHALL 使用tenant_access_token或user_access_token验证飞书API凭据
3. IF 认证失败 THEN 系统 SHALL 返回明确的错误信息和状态码

### Requirement 2

**User Story:** 作为用户，我希望能够列出我有权限访问的飞书电子表格，以便选择需要读取的表格。

#### Acceptance Criteria

1. WHEN 用户请求电子表格列表时 THEN 系统 SHALL 调用"获取文件夹中的文件清单"API返回type为"sheet"的文件
2. WHEN 返回电子表格列表时 THEN 系统 SHALL 包含表格名称、token、创建时间、修改时间和所有者信息
3. IF 用户没有任何可访问的电子表格 THEN 系统 SHALL 返回空列表和相应提示
4. WHEN API返回1061004权限错误时 THEN 系统 SHALL 提示用户检查文档权限设置

### Requirement 3

**User Story:** 作为用户，我希望能够获取指定电子表格的工作表列表，以便了解表格的结构和选择要读取的工作表。

#### Acceptance Criteria

1. WHEN 用户指定电子表格token时 THEN 系统 SHALL 调用"获取工作表"API返回所有工作表信息
2. WHEN 返回工作表列表时 THEN 系统 SHALL 包含工作表ID、标题、索引位置、是否隐藏、行列数等属性
3. WHEN 工作表包含合并单元格时 THEN 系统 SHALL 返回合并单元格的范围信息
4. IF 指定的电子表格不存在 THEN 系统 SHALL 返回1310214错误码
5. IF 用户没有读取权限 THEN 系统 SHALL 返回1310213权限错误

### Requirement 4

**User Story:** 作为用户，我希望能够读取电子表格中指定范围的单元格数据，以便获取特定区域的内容。

#### Acceptance Criteria

1. WHEN 用户指定单元格范围（如sheetId!A1:C10）时 THEN 系统 SHALL 调用"读取单个范围"API返回该范围内的数据
2. WHEN 用户指定多个范围时 THEN 系统 SHALL 调用"读取多个范围"API批量获取数据
3. WHEN 指定valueRenderOption参数时 THEN 系统 SHALL 支持ToString、Formula、FormattedValue、UnformattedValue格式
4. WHEN 指定dateTimeRenderOption参数时 THEN 系统 SHALL 支持FormattedString格式化日期时间
5. IF 范围格式无效 THEN 系统 SHALL 返回相应错误码和格式说明
6. WHEN 返回数据超过10MB限制时 THEN 系统 SHALL 返回相应错误提示

### Requirement 5

**User Story:** 作为用户，我希望能够在电子表格中查找特定内容，以便快速定位所需的数据。

#### Acceptance Criteria

1. WHEN 用户指定查找条件时 THEN 系统 SHALL 调用"查找单元格"API在指定范围内搜索
2. WHEN 设置match_case参数时 THEN 系统 SHALL 支持区分或忽略大小写的搜索
3. WHEN 设置match_entire_cell参数时 THEN 系统 SHALL 支持完全匹配或部分匹配单元格内容
4. WHEN 设置search_by_regex参数时 THEN 系统 SHALL 支持正则表达式搜索
5. WHEN 设置include_formulas参数时 THEN 系统 SHALL 支持仅搜索公式或仅搜索内容
6. WHEN 返回搜索结果时 THEN 系统 SHALL 包含匹配的单元格位置和含公式的单元格位置

### Requirement 6

**User Story:** 作为开发者，我希望MCP服务能够处理飞书API的限流和错误，以便提供稳定可靠的服务。

#### Acceptance Criteria

1. WHEN 遇到1310217（Too Many Request）错误时 THEN 系统 SHALL 自动重试并实现指数退避
2. WHEN 遇到1310235（Retry Later）错误时 THEN 系统 SHALL 稍后重试最多3次
3. WHEN 遇到网络超时时 THEN 系统 SHALL 返回明确的超时错误信息
4. WHEN 遇到1315201或1315203服务内部错误时 THEN 系统 SHALL 提示联系客服
5. WHEN API返回永久性错误（如1310214表格未找到）时 THEN 系统 SHALL 立即返回错误而不重试
6. WHEN 遇到1310242（In Mix state）错误时 THEN 系统 SHALL 提示数据正在恢复中请稍后重试