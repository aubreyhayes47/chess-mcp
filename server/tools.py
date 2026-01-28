"""MCP tool handlers for chess-mcp."""

from __future__ import annotations

import uuid
from typing import Literal

import chess
from fastmcp import FastMCP
from fastmcp.tools.tool import ToolResult

try:
    from .chess_rules import apply_uci_move, legal_moves_uci
except ImportError:
    from chess_rules import apply_uci_move, legal_moves_uci

WIDGET_TEMPLATE_URI = "ui://widget/chess-board-v1.html"


def _tool_meta(widget_accessible: bool) -> dict[str, object]:
    meta: dict[str, object] = {"openai/outputTemplate": WIDGET_TEMPLATE_URI}
    if widget_accessible:
        meta["openai/widgetAccessible"] = True
    return meta


def register_tools(app: FastMCP) -> None:
    """Register MCP tools on the provided FastMCP app instance."""

    @app.tool(
        name="new_game",
        description="Start a new chess game.",
        meta=_tool_meta(widget_accessible=True),
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
        description="Validate and apply a UCI move to the provided FEN.",
        meta=_tool_meta(widget_accessible=True),
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
        description="List legal moves for a given FEN.",
        meta=_tool_meta(widget_accessible=True),
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
        description="Return legal moves and opponent selection policy.",
        meta=_tool_meta(widget_accessible=True),
    )
    def choose_opponent_move(fen: str) -> ToolResult:
        moves = legal_moves_uci(fen)
        if not moves:
            # Terminal position: no legal moves available
            payload = {
                "type": "opponent_choice",
                "movesUci": [],
                "error": "No legal moves available (terminal position)",
            }
        else:
            payload = {
                "type": "opponent_choice",
                "movesUci": moves,
                "policy": {
                    "mustChooseFromMovesUci": True,
                    "chooseExactlyOne": True,
                },
            }
        return ToolResult(content=[], structured_content=payload)
