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

## Widget build & serving

The widget bundle is built from `web/` and inlined into the skybridge template.

```bash
cd web
npm install
npm run build
```

The server reads `web/dist/widget.js` and `web/dist/widget.css` at runtime and
replaces the `/* INLINE_CSS */` and `/* INLINE_JS */` placeholders in
`server/templates/chess-board-v1.html`.

To cache-bust the widget, bump `WIDGET_VERSION` in `server/app.py` and rename the
template file (for example `chess-board-v2.html`).

### CSP for local development

By default, the widget CSP only allows the configured `WIDGET_DOMAIN` for
`connect_domains`. To allow local development against
`http://localhost:8000`, set:

```bash
export WIDGET_ALLOW_LOCALHOST=true
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

## Opponent move constraints & revalidation

The `choose_opponent_move` tool always returns a list of legal UCI moves derived
from the current FEN. By default the server returns all legal moves and caps the
list at 200 entries (rarely exceeded). The tool also provides a strict policy
object that requires the model to choose exactly one UCI move from that list.

When a model-selected move is applied, the server **must** revalidate it using
the same rules engine as `apply_move`. Use
`revalidate_opponent_choice(fen, move_uci, allowed_moves)` to enforce:

- The move is legal for the provided FEN.
- The move is present in the allowed list that was given to the model.

If the selected move is not in the allowed list, the helper returns
`legal: false` with `error: "Opponent move not in allowed list"`, and the UI or
orchestrator should call `choose_opponent_move` again to request a valid move.

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
