# AGENTS.md

## Cursor Cloud specific instructions

**Equibets** is a full-stack TypeScript app for tracking event bets and results.

### Architecture

- **`server/`** — Express API + SQLite (better-sqlite3). Runs on port 3001.
- **`client/`** — React + Vite SPA. Runs on port 5173, proxies `/api` to the server.
- **Root** — npm workspaces monorepo. ESLint configured at root level.

### Common commands

| Task | Command |
|---|---|
| Install deps | `npm install` (from root) |
| Dev (both) | `npm run dev` |
| Dev server only | `npm run dev:server` |
| Dev client only | `npm run dev:client` |
| Lint | `npm run lint` |
| Test all | `npm test` |
| Build | `npm run build` |

### Non-obvious notes

- The SQLite database file (`equibets.db`) is created automatically in `server/` on first run; it is git-ignored.
- Start the server **before** the client when running them separately — Vite proxies `/api` requests to `localhost:3001`.
- Server tests use in-memory SQLite (`:memory:`) and ephemeral ports, so they are fully isolated.
- Client tests use jsdom + `@testing-library/react` with a mocked `fetch`.
