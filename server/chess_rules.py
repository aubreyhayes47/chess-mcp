"""Chess rules helpers built on python-chess."""

from __future__ import annotations

from typing import Any

import chess


def _status_from_board(board: chess.Board) -> tuple[str, bool]:
    """Return (status, in_check) for the current board state."""
    if board.is_checkmate():
        return "checkmate", True
    if board.is_stalemate():
        return "stalemate", False
    if board.is_check():
        return "check", True
    return "in_progress", False


def _turn_from_board(board: chess.Board) -> str:
    return "w" if board.turn == chess.WHITE else "b"


def apply_uci_move(fen: str, move_uci: str) -> dict[str, Any]:
    """Validate and apply a UCI move against a FEN string.

    Returns a dict containing move legality, resulting FEN, SAN, UCI, turn,
    check information, status, and an optional error.
    """
    try:
        board = chess.Board(fen)
    except ValueError as exc:
        return {
            "legal": False,
            "fen": fen,
            "san": None,
            "uci": move_uci.lower(),
            "turn": "w",
            "check": False,
            "status": "in_progress",
            "error": f"Invalid FEN: {exc}",
        }

    try:
        move = chess.Move.from_uci(move_uci)
    except ValueError:
        status, in_check = _status_from_board(board)
        return {
            "legal": False,
            "fen": fen,
            "san": None,
            "uci": move_uci.lower(),
            "turn": _turn_from_board(board),
            "check": in_check,
            "status": status,
            "error": "Invalid move format",
        }

    if not board.is_legal(move):
        status, in_check = _status_from_board(board)
        return {
            "legal": False,
            "fen": fen,
            "san": None,
            "uci": move.uci(),
            "turn": _turn_from_board(board),
            "check": in_check,
            "status": status,
            "error": "Illegal move",
        }

    san = board.san(move)
    board.push(move)
    status, in_check = _status_from_board(board)
    return {
        "legal": True,
        "fen": board.fen(),
        "san": san,
        "uci": move.uci(),
        "turn": _turn_from_board(board),
        "check": in_check,
        "status": status,
        "error": None,
    }


def legal_moves_uci(fen: str) -> list[str]:
    """Return legal moves in UCI notation for a given FEN."""
    try:
        board = chess.Board(fen)
    except ValueError:
        return []

    return [move.uci() for move in board.legal_moves]
