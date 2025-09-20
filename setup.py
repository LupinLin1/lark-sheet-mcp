"""
Setup configuration for Feishu Spreadsheet MCP server.
"""

from setuptools import setup, find_packages
import os

# Read README for long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="lark-sheet-mcp",
    version="1.0.1",
    author="Lupin",
    author_email="lupin@example.com",
    description="A Model Context Protocol (MCP) server for accessing Feishu/Lark spreadsheet data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/lupin/lark-sheet-mcp",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
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
        "aiohttp>=3.8.0",
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
            "lark-sheet-mcp=lark_sheet_mcp.main:main",
        ],
    },
    keywords="feishu lark spreadsheet mcp model-context-protocol api",
    project_urls={
        "Bug Reports": "https://github.com/lupin/lark-sheet-mcp/issues",
        "Source": "https://github.com/lupin/lark-sheet-mcp",
        "Documentation": "https://github.com/lupin/lark-sheet-mcp#readme",
    },
    include_package_data=True,
    zip_safe=False,
)