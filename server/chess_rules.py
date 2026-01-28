"""Chess rules helpers built on python-chess."""

from __future__ import annotations

from typing import Any
import re

import chess


MAX_FEN_LENGTH = 200
UCI_PATTERN = re.compile(r"^[a-h][1-8][a-h][1-8][qrbn]?$")


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


def _validate_fen_string(fen: str) -> str | None:
    if not isinstance(fen, str) or not fen.strip():
        return "Invalid FEN: missing"
    if len(fen) > MAX_FEN_LENGTH:
        return "Invalid FEN: too long"
    if any(ch in "\n\r\t" for ch in fen):
        return "Invalid FEN: contains control characters"
    return None


def _normalize_uci(move_uci: str) -> str:
    return move_uci.strip().lower()


def _validate_uci_string(move_uci: str) -> str | None:
    if not isinstance(move_uci, str) or not move_uci.strip():
        return "Invalid move format"
    normalized = _normalize_uci(move_uci)
    if len(normalized) not in (4, 5):
        return "Invalid move format"
    if not UCI_PATTERN.match(normalized):
        return "Invalid move format"
    return None


def apply_uci_move(fen: str, move_uci: str) -> dict[str, Any]:
    """Validate and apply a UCI move against a FEN string.

    Returns a dict containing move legality, resulting FEN, SAN, UCI, turn,
    check information, status, and an optional error.
    """
    fen_error = _validate_fen_string(fen)
    if fen_error:
        return _error_snapshot_from_fen(fen, _normalize_uci(move_uci), fen_error)

    try:
        board = chess.Board(fen)
    except ValueError as exc:
        return _error_snapshot_from_fen(
            fen,
            _normalize_uci(move_uci),
            f"Invalid FEN: {exc}",
        )

    move_error = _validate_uci_string(move_uci)
    if move_error:
        status, in_check = _status_from_board(board)
        return {
            "legal": False,
            "fen": fen,
            "san": None,
            "uci": _normalize_uci(move_uci),
            "turn": _turn_from_board(board),
            "check": in_check,
            "status": status,
            "error": move_error,
        }

    move = chess.Move.from_uci(_normalize_uci(move_uci))

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
    fen_error = _validate_fen_string(fen)
    if fen_error:
        return []
    try:
        board = chess.Board(fen)
    except ValueError:
        return []

    return [move.uci() for move in board.legal_moves]


def opponent_move_candidates(fen: str, limit: int = 200) -> list[str]:
    """Return a capped list of legal opponent moves in UCI notation."""
    moves = legal_moves_uci(fen)
    if limit > 0:
        return moves[:limit]
    return moves


def _error_snapshot_from_fen(fen: str, move_uci: str, error: str) -> dict[str, Any]:
    try:
        board = chess.Board(fen)
    except ValueError:
        return {
            "legal": False,
            "fen": fen,
            "san": None,
            "uci": _normalize_uci(move_uci),
            "turn": "w",
            "check": False,
            "status": "in_progress",
            "error": error,
        }

    status, in_check = _status_from_board(board)
    return {
        "legal": False,
        "fen": fen,
        "san": None,
        "uci": _normalize_uci(move_uci),
        "turn": _turn_from_board(board),
        "check": in_check,
        "status": status,
        "error": error,
    }


def revalidate_opponent_choice(
    fen: str,
    move_uci: str,
    allowed_moves: list[str] | None = None,
) -> tuple[bool, dict[str, Any]]:
    """Revalidate an opponent-selected move using the same rules engine."""
    normalized_move = _normalize_uci(move_uci)
    result = apply_uci_move(fen, normalized_move)
    if not result["legal"]:
        return False, result

    allowed = allowed_moves if allowed_moves is not None else legal_moves_uci(fen)
    if normalized_move not in allowed:
        return False, _error_snapshot_from_fen(
            fen,
            normalized_move,
            "Opponent move not in allowed list",
        )

    return True, result
