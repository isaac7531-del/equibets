# eventiq

Personal eventing results calculator and data storage.

## Quick start

```bash
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

## Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start server + client in dev mode |
| `npm run dev:server` | Start Express API (port 3001) |
| `npm run dev:client` | Start Vite dev server (port 5173) |
| `npm run build` | Build client + server |
| `npm test` | Run all tests |
| `npm run lint` | Lint with ESLint |

## Tech stack

- **Frontend**: React 18 + Vite + TypeScript
- **Backend**: Express + TypeScript
- **Database**: SQLite (via better-sqlite3)
- **Testing**: Vitest + Testing Library
- **Linting**: ESLint + typescript-eslint
