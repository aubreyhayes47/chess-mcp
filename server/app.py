"""FastMCP server entrypoint (scaffold only)."""

from fastmcp import FastMCP


app = FastMCP("chess-mcp")

# TODO: Register tools in tools.py with MCP metadata.
# TODO: Register the widget template resource from templates/.

if __name__ == "__main__":
    # TODO: Replace with proper ASGI server invocation for production.
    app.run()
