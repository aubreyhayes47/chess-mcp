import { useEffect, useMemo } from "react";
import "./app.css";
import { useOpenAiGlobal } from "./hooks/useOpenAiGlobal";

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

  const orientation = "white";
  const displayFiles =
    orientation === "white" ? FILES : [...FILES].reverse();
  const displayRanks =
    orientation === "white" ? RANKS : [...RANKS].reverse();

  return (
    <main className="app">
      <header className="app__header">
        <div>
          <h1>Chess MCP</h1>
          <p className="app__subtitle">
            Type your move in chat. The board updates only from verified tool
            results.
          </p>
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

      <section className="board-wrapper">
        {isWaitingForTool ? (
          <div className="board board--waiting" role="status">
            <p>Waiting for the next tool update...</p>
          </div>
        ) : (
          <div className="board" role="grid" aria-label="Chess board">
            {displayRanks.map((rank, rankIndex) =>
              displayFiles.map((file, fileIndex) => {
                const square = `${file}${rank}`;
                const piece = getPieceAtSquare(board, square);
                const isDark = (rankIndex + fileIndex) % 2 === 1;
                return (
                  <div
                    key={square}
                    className={`square ${
                      isDark ? "square--dark" : "square--light"
                    }`}
                    role="gridcell"
                    aria-label={`Square ${square}`}
                  >
                    <span className="piece">{piece ? PIECES[piece] : ""}</span>
                    <span className="coord">
                      {fileIndex === 0 ? rank : ""}
                      {rankIndex === 7 ? file : ""}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        )}
        <div className="board-meta">
          <span>Type your move in chat (UCI like e2e4 or SAN like Nf3).</span>
          <p className="board-note">
            For promotions, include the piece letter (e.g., e7e8q).
          </p>
          <p className="board-note">
            Need the opponent to retry? Ask in chat and the model will rerun the
            opponent turn loop.
          </p>
        </div>
      </section>
    </main>
  );
}
