"""FastMCP server entrypoint (Task 1: widget resource only)."""

from __future__ import annotations

import os
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ResourceError
from mcp.server.lowlevel.helper_types import ReadResourceContents

from tools import register_tools

WIDGET_VERSION = "v1"
WIDGET_URI = f"ui://widget/chess-board-{WIDGET_VERSION}.html"
WIDGET_MIME_TYPE = "text/html+skybridge"
WIDGET_DOMAIN = os.getenv("WIDGET_DOMAIN", "https://chess-mcp.example.com")
ALLOW_LOCALHOST = os.getenv("WIDGET_ALLOW_LOCALHOST", "false").lower() in {
    "1",
    "true",
    "yes",
}
connect_domains = [WIDGET_DOMAIN]
if ALLOW_LOCALHOST:
    connect_domains.append("http://localhost:8000")

WIDGET_CSP = {
    "connect_domains": connect_domains,
    "resource_domains": [],
}
WIDGET_BUILD_DIR = Path(__file__).resolve().parents[1] / "web" / "dist"
WIDGET_TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / f"chess-board-{WIDGET_VERSION}.html"
WIDGET_JS_PATH = WIDGET_BUILD_DIR / "widget.js"
WIDGET_CSS_PATH = WIDGET_BUILD_DIR / "widget.css"

app = FastMCP("chess-mcp")
register_tools(app)


@app.resource(WIDGET_URI, mime_type=WIDGET_MIME_TYPE)
def chess_widget_template() -> str:
    if not WIDGET_TEMPLATE_PATH.exists():
        raise ResourceError(
            f"Widget template not found at {WIDGET_TEMPLATE_PATH}. "
            "Ensure the template exists and the URI version matches."
        )
    if not WIDGET_JS_PATH.exists() or not WIDGET_CSS_PATH.exists():
        raise ResourceError(
            "Widget build artifacts are missing. "
            "Run `npm install && npm run build` in the web/ directory "
            "to generate web/dist/widget.js and web/dist/widget.css."
        )

    template = WIDGET_TEMPLATE_PATH.read_text(encoding="utf-8")
    css = WIDGET_CSS_PATH.read_text(encoding="utf-8")
    js = WIDGET_JS_PATH.read_text(encoding="utf-8")

    if "/* INLINE_CSS */" not in template or "/* INLINE_JS */" not in template:
        raise ResourceError(
            "Widget template placeholders are missing. "
            "Expected /* INLINE_CSS */ and /* INLINE_JS */ markers."
        )

    return (
        template.replace("/* INLINE_CSS */", css)
        .replace("/* INLINE_JS */", js)
    )


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
