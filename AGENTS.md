# Repository instructions

## Cursor Cloud specific instructions

**EventIQ** is a full-stack TypeScript app for tracking event bets and results,
with a Python package for FEI data collection and event source management.

### Architecture

- **`server/`** — Express API + SQLite (better-sqlite3). Runs on port 3001.
- **`client/`** — React + Vite SPA. Runs on port 5173, proxies `/api` to the server.
- **Root** — npm workspaces monorepo. ESLint configured at root level.
- **`equibets/`** — Python package (FEI bot, results, sources).

### Common commands

| Task | Command |
|---|---|
| Install JS deps | `npm install` (from root) |
| Install Python deps | `python3 -m pip install -e .` |
| Dev (both) | `npm run dev` |
| Dev server only | `npm run dev:server` |
| Dev client only | `npm run dev:client` |
| Lint | `npm run lint` |
| Test JS | `npm test` |
| Test Python | `python3 -m unittest discover -s tests` |
| Build | `npm run build` |

### Non-obvious notes

- The SQLite database file (`eventiq.db`) is created automatically in `server/` on first run; it is git-ignored.
- Start the server **before** the client when running them separately — Vite proxies `/api` requests to `localhost:3001`.
- Server tests use in-memory SQLite (`:memory:`) and ephemeral ports, so they are fully isolated.
- Client tests use jsdom + `@testing-library/react` with a mocked `fetch`.
- The Python package currently uses only the standard library at runtime. Use
  `python3 -m pip install -e .` when editable package metadata is needed.

## Checks

- Run frontend tests with `npm test`.
- Run the production frontend build with `npm run build`.
- Run Python tests with `python3 -m unittest discover -s tests`.
