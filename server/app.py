"""FastMCP server entrypoint (Task 1: widget resource only)."""

from __future__ import annotations

from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ResourceError
from mcp.server.lowlevel.helper_types import ReadResourceContents

from .tools import register_tools

WIDGET_URI = "ui://widget/chess-board-v1.html"
WIDGET_MIME_TYPE = "text/html+skybridge"
WIDGET_DOMAIN = "https://chess-mcp.example.com"
WIDGET_CSP = {
    "connect_domains": ["http://localhost:3000"],
    "resource_domains": ["https://*.oaistatic.com"],
}

app = FastMCP("chess-mcp")
register_tools(app)


@app.resource(WIDGET_URI, mime_type=WIDGET_MIME_TYPE)
def chess_widget_template() -> str:
    template_path = Path(__file__).resolve().parent / "templates" / "chess-board-v1.html"
    return template_path.read_text(encoding="utf-8")


@app._mcp_server.read_resource()
async def read_resource(uri: str):
    resource = await app._resource_manager.get_resource(uri)
    if not resource:
        raise ResourceError(f"Unknown resource: {uri}")

    content = await resource.read()
    meta = None
    if str(uri) == WIDGET_URI:
        meta = {
            "openai/widgetDomain": WIDGET_DOMAIN,
            "openai/widgetCSP": WIDGET_CSP,
        }

    return [
        ReadResourceContents(
            content=content,
            mime_type=resource.mime_type,
            meta=meta,
        )
    ]

if __name__ == "__main__":
    # TODO: Replace with proper ASGI server invocation for production.
    app.run()
