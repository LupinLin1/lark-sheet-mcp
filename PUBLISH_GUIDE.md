# Lark Sheet MCP - PyPI 发布指南

## 项目状态 ✅ 发布成功！
- ✅ 包已构建完成
- ✅ 质量检查通过
- ✅ 本地安装测试成功
- ✅ GitHub 代码已推送
- ✅ GitHub Release 创建完成
- ✅ **PyPI 发布成功** - 包已上线！

🎉 **项目现已在 PyPI 上可用**: https://pypi.org/project/lark-sheet-mcp/

## 手动发布到PyPI步骤

### 1. 注册PyPI账户
1. 访问 https://pypi.org/account/register/
2. 创建账户并验证邮箱

### 2. 获取API Token
1. 登录PyPI账户
2. 访问 https://pypi.org/manage/account/token/
3. 创建一个新的API Token
4. 复制生成的token（以`pypi-`开头）

### 3. 配置认证
创建 `~/.pypirc` 文件：
```ini
[distutils]
index-servers = pypi

[pypi]
username = __token__
password = pypi-你的API令牌在这里
```

### 4. 发布到PyPI
```bash
cd /Users/lupin/Dev/lark_sheet_mcp
twine upload dist/*
```

## 项目结构确认

```
lark_sheet_mcp-1.0.0/
├── src/lark_sheet_mcp/
│   ├── __init__.py
│   ├── main.py          # CLI入口点
│   ├── server.py        # MCP服务器
│   ├── config.py        # 配置管理
│   ├── models/          # 数据模型
│   ├── services/        # 服务层
│   └── tools/           # MCP工具
├── setup.py
├── pyproject.toml
├── README.md
└── LICENSE
```

## 验证发布成功

发布后，用户可以通过以下方式使用：

1. **安装包**：
   ```bash
   pip install lark-sheet-mcp
   ```

2. **MCP配置**：
   ```json
   {
     "mcpServers": {
       "lark-sheet-mcp": {
         "command": "lark-sheet-mcp",
         "args": ["--app-id", "your_app_id", "--app-secret", "your_app_secret"]
       }
     }
   }
   ```

3. **命令行使用**：
   ```bash
   lark-sheet-mcp --help
   lark-sheet-mcp --app-id your_id --app-secret your_secret
   ```

## 备用安装方式

如果PyPI发布遇到问题，用户可以：

1. **从GitHub直接安装**：
   ```bash
   pip install git+https://github.com/LupinLin1/lark-sheet-mcp.git
   ```

2. **本地wheel安装**：
   ```bash
   # 下载 dist/lark_sheet_mcp-1.0.0-py3-none-any.whl
   pip install lark_sheet_mcp-1.0.0-py3-none-any.whl
   ```

## 发布清单 ✅ 全部完成！

- [x] 项目重命名为 lark_sheet_mcp
- [x] 修复CLI入口点问题
- [x] 完善包结构和依赖
- [x] 本地安装测试通过
- [x] 构建分发包
- [x] 质量检查通过
- [x] GitHub仓库创建并推送
- [x] GitHub Release v1.0.0 创建
- [x] **PyPI发布成功** ✅

## 项目信息
- **包名**: lark-sheet-mcp
- **版本**: 1.0.0
- **作者**: Lupin
- **GitHub**: https://github.com/LupinLin1/lark-sheet-mcp
- **License**: MIT