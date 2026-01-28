import { useEffect, useMemo, useRef, useState } from "react";
import "./app.css";
import { useOpenAiGlobal } from "./hooks/useOpenAiGlobal";
import { useWidgetState } from "./hooks/useWidgetState";

const FILES = ["a", "b", "c", "d", "e", "f", "g", "h"];
const RANKS = ["8", "7", "6", "5", "4", "3", "2", "1"];
const PIECES = {
  p: "♟",
  r: "♜",
  n: "♞",
  b: "♝",
  q: "♛",
  k: "♚",
  P: "♙",
  R: "♖",
  N: "♘",
  B: "♗",
  Q: "♕",
  K: "♔",
};

const STATUS_LABELS = {
  in_progress: "In progress",
  check: "Check",
  checkmate: "Checkmate",
  stalemate: "Stalemate",
};

const normalizeToolOutput = (toolOutput) => {
  if (!toolOutput) {
    return null;
  }
  if (toolOutput.structuredContent) {
    return toolOutput.structuredContent;
  }
  return toolOutput;
};

const isSnapshotPayload = (payload) =>
  payload?.type === "chess_snapshot" && typeof payload?.fen === "string";

const parseFenBoard = (fen) => {
  if (!fen) {
    return Array.from({ length: 8 }, () => Array(8).fill(null));
  }
  const [boardPart] = fen.split(" ");
  const rows = boardPart.split("/");
  return rows.map((row) => {
    const squares = [];
    for (const char of row) {
      const count = Number(char);
      if (Number.isInteger(count) && count > 0) {
        for (let i = 0; i < count; i += 1) {
          squares.push(null);
        }
      } else {
        squares.push(char);
      }
    }
    return squares;
  });
};

const squareToIndices = (square) => {
  const file = square[0];
  const rank = square[1];
  return {
    fileIndex: FILES.indexOf(file),
    rankIndex: RANKS.indexOf(rank),
  };
};

const getPieceAtSquare = (board, square) => {
  const { fileIndex, rankIndex } = squareToIndices(square);
  if (rankIndex < 0 || fileIndex < 0) {
    return null;
  }
  return board[rankIndex]?.[fileIndex] ?? null;
};

const isPieceForTurn = (piece, turn) => {
  if (!piece) {
    return false;
  }
  const isWhitePiece = piece === piece.toUpperCase();
  return turn === "w" ? isWhitePiece : !isWhitePiece;
};

const buildUciMove = (from, to, piece, turn) => {
  let uci = `${from}${to}`;
  if (!piece) {
    return uci;
  }
  const isPawn = piece.toLowerCase() === "p";
  if (!isPawn) {
    return uci;
  }
  const promotionRank = turn === "w" ? "8" : "1";
  if (to[1] === promotionRank) {
    uci += "q";
  }
  return uci;
};

const getStatusLabel = (snapshot) => {
  if (!snapshot) {
    return "No game";
  }
  return STATUS_LABELS[snapshot.status] || snapshot.status || "Unknown";
};

