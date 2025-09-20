"""
Main entry point for Feishu Spreadsheet MCP server.
"""

import argparse
import asyncio
import logging
import sys
from typing import Optional

from .config import config_manager
from .server import FeishuSpreadsheetMCPServer


def run_server(
    app_id: Optional[str] = None,
    app_secret: Optional[str] = None,
    config_file: Optional[str] = None,
) -> None:
    """
    Run the FastMCP server synchronously.

    Args:
        app_id: Feishu app ID (optional, will use config file or env var if not provided)
        app_secret: Feishu app secret (optional, will use config file or env var if not provided)
        config_file: Configuration file path (optional)
    """
    try:
        # Load configuration
        config = config_manager.load_config(app_id, app_secret, config_file)

        # Setup logging
        config_manager.setup_logging()

        # Validate configuration
        if not config_manager.validate_config():
            raise ValueError("Invalid configuration")

        logger = logging.getLogger(__name__)
        logger.info(
            f"Feishu Spreadsheet MCP Server initialized with app_id: {config.app_id[:8]}..."
        )
        logger.info("Server ready to handle MCP requests")

        # Create and run server with FastMCP
        server = FeishuSpreadsheetMCPServer(config.app_id, config.app_secret)
        mcp = server.get_mcp_server()

        # Run the FastMCP server with stdio transport
        mcp.run("stdio")

    except Exception as e:
        logging.error(f"Failed to start server: {e}")
        raise


# Keep the async version for backward compatibility
async def main_async(
    app_id: Optional[str] = None,
    app_secret: Optional[str] = None,
    config_file: Optional[str] = None,
) -> None:
    """
    Async main function - calls synchronous run_server.

    Args:
        app_id: Feishu app ID (optional, will use config file or env var if not provided)
        app_secret: Feishu app secret (optional, will use config file or env var if not provided)
        config_file: Configuration file path (optional)
    """
    run_server(app_id, app_secret, config_file)


def main() -> None:
    """Main entry point for command line."""
    parser = argparse.ArgumentParser(
        description="Feishu Spreadsheet MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Configuration priority (highest to lowest):
1. Command line arguments
2. Environment variables
3. Configuration file

Environment variables:
  FEISHU_APP_ID          Feishu application ID
  FEISHU_APP_SECRET      Feishu application secret
  FEISHU_LOG_LEVEL       Log level (DEBUG, INFO, WARNING, ERROR)
  FEISHU_MAX_RETRIES     Maximum retry attempts
  FEISHU_TIMEOUT         Request timeout in seconds

Configuration file locations (searched in order):
  - ./feishu_mcp_config.json
  - ~/.feishu_mcp_config.json
  - /etc/feishu_mcp/config.json
        """,
    )

    parser.add_argument(
        "--app-id",
        help="Feishu app ID (can also use FEISHU_APP_ID env var or config file)",
    )
    parser.add_argument(
        "--app-secret",
        help="Feishu app secret (can also use FEISHU_APP_SECRET env var or config file)",
    )
    parser.add_argument("--config", help="Configuration file path (JSON format)")
    parser.add_argument(
        "--create-config",
        metavar="FILE",
        help="Create a sample configuration file and exit",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set log level (overrides config file)",
    )

    args = parser.parse_args()

    # Handle create-config command
    if args.create_config:
        try:
            config_manager.create_sample_config(args.create_config)
            print(f"Sample configuration file created: {args.create_config}")
            print("Please edit the file to set your actual Feishu app credentials.")
            sys.exit(0)
        except Exception as e:
            print(f"Failed to create config file: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        # Set log level early if specified
        if args.log_level:
            logging.basicConfig(level=getattr(logging, args.log_level))

        run_server(args.app_id, args.app_secret, args.config)

    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        print("\nRun with --help for configuration options.", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutting down server...")
        sys.exit(0)
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
