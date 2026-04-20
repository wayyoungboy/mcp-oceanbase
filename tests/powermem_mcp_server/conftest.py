import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--base-url",
        default="http://localhost:8000/mcp",
        help="PowerMem MCP server base URL",
    )