export default function App() {
  const toolOutput = useOpenAiGlobal("toolOutput");
  const latestPayload = normalizeToolOutput(toolOutput);
  const snapshot = isSnapshotPayload(latestPayload) ? latestPayload : null;
  const [widgetState, setWidgetState] = useWidgetState({
    orientation: "white",
    selectedSquare: null,
  });
  const [errorMessage, setErrorMessage] = useState("");
  const [opponentError, setOpponentError] = useState(false);
  const [isApplyingMove, setIsApplyingMove] = useState(false);
  const [isOpponentThinking, setIsOpponentThinking] = useState(false);
  const newGameRequested = useRef(false);

  const isWaitingForTool =
    !isSnapshotPayload(latestPayload) && latestPayload !== null;

  useEffect(() => {
    const handleError = (event) => {
      const message = event?.error?.message || event?.message || "Unknown error";
      // eslint-disable-next-line no-console
      console.error("Widget runtime error:", message, event?.error || event);
    };
    const handleRejection = (event) => {
      const reason = event?.reason;
      // eslint-disable-next-line no-console
      console.error("Widget unhandled rejection:", reason || event);
    };
    window.addEventListener("error", handleError);
    window.addEventListener("unhandledrejection", handleRejection);
    return () => {
      window.removeEventListener("error", handleError);
      window.removeEventListener("unhandledrejection", handleRejection);
    };
  }, []);

  const board = useMemo(
    () => parseFenBoard(snapshot?.fen),
    [snapshot?.fen]
  );

  const orientation = widgetState.orientation || "white";
  const displayFiles =
    orientation === "white" ? FILES : [...FILES].reverse();
  const displayRanks =
    orientation === "white" ? RANKS : [...RANKS].reverse();

  const startNewGame = async () => {
    setErrorMessage("");
    setOpponentError(false);
    setIsOpponentThinking(false);
    setIsApplyingMove(true);
    try {
      if (!window.openai?.callTool) {
        throw new Error("window.openai.callTool is not available.");
      }
      await window.openai.callTool({ name: "new_game", arguments: {} });
    } catch (error) {
      setErrorMessage(error?.message || "Failed to start a new game.");
    } finally {
      setIsApplyingMove(false);
    }
  };

  useEffect(() => {
    if (snapshot?.fen || newGameRequested.current) {
      return;
    }
    newGameRequested.current = true;
    void startNewGame();
  }, [snapshot?.fen]);

  const updateWidgetState = (updates) => {
    setWidgetState((current) => ({ ...current, ...updates }));
  };

  const clearSelection = () => {
    updateWidgetState({ selectedSquare: null });
  };

  const handleOpponentTurn = async (currentFen, gameId) => {
    setIsOpponentThinking(true);
    setErrorMessage("");
    setOpponentError(false);
    try {
      if (!window.openai?.callTool) {
        throw new Error("window.openai.callTool is not available.");
      }
      const opponentChoice = await window.openai.callTool({
        name: "choose_opponent_move",
        arguments: { fen: currentFen },
      });
      const opponentPayload = normalizeToolOutput(opponentChoice);
      const moves = opponentPayload?.movesUci || [];
      if (!moves.length) {
        setErrorMessage(
          opponentPayload?.error ||
            "Opponent has no legal moves. The game may be over."
        );
        setOpponentError(true);
        return;
      }

      if (typeof window.openai?.selectMoveFromList !== "function") {
        setErrorMessage(
          "LLM move selection is unavailable. Unable to choose an opponent move."
        );
        setOpponentError(true);
        return;
      }

      const selectedMove = await window.openai.selectMoveFromList(moves);
      if (!selectedMove) {
        setErrorMessage("Opponent did not select a move.");
        setOpponentError(true);
        return;
      }

      if (!moves.includes(selectedMove)) {
        setErrorMessage(
          "Opponent move selection was invalid. Please retry the opponent move."
        );
        setOpponentError(true);
        return;
      }

      const opponentResult = await window.openai.callTool({
        name: "apply_move",
        arguments: {
          gameId,
          fen: currentFen,
          moveUci: selectedMove,
        },
      });
      const opponentSnapshot = normalizeToolOutput(opponentResult);
      if (opponentSnapshot?.legal === false) {
        setErrorMessage(opponentSnapshot?.error || "Opponent move was illegal.");
        setOpponentError(true);
      }
    } catch (error) {
      setErrorMessage(
        error?.message || "Failed to compute opponent move. Please retry."
      );
      setOpponentError(true);
    } finally {
      setIsOpponentThinking(false);
    }
  };

  const handleSquareClick = async (square) => {
    if (!snapshot?.fen || !snapshot?.gameId) {
      return;
    }
    if (isApplyingMove || isOpponentThinking) {
      return;
    }
    const selectedSquare = widgetState.selectedSquare;
    const pieceAtSquare = getPieceAtSquare(board, square);

    if (!selectedSquare) {
      if (!pieceAtSquare || !isPieceForTurn(pieceAtSquare, snapshot.turn)) {
        return;
      }
      updateWidgetState({ selectedSquare: square });
      return;
    }

    if (selectedSquare === square) {
      clearSelection();
      return;
    }

    const movingPiece = getPieceAtSquare(board, selectedSquare);
    const moveUci = buildUciMove(
      selectedSquare,
      square,
      movingPiece,
      snapshot.turn
    );
    clearSelection();
    setIsApplyingMove(true);
    setErrorMessage("");
    setOpponentError(false);
    try {
      if (!window.openai?.callTool) {
        throw new Error("window.openai.callTool is not available.");
      }
      const result = await window.openai.callTool({
        name: "apply_move",
        arguments: {
          gameId: snapshot.gameId,
          fen: snapshot.fen,
          moveUci,
        },
      });
      const resultSnapshot = normalizeToolOutput(result);
      if (resultSnapshot?.legal === false) {
        setErrorMessage(resultSnapshot?.error || "Illegal move.");
        setOpponentError(false);
        return;
      }
      const shouldOpponentMove =
        resultSnapshot &&
        !["checkmate", "stalemate"].includes(resultSnapshot.status);
      if (shouldOpponentMove) {
        await handleOpponentTurn(resultSnapshot?.fen, resultSnapshot?.gameId);
      }
    } catch (error) {
      setErrorMessage(error?.message || "Failed to apply move.");
    } finally {
      setIsApplyingMove(false);
    }
  };

  const handleRetryOpponent = async () => {
    if (!snapshot?.fen || !snapshot?.gameId) {
      return;
    }
    await handleOpponentTurn(snapshot.fen, snapshot.gameId);
  };

  const flipBoard = () => {
    updateWidgetState({
      orientation: orientation === "white" ? "black" : "white",
    });
  };

  return (
    <main className="app">
      <header className="app__header">
        <div>
          <h1>Chess MCP</h1>
          <p className="app__subtitle">
            Play a legal move. The server confirms every move before the board
            updates.
          </p>
        </div>
        <div className="app__actions">
          <button
            className="button"
            onClick={startNewGame}
            disabled={isApplyingMove || isOpponentThinking}
          >
            New Game
          </button>
          <button className="button button--secondary" onClick={flipBoard}>
            Flip Board
          </button>
        </div>
      </header>

      <section className="status">
        <div>
          <strong>Status:</strong> {getStatusLabel(snapshot)}
        </div>
        <div>
          <strong>Turn:</strong> {snapshot?.turn || "-"}
        </div>
        <div>
          <strong>Last move:</strong>{" "}
          {snapshot?.lastMove?.san || snapshot?.lastMove?.uci || "-"}
        </div>
        <div>
          <strong>Check:</strong> {snapshot?.check ? "Yes" : "No"}
        </div>
      </section>

      {errorMessage ? (
        <div className="alert">
          <span>{errorMessage}</span>
          <button
            className="link"
            onClick={() => {
              setErrorMessage("");
              setOpponentError(false);
            }}
          >
            OK
          </button>
        </div>
      ) : null}

      <section className="board-wrapper">
        {isWaitingForTool ? (
          <div className="board board--waiting" role="status">
            <p>Your opponent is thinking...</p>
          </div>
        ) : (
          <div className="board" role="grid" aria-label="Chess board">
            {displayRanks.map((rank, rankIndex) =>
              displayFiles.map((file, fileIndex) => {
                const square = `${file}${rank}`;
                const piece = getPieceAtSquare(board, square);
                const isDark = (rankIndex + fileIndex) % 2 === 1;
                const isSelected = widgetState.selectedSquare === square;
                return (
                  <button
                    key={square}
                    type="button"
                    className={`square ${
                      isDark ? "square--dark" : "square--light"
                    } ${isSelected ? "square--selected" : ""}`}
                    onClick={() => handleSquareClick(square)}
                    aria-label={`Square ${square}`}
                  >
                    <span className="piece">{piece ? PIECES[piece] : ""}</span>
                    <span className="coord">
                      {fileIndex === 0 ? rank : ""}
                      {rankIndex === 7 ? file : ""}
                    </span>
                  </button>
                );
              })
            )}
          </div>
        )}
        <div className="board-meta">
          {isApplyingMove ? "Applying move..." : null}
          {isOpponentThinking ? "Opponent thinking..." : null}
          {!isApplyingMove && !isOpponentThinking ? (
            <span>Click a piece, then a destination square.</span>
          ) : null}
          <p className="board-note">
            Promotions default to queen for now. TODO: add a promotion picker.
          </p>
          {opponentError ? (
            <button
              className="button button--secondary"
              onClick={handleRetryOpponent}
            >
              Retry opponent move
            </button>
          ) : null}
        </div>
      </section>
    </main>
  );
}
