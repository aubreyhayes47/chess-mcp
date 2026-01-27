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
