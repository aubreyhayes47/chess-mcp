# chess-mcp server (scaffold)

This directory contains the FastMCP server and chess MCP tools.

## Local development

```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
python app.py
```

## Example tool calls

Use MCP Inspector (or any MCP client) to call the tools with these sample inputs:

```json
// new_game
{
  "side": "white"
}
```

```json
// legal_moves
{
  "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
}
```

```json
// apply_move
{
  "gameId": "g_example",
  "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
  "moveUci": "e2e4"
}
```

```json
// choose_opponent_move
{
  "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
}
```

## Running tests

```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
pytest
```

## Manual test checklist

- Start the server and open MCP Inspector.
- Call `new_game`.
- Call `legal_moves` with the returned `fen`.
- Call `apply_move` with a legal move (e.g., `e2e4` from the starting position).
- Call `apply_move` with an illegal move (e.g., `e2e5` from the starting position).
- Call `choose_opponent_move` with the current `fen` and confirm it returns moves + policy.

## Notes

- Tool handlers live in `tools.py`.
- Chess rules and legality checks will live in `chess_rules.py`.
- The widget HTML template is in `templates/chess-board-v1.html`.
- The widget resource is registered in `app.py` with the URI
  `ui://widget/chess-board-v1.html` and served with
  `mimeType: text/html+skybridge`.
- To cache-bust future template changes, version the URI and template name
  (for example `ui://widget/chess-board-v2.html` plus a new
  `templates/chess-board-v2.html`) and update `app.py` accordingly.
