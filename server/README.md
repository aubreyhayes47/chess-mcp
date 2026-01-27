# chess-mcp server (scaffold)

This directory contains the FastMCP server scaffold. No chess logic or tools
are implemented yet.

## Local development

```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
python app.py
```

## Notes

- Tool handlers will live in `tools.py`.
- Chess rules and legality checks will live in `chess_rules.py`.
- The widget HTML template is in `templates/chess-board-v1.html`.
- The widget resource is registered in `app.py` with the URI
  `ui://widget/chess-board-v1.html` and served with
  `mimeType: text/html+skybridge`.
- To cache-bust future template changes, version the URI and template name
  (for example `ui://widget/chess-board-v2.html` plus a new
  `templates/chess-board-v2.html`) and update `app.py` accordingly.
