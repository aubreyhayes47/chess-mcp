"""Tests for MCP tool handlers."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest
from fastmcp import FastMCP

sys.path.append(str(Path(__file__).resolve().parents[1]))

from tools import register_tools  # noqa: E402


@pytest.fixture
def app():
    """Create a FastMCP app with tools registered."""
    mcp_app = FastMCP("test-chess-mcp")
    register_tools(mcp_app)
    return mcp_app


def test_choose_opponent_move_normal_position(app):
    """Test choose_opponent_move returns policy with legal moves for normal position."""
    # Starting position should have 20 legal moves
    normal_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    
    # Get the tool function directly
    tool = app._tool_manager._tools["choose_opponent_move"]
    result = tool.fn(fen=normal_fen)
    
    payload = result.structured_content
    assert payload["type"] == "opponent_choice"
    assert len(payload["movesUci"]) == 20
    assert "policy" in payload
    assert payload["policy"]["mustChooseFromMovesUci"] is True
    assert payload["policy"]["chooseExactlyOne"] is True
    assert "error" not in payload


def test_choose_opponent_move_checkmate_position(app):
    """Test choose_opponent_move returns error for checkmate position."""
    # Fool's mate - white is checkmated
    checkmate_fen = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"
    
    tool = app._tool_manager._tools["choose_opponent_move"]
    result = tool.fn(fen=checkmate_fen)
    
    payload = result.structured_content
    assert payload["type"] == "opponent_choice"
    assert payload["movesUci"] == []
    assert "error" in payload
    assert "terminal position" in payload["error"].lower()
    assert "policy" not in payload


def test_choose_opponent_move_stalemate_position(app):
    """Test choose_opponent_move returns error for stalemate position."""
    # Stalemate position - black king has no legal moves but is not in check
    stalemate_fen = "7k/8/6Q1/8/8/8/8/K7 b - - 0 1"
    
    tool = app._tool_manager._tools["choose_opponent_move"]
    result = tool.fn(fen=stalemate_fen)
    
    payload = result.structured_content
    assert payload["type"] == "opponent_choice"
    assert payload["movesUci"] == []
    assert "error" in payload
    assert "terminal position" in payload["error"].lower()
    assert "policy" not in payload
