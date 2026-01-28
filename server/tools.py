"""MCP tool handlers for chess-mcp."""

from __future__ import annotations

import uuid
from typing import Literal

import chess
from fastmcp import FastMCP
from fastmcp.tools.tool import ToolResult

from chess_rules import apply_uci_move, legal_moves_uci, opponent_move_candidates

WIDGET_TEMPLATE_URI = "ui://widget/chess-board-v1.html"
OPPONENT_MOVE_CAP = 200


def _tool_meta(
    *,
    include_output_template: bool = False,
    widget_accessible: bool = False,
) -> dict[str, object]:
    meta: dict[str, object] = {}
    if include_output_template:
        meta["openai/outputTemplate"] = WIDGET_TEMPLATE_URI
    if widget_accessible:
        meta["openai/widgetAccessible"] = True
    return meta


def register_tools(app: FastMCP) -> None:
    """Register MCP tools on the provided FastMCP app instance."""

    @app.tool(
        name="render_game",
        description="Render the chess widget for the provided snapshot.",
        meta=_tool_meta(include_output_template=True),
    )
    def render_game(snapshot: dict) -> ToolResult:
        if not isinstance(snapshot, dict):
            payload = {
                "type": "chess_snapshot",
                "gameId": "unknown",
                "fen": "",
                "status": "in_progress",
                "turn": "w",
                "legal": False,
                "error": "Invalid snapshot payload.",
            }
            return ToolResult(content=[], structured_content=payload)
        snapshot_payload = {**snapshot}
        snapshot_payload.setdefault("type", "chess_snapshot")
        return ToolResult(content=[], structured_content=snapshot_payload)

    @app.tool(
        name="new_game",
        description="Start a new chess game for chat-driven play.",
        meta=_tool_meta(),
    )
    def new_game(side: Literal["white", "black"] | None = None) -> ToolResult:
        board = chess.Board()
        if side == "black":
            board.turn = chess.BLACK
        game_id = f"g_{uuid.uuid4().hex}"
        payload = {
            "type": "chess_snapshot",
            "gameId": game_id,
            "fen": board.fen(),
            "status": "in_progress",
            "turn": "w" if board.turn == chess.WHITE else "b",
        }
        return ToolResult(content=[], structured_content=payload)

    @app.tool(
        name="apply_move",
        description=(
            "Validate and apply a UCI move to the provided FEN. Intended for the "
            "model to call after the user types a move in chat."
        ),
        meta=_tool_meta(),
        annotations={
            "readOnlyHint": False,
            "openWorldHint": False,
            "destructiveHint": False,
        },
    )
    def apply_move(gameId: str, fen: str, moveUci: str) -> ToolResult:  # noqa: N803
        result = apply_uci_move(fen, moveUci)
        if not result["legal"]:
            payload = {
                "type": "chess_snapshot",
                "gameId": gameId,
                "legal": False,
                "fen": result["fen"],
                "error": result["error"],
            }
            return ToolResult(content=[], structured_content=payload)

        payload = {
            "type": "chess_snapshot",
            "gameId": gameId,
            "legal": True,
            "fen": result["fen"],
            "status": result["status"],
            "turn": result["turn"],
            "lastMove": {"uci": result["uci"], "san": result["san"]},
            "check": result["check"],
        }
        return ToolResult(content=[], structured_content=payload)

    @app.tool(
        name="legal_moves",
        description=(
            "List legal moves for a given FEN so the model can interpret chat "
            "input."
        ),
        meta=_tool_meta(),
        annotations={"readOnlyHint": True},
    )
    def legal_moves(fen: str) -> ToolResult:
        payload = {
            "type": "legal_moves",
            "movesUci": legal_moves_uci(fen),
        }
        return ToolResult(content=[], structured_content=payload)

    @app.tool(
        name="choose_opponent_move",
        description=(
            "Return legal moves and opponent selection policy for the "
            "model-driven opponent turn loop."
        ),
        meta=_tool_meta(),
    )
    def choose_opponent_move(fen: str) -> ToolResult:
        moves = opponent_move_candidates(fen, limit=OPPONENT_MOVE_CAP)
        content = []
        if not moves:
            content = [
                {
                    "type": "text",
                    "text": "No legal moves available; the game is over.",
                }
            ]
        payload = {
            "type": "opponent_choice",
            "movesUci": moves,
            "policy": {
                "mustChooseFromMovesUci": True,
                "chooseExactlyOne": True,
            },
        }
        return ToolResult(content=content, structured_content=payload)
