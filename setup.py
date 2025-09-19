"""
Setup configuration for Feishu Spreadsheet MCP server.
"""

from setuptools import setup, find_packages
import os

# Read README for long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="feishu-spreadsheet-mcp",
    version="1.0.0",
    author="MCP Development Team",
    author_email="dev@example.com",
    description="A Model Context Protocol (MCP) server for accessing Feishu/Lark spreadsheet data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/example/feishu-spreadsheet-mcp",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business :: Financial :: Spreadsheet",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    python_requires=">=3.8",
    install_requires=[
        "fastmcp>=0.9.0",
        "pydantic>=2.0.0", 
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "isort>=5.12.0",
            "pytest-mock>=3.10.0",
            "responses>=0.23.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "feishu-spreadsheet-mcp=feishu_spreadsheet_mcp.main:main",
        ],
    },
    keywords="feishu lark spreadsheet mcp model-context-protocol api",
    project_urls={
        "Bug Reports": "https://github.com/example/feishu-spreadsheet-mcp/issues",
        "Source": "https://github.com/example/feishu-spreadsheet-mcp",
        "Documentation": "https://github.com/example/feishu-spreadsheet-mcp#readme",
    },
    include_package_data=True,
    zip_safe=False,
)