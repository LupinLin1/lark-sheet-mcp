# MCP Configuration Guide - Feishu Spreadsheet Server (FastMCP)

## 🚀 Quick Start

1. **复制示例配置**:
   ```bash
   cp .mcp.json.example .mcp.json
   ```

2. **设置您的飞书应用凭据**:
   ```json
   {
     "mcpServers": {
       "feishu-spreadsheet-fastmcp": {
         "env": {
           "FEISHU_APP_ID": "your_actual_app_id",
           "FEISHU_APP_SECRET": "your_actual_app_secret"
         }
       }
     }
   }
   ```

3. **启用服务器**:
   ```json
   {
     "disabled": false
   }
   ```

## 📋 配置选项

### 基础配置

```json
{
  "mcpServers": {
    "feishu-spreadsheet-fastmcp": {
      "command": "python",
      "args": ["-m", "feishu_spreadsheet_mcp.main"],
      "env": {
        "FEISHU_APP_ID": "your_app_id",
        "FEISHU_APP_SECRET": "your_app_secret",
        "FEISHU_LOG_LEVEL": "INFO"
      },
      "disabled": false,
      "autoApprove": [
        "list_spreadsheets",
        "get_worksheets",
        "read_range",
        "read_multiple_ranges",
        "find_cells"
      ]
    }
  }
}
```

### 开发调试配置

```json
{
  "feishu-spreadsheet-dev": {
    "command": "python",
    "args": [
      "-m", 
      "feishu_spreadsheet_mcp.main",
      "--log-level", 
      "DEBUG"
    ],
    "env": {
      "FEISHU_APP_ID": "dev_app_id",
      "FEISHU_APP_SECRET": "dev_app_secret",
      "FEISHU_LOG_LEVEL": "DEBUG"
    },
    "disabled": true,
    "autoApprove": []
  }
}
```

### 使用配置文件

```json
{
  "feishu-spreadsheet-config": {
    "command": "python",
    "args": [
      "-m",
      "feishu_spreadsheet_mcp.main",
      "--config",
      "/path/to/config.json"
    ],
    "disabled": true
  }
}
```

## 🔧 环境变量

| 变量名 | 描述 | 必需 | 默认值 |
|-------|------|------|-------|
| `FEISHU_APP_ID` | 飞书应用ID | ✅ | - |
| `FEISHU_APP_SECRET` | 飞书应用密钥 | ✅ | - |
| `FEISHU_LOG_LEVEL` | 日志级别 | ❌ | INFO |
| `FEISHU_MAX_RETRIES` | 最大重试次数 | ❌ | 3 |
| `FEISHU_TIMEOUT` | 请求超时时间(秒) | ❌ | 30 |

## 🛠️ 可用工具

### 1. list_spreadsheets
获取用户可访问的电子表格列表

**参数**:
- `folder_token` (可选): 文件夹token，为空时获取根目录
- `page_size` (可选): 每页返回数量，默认50，最大200

### 2. get_worksheets  
获取指定电子表格的工作表列表

**参数**:
- `spreadsheet_token` (必需): 电子表格token

### 3. read_range
读取指定范围的单元格数据

**参数**:
- `spreadsheet_token` (必需): 电子表格token
- `range_spec` (必需): 范围规格，如 'sheetId!A1:B10'
- `value_render_option` (可选): 数据渲染选项，默认 'UnformattedValue'
- `date_time_render_option` (可选): 日期时间渲染选项，默认 'FormattedString'

### 4. read_multiple_ranges
批量读取多个范围的数据

**参数**:
- `spreadsheet_token` (必需): 电子表格token  
- `ranges` (必需): 范围列表数组
- `value_render_option` (可选): 数据渲染选项
- `date_time_render_option` (可选): 日期时间渲染选项

### 5. find_cells
在指定范围内查找单元格

**参数**:
- `spreadsheet_token` (必需): 电子表格token
- `sheet_id` (必需): 工作表ID
- `range_spec` (必需): 搜索范围
- `find_text` (必需): 查找文本或正则表达式
- `match_case` (可选): 是否区分大小写，默认false
- `match_entire_cell` (可选): 是否完全匹配，默认false  
- `search_by_regex` (可选): 是否使用正则表达式，默认false
- `include_formulas` (可选): 是否仅搜索公式，默认false

## ⚡ FastMCP 优势

- ✅ **自动参数验证**: 使用 Pydantic 模型自动验证输入
- ✅ **简化工具注册**: 使用装饰器模式，无需手动注册
- ✅ **内置 Schema 生成**: 自动生成 JSON Schema
- ✅ **更好的错误处理**: 内置错误处理和日志记录
- ✅ **代码减少74%**: 相比手动 MCP 实现大幅简化
- ✅ **连接稳定性**: 修复了 MCP 连接关闭问题

## 🔍 故障排除

### 连接问题
如果遇到 "Connection closed" 错误:
1. 确保使用最新的 FastMCP 版本 (v1.1.0+)
2. 检查应用凭据是否正确
3. 查看日志输出获取详细错误信息

### 工具调用失败
如果工具调用失败:
1. 检查参数格式是否正确
2. 确保必需参数都已提供
3. 验证飞书应用权限设置

### 日志调试
设置调试日志查看详细信息:
```json
{
  "env": {
    "FEISHU_LOG_LEVEL": "DEBUG"
  }
}
```

## 📚 参考文档

- [FastMCP 官方文档](https://gofastmcp.com)
- [飞书开放平台文档](https://open.feishu.cn/document/)
- [MCP 协议规范](https://modelcontextprotocol.io)

---

**版本**: 1.1.0-fastmcp  
**更新日期**: 2025-08-10  
**框架**: FastMCP