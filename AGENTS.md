# AGENTS.md

This file is the **single source of truth** for how coding agents should work on this repo.

Repo: **chess-mcp**
Stack preference: **Python (FastMCP)** for the MCP server, React widget for UI.
Opponent mode: **LLM constrained to legal moves**.

---

## 0) One-paragraph goal

Build a minimal ChatGPT Apps SDK app that lets a user play chess inside ChatGPT with an interactive board, **authoritative rule enforcement**, and an **LLM opponent** that is strictly constrained to choose from legal moves.

---

## 1) Definition of Done (v1)

A change is “done” when all of the following are true:

1. **Widget renders a board** from `window.openai.toolOutput.fen` inside the ChatGPT iframe.
2. User **types moves in chat** (no board interaction).
3. The model calls `apply_move` with `(gameId, fen, moveUci)` based on chat input.
4. The model renders the updated snapshot via `render_game` (the only tool that returns a widget).

   * If `legal: false`, the model reports the error and does not change the board.
5. After a legal player move, the model runs the **opponent turn loop**:

   * call `choose_opponent_move(fen)` → obtain `movesUci[]` + policy
   * model selects exactly one UCI move from the list
   * apply it via `apply_move`
   * render the result via `render_game`
6. Game over states are rendered correctly (check, checkmate, stalemate).
7. Works locally and in production behind HTTPS (e.g., Render).

---

## 2) Non‑negotiable invariants

These are hard rules. If your implementation violates them, it is wrong.

### 2.1 Canonical truth

* **Canonical state is the server-confirmed FEN** returned by tools.
* The widget must never “optimistically commit” a move.

### 2.2 LLM opponent constraints

* The LLM opponent **must choose from** a tool-provided list of legal moves.
* The server must **re-validate** the chosen move via `apply_move` before committing.

### 2.3 No game logic in prose

* No chess state transitions are inferred from chat text.
* Every state transition is derived from a tool response.

### 2.4 Payload discipline

* `structuredContent` is **small** and stable.
* Put bulky or UI-only information in `_meta` (or omit for v1).
* Never return secrets in any user-visible channel (`structuredContent`, `content`, `_meta`, widgetState).

### 2.5 Idempotency

* Tools must be **idempotent**. Assume the model/runtime may retry.
* Prefer deterministic transitions: `(fen, moveUci) → (legal, newFen)`.

### 2.6 Avoid brittle turn orchestration

* Do **not** use `window.openai.sendFollowUpMessage` as the core gameplay engine.
* Use a **single render tool** (`render_game`) per assistant turn; other tools
  should return structured content only (no widget).

---

## 3) Required MCP tool contracts (exact shapes)

Agents must implement **exactly** these tools and these JSON fields.

### 3.0 `render_game` (widget render)

Return a widget-renderable snapshot. This is the **only tool** that sets
`_meta["openai/outputTemplate"]`.

**Input**

* `snapshot`: object (must include `fen` and `gameId`, plus optional status fields)

**Output (structuredContent)**

```json
{
  "type": "chess_snapshot",
  "gameId": "g_123",
  "fen": "<FEN>",
  "status": "in_progress",
  "turn": "w"
}
```

### 3.1 `new_game`

Start a new game.

**Input**

* `side` (optional): `"white" | "black"`

**Output (structuredContent)**

```json
{
  "type": "chess_snapshot",
  "gameId": "g_123",
  "fen": "<FEN>",
  "status": "in_progress",
  "turn": "w"
}
```

### 3.2 `apply_move`

Validate and apply a single move.

**Input**

* `gameId`: string
* `fen`: string (FEN)
* `moveUci`: string (examples: `e2e4`, `e7e8q`)

**Output (structuredContent)**

```json
{
  "type": "chess_snapshot",
  "gameId": "g_123",
  "legal": true,
  "fen": "<NEW_FEN>",
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
  "fen": "<UNCHANGED_FEN>",
  "error": "Illegal move: king would be in check"
}
```

### 3.3 `legal_moves` (read-only)

Return legal moves for a position.

**Input**

* `fen`: string

**Output (structuredContent)**

```json
{
  "type": "legal_moves",
  "movesUci": ["e2e4", "g1f3"]
}
```

### 3.4 `choose_opponent_move` (LLM opponent mode)

Return the legal move list and a policy that forces a single choice.

**Input**

* `fen`: string

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

**Model-side contract**

* The model must output exactly one UCI move from `movesUci`.

**Server-side contract**

* The server must always re-validate the chosen move via `apply_move`.

---

## 4) Tool metadata requirements

Tool descriptor metadata must be set correctly (not in tool responses):

* Tools callable from the widget must set:

  * `_meta["openai/widgetAccessible"]: true`
* Only `render_game` should set:

  * `_meta["openai/outputTemplate"]`
* Read-only tools must set annotations:

  * `annotations.readOnlyHint: true` (for `legal_moves`)
* For `apply_move` (a bounded write):

  * `readOnlyHint: false`
  * `openWorldHint: false`
  * `destructiveHint: false`

---

## 5) UI template/resource requirements

* The widget must be registered as an MCP resource with:

  * `mimeType: "text/html+skybridge"`
  * `_meta["openai/widgetDomain"]` set (required for submission)
  * `_meta["openai/widgetCSP"]` allowlists for connect/resource domains
* Cache-bust template URIs on breaking changes (e.g., `...-v1.html` → `...-v2.html`).

---

## 6) Frontend (React) rules

### 6.1 State placement

* **Business state (truth):** `toolOutput.fen` returned by server tools
* **UI state (widgetState):** selection, highlights, orientation
* Do not treat `widgetState.fen` as canonical; it may be empty for new widget instances.

### 6.2 Turn loop (chat-driven)

1. User types a move in chat.
2. Model calls `apply_move`.
3. If legal → model calls `render_game` with the updated snapshot.
4. If game not over → trigger opponent:

   * call `choose_opponent_move(fen)`
   * model selects one UCI
   * call `apply_move` for opponent move
   * call `render_game` to update the widget
5. Render updated snapshot.

### 6.3 Move formatting

* Prefer UCI for all tool calls.
* Promotion must be encoded (`e7e8q`, `e2e1n`, etc.).

---

## 7) Python / FastMCP server guidance

* Prefer a small, explicit module layout:

  * `tools.py` (tool handlers)
  * `chess_rules.py` (move parsing/validation/apply)
  * `templates/` (skybridge HTML)
* You may store game history server-side keyed by `gameId` (recommended).
* Keep tool handlers deterministic and safe on retries.

Recommended Python deps:

* `python-chess` for FEN + legality + SAN/UCI conversion

---

## 8) Testing requirements

At minimum, add automated tests for `apply_move` with:

* normal moves (e2e4)
* illegal move (moving pinned piece exposing king)
* castling
* en passant
* promotion
* check/checkmate detection

Also include a short manual test checklist in the README.

---

## 9) Deliverables for any agent PR

Every PR must include:

* Updated/added code
* Notes on how to run locally
* Any schema changes documented here (AGENTS.md) and in README
* Screenshots or a short description of the UI behavior change

---

## 10) If you are unsure

When uncertain, prioritize:

1. Correctness (no desync)
2. Minimal tool surface
3. Deterministic, testable behavior

Do not add features that expand scope unless explicitly requested.
