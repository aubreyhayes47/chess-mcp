# chess-mcp

A minimal, **capability-first** ChatGPT App that lets users play chess inside ChatGPT with a display-only board, **authoritative rule enforcement**, and an optional LLM opponent.

> Core contract: **(state, moveUci) → new_state**
>
> * **Input:** `fen` (board state) + `moveUci` (UCI)
> * **Output:** `fen` (updated board state) + game status

---

## Goals

* **Do:** Apply legal chess moves, advance turns, and keep the game consistent.
* **Show:** Render a display-only chessboard UI inside ChatGPT.
* **(Optional) Know:** Provide explanations, hints, or analysis without making the UI/logic fragile.

Non-goals (v1): full lichess-style analysis suite, accounts, matchmaking, opening explorer, etc.

---

## Architecture Overview

### Components

1. **Widget UI (React)**

   * Runs inside ChatGPT as an iframe via `text/html+skybridge`.
   * Renders the board and status from `window.openai.toolOutput`.
   * Provides chat-only instructions; the model drives all tool calls.
   * Avoids move input controls so the widget remains display-only.

2. **MCP Server (Python)**

   * Registers the UI template resource.
   * Exposes tools for starting games, validating/applying moves, and generating opponent moves.
   * Enforces **idempotency** and **authoritative transitions**.
   * Returns **small `structuredContent`** for the model + optional `_meta` for the widget.

3. **Model (ChatGPT)**

   * Orchestrates tool calls and narrates.
   * If using an LLM opponent, it must choose from tool-provided legal moves (no free-form move invention).

---

## Data Model

### Canonical State: FEN

We use **FEN (Forsyth–Edwards Notation)** as the canonical game snapshot.

Why:

* Encodes board + side to move + castling rights + en passant + move counters.
* Compact, standard, and easy to validate.

### Identifiers

* `gameId` — stable identifier for a game session.
* `openai/widgetSessionId` — provided by ChatGPT; useful for correlating calls/logs.

---

## Tooling Contracts (MCP)

Design principles:

* **Tools are authoritative**: widget never commits a move until tool confirms legality.
* **Idempotent**: tools may be retried by the model/runtime.
* **Small structuredContent**: only what the model should see.
* **UI-only bulk in _meta**: legal-move lists, long history, etc.
* **Single widget render**: only `render_game` returns the widget template.

### Tool: `render_game`

Render a widget snapshot. This is the **only tool** that sets
`openai/outputTemplate`.

**Input**

* `snapshot`: object (must include `fen` and `gameId`, plus optional status fields)

**Output (structuredContent)**

```json
{
  "type": "chess_snapshot",
  "gameId": "g_123",
  "fen": "...",
  "status": "in_progress",
  "turn": "w"
}
```

### Tool: `new_game`

Start a new chess game.

**Input**

* `side` (optional): `"white" | "black"`

**Output (structuredContent)**

```json
{
  "type": "chess_snapshot",
  "gameId": "g_123",
  "fen": "...",
  "status": "in_progress",
  "turn": "w"
}
```

### Tool: `apply_move`

Validate and apply a single move.

**Input**

* `gameId`
* `fen`
* `moveUci` (string): UCI (`e2e4`, `e7e8q`)

**Output (structuredContent)**

```json
{
  "type": "chess_snapshot",
  "gameId": "g_123",
  "legal": true,
  "fen": "...",
  "status": "in_progress",
  "turn": "b",
  "lastMove": { "uci": "e2e4", "san": "e4" },
  "check": false
}
```

If illegal:

```json
{
  "type": "chess_snapshot",
  "gameId": "g_123",
  "legal": false,
  "fen": "<unchanged>",
  "error": "Illegal move: king would be in check"
}
```

### Tool: `legal_moves` (read-only)

Return legal moves for the current position.

**Input**

* `fen`

**Output (structuredContent)**

```json
{ "type": "legal_moves", "movesUci": ["e2e4", "g1f3"] }
```

### Tool: `choose_opponent_move` (LLM opponent mode)

Select an opponent move by constraining the model to a legal-move list.

**Input**

* `fen`

**Output (structuredContent)**

```json
{
  "type": "opponent_choice",
  "movesUci": ["g8f6", "d7d5", "e7e5"],
  "policy": {
    "mustChooseFromMovesUci": true,
    "chooseExactlyOne": true
  }
}
```

**Model-side contract (enforced in server prompt)**

* The model must return exactly one UCI move from `movesUci`.
* If the model wants to resign/offer draw, it must use an explicit non-move tool (future).

**Server-side safety**

* Even after model selection, the server must re-validate by calling `apply_move(fen, moveUci)`.
* If the model outputs an illegal move, re-run `choose_opponent_move` with a stricter instruction and/or reduce the candidate list.

### Tool: `play_turn` (optional convenience)

Atomic “player move then opponent move” to minimize round trips.

**Input**

* `gameId`
* `fen`
* `playerMove`

**Output**

* Updated snapshot + opponent move info

---

## Widget UI

### Responsibilities

* Render chessboard and status from `toolOutput.fen`.
* Provide chat-first instructions so users type moves in the conversation.
* Avoid local move input and rely on tool-confirmed updates.

