# Equibets

Personal equestrian eventing results calculator, browser-based results tracker, and data source registry.

## Cursor Cloud specific instructions

### Project structure

- **Frontend (React + TypeScript + Vite):** Main web application in `src/`. Uses npm as package manager.
- **Python package (`equibets/`):** Utility library for source registry and result consolidation logic. No external Python dependencies.

### Running the application

- `npm run dev` — starts Vite dev server on `0.0.0.0:5173` with HMR.
- No backend services, databases, or Docker containers are required. The app is purely client-side using localStorage.

### Testing

- **JS tests:** `npm test` (runs Vitest with jsdom environment)
- **Python tests:** `python3 -m unittest discover -s tests`
- **Build check:** `npm run build` (runs `tsc -b` then `vite build`)

### Notes

- There is no linter configured (no ESLint or Prettier in devDependencies). TypeScript strict type-checking via `tsc -b` serves as the primary code-quality gate.
- The Python package has zero external dependencies; `pip install -e .` is sufficient.
- The dev server binds to `0.0.0.0` so it's accessible from outside the container.
