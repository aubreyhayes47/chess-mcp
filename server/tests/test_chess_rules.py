from pathlib import Path
import sys

import chess

sys.path.append(str(Path(__file__).resolve().parents[1]))

from chess_rules import apply_uci_move, legal_moves_uci  # noqa: E402


def test_apply_uci_move_normal():
    result = apply_uci_move(chess.STARTING_FEN, "e2e4")
    assert result["legal"] is True
    assert result["fen"] != chess.STARTING_FEN
    assert result["san"] in {"e4", "e4+"}
    assert result["turn"] == "b"


def test_apply_uci_move_illegal_pinned_piece():
    fen = "4r3/8/8/8/8/8/4R3/4K3 w - - 0 1"
    result = apply_uci_move(fen, "e2a2")
    assert result["legal"] is False
    assert result["fen"] == fen
    assert result["error"]


def test_apply_uci_move_castling():
    fen = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
    result = apply_uci_move(fen, "e1g1")
    assert result["legal"] is True
    assert result["turn"] == "b"


def test_apply_uci_move_en_passant():
    fen = "8/8/8/3pP3/8/8/8/4K3 w - d6 0 1"
    result = apply_uci_move(fen, "e5d6")
    assert result["legal"] is True
    assert result["turn"] == "b"


def test_apply_uci_move_promotion():
    fen = "k7/4P3/8/8/8/8/8/4K3 w - - 0 1"
    result = apply_uci_move(fen, "e7e8q")
    assert result["legal"] is True
    assert result["uci"] == "e7e8q"


def test_apply_uci_move_checkmate():
    fen = "6k1/5Q2/6K1/8/8/8/8/8 w - - 0 1"
    result = apply_uci_move(fen, "f7g7")
    assert result["legal"] is True
    assert result["status"] == "checkmate"


def test_legal_moves_uci_starting_position():
    moves = legal_moves_uci(chess.STARTING_FEN)
    assert moves