### State Placement

* **Business data (truth):** MCP server / tool outputs (`fen`, `status`, `history`)
* **UI state (ephemeral):** optional, for display-only preferences
* **Cross-session preferences (optional):** your backend DB

### React runtime integration

Use `useOpenAiGlobal("toolOutput")` to keep the widget reactive.

### UI manual test checklist

* Build the widget bundle: `cd web && npm install && npm run build`.
* Start a new game via chat (model calls `new_game`).
* Type a legal move in chat and confirm the model renders the update via `render_game`.
* Type an illegal move in chat and confirm the model reports the error with no board change.
* After a legal move, confirm the opponent move appears after the model runs the opponent loop.
* Reach a game end state (checkmate/stalemate/check) and confirm status renders.

### Local E2E (Playwright)

This runs the widget against the real MCP server using a local MCP client
bridge (no ChatGPT required), using Playwright's Python package.

Prereqs:

* Python deps: `./.venv/bin/pip install -e server`
* Playwright (Python): `./.venv/bin/pip install -r e2e/requirements.txt`
* Playwright browsers: `./.venv/bin/python -m playwright install --with-deps`

Run:

```bash
./.venv/bin/pytest e2e/test_widget_e2e.py
```

Notes:

* The test runner builds the widget and starts the MCP server automatically.
* Server runs on `http://127.0.0.1:8000/mcp` via `server/run_http.py`.

---

## Turn Loop

1. User types a move in chat.
2. Model parses input into UCI (or uses `legal_moves` to disambiguate).
3. Model calls `apply_move({ gameId, fen, moveUci })`.
4. If illegal → model reports error.
5. If legal → model calls `render_game` to render the new snapshot.
6. Opponent step (choose one):

   * **LLM opponent:** call `choose_opponent_move(fen)` then `apply_move`.
   * **Engine opponent:** call `get_best_move(fen)` then `apply_move`.
7. Render updated snapshot with `render_game`, checkmate/stalemate if reached.

## Chat-driven move parsing

* The model should parse user input into UCI moves.
* If the input is ambiguous or invalid, call `legal_moves` and ask for clarification.
* Always call `apply_move` to validate and update FEN (no optimistic updates).

---

## Repo Layout

```
chess-mcp/
  server/
    app.py                 # MCP server (FastMCP/FastAPI)
    chess_rules.py         # move parsing + legality + FEN transitions
    storage.py             # optional: gameId → state/history persistence
    templates/
      chess-board-v1.html  # text/html+skybridge wrapper
  web/
    src/
      App.jsx              # React widget
      hooks/
        useOpenAiGlobal.js
    dist/
      widget.js            # bundled JS (inlined into template)
      widget.css           # bundled CSS (inlined into template)
  README.md
```

---

## Widget build & serving (Task 6)

The FastMCP server embeds the built widget bundle directly into the skybridge
HTML template.

### Build the widget

```bash
cd web
npm install
npm run build
```

Build output lives in `web/dist/`:

* `web/dist/widget.js`
* `web/dist/widget.css`

### How the server loads the widget

* `server/app.py` reads the bundle from `web/dist/`.
* `server/templates/chess-board-v1.html` contains placeholders for inline CSS and JS:
  * `/* INLINE_CSS */`
  * `/* INLINE_JS */`
* The server replaces those markers at runtime and returns a single
  `text/html+skybridge` document with `<style>` and `<script type="module">`.

### CSP configuration

`openai/widgetCSP` is set by the server. The only required allowance is the
server origin itself in `connect_domains`. Since the bundle is inlined, there
are no external resource domains to allowlist. For local development, set
`WIDGET_ALLOW_LOCALHOST=true` to include `http://localhost:8000` in the CSP
`connect_domains` list.

### Cache-busting the template URI

When you make breaking widget changes, bump the version in `server/app.py`:

* `WIDGET_VERSION = "v1"` → `"v2"`
* Template file name: `server/templates/chess-board-v1.html` → `chess-board-v2.html`
* Template URI updates automatically: `ui://widget/chess-board-v2.html`

---

## Deployment (Render)

* Deploy `server/` as a web service with HTTPS.
* Ensure the widget resource sets:

  * `openai/widgetDomain`
  * `openai/widgetCSP.connect_domains` (your Render domain)
  * `resource_domains` (if loading assets from a CDN)
* Cache-bust UI template URIs when updating bundles:

  * `ui://widget/chess-board-v1.html` → `...-v2.html`

---

## Security & Reliability

* Never return secrets in `structuredContent`, `content`, `_meta`, or widgetState.
* Mark read-only tools with `annotations.readOnlyHint: true`.
* Keep `structuredContent` small; put bulky data in `_meta`.
* Treat `(fen, moveUci)` as a deterministic transition for idempotency.

---

## Roadmap

* v1: legal play + widget board + LLM opponent constrained to legal moves
* v1.1: move history, undo, resign, new game
* v1.2: hints (top-3 candidate moves), basic eval
* v2: puzzles mode, lessons, openings, analysis view in fullscreen
