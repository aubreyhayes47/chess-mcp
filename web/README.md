# chess-mcp widget (scaffold)

This directory contains the React + Vite widget for the chess MCP app. The
widget renders the board from `window.openai.toolOutput` (provided by
`render_game`) and displays instructions for chat-driven moves.

## Local development

```bash
cd web
npm install
npm run dev
```

## Build

```bash
npm run build
```

## Notes

- The widget reads from `window.openai.toolOutput`.
- The build output is embedded into the server template.
