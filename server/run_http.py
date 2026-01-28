"""Run the MCP server over Streamable HTTP for local testing."""

from __future__ import annotations

import os

from app import app


def main() -> None:
    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8000"))
    path = os.getenv("MCP_PATH", "/mcp")
    app.run(
        transport="streamable-http",
        host=host,
        port=port,
        path=path,
        show_banner=False,
    )


if __name__ == "__main__":
    main()
