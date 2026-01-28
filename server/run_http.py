"""Run the MCP server over Streamable HTTP."""

from __future__ import annotations
import os
from app import app

def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")  # IMPORTANT on Render
    port = int(os.getenv("PORT", "10000"))  # Render sets PORT
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
