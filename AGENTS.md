# Repository instructions

## Cursor Cloud specific instructions

- Install frontend dependencies with `npm ci` before running `npm test`,
  `npm run build`, or `npm run dev`.
- The Python package currently uses only the standard library at runtime. Use
  `python3 -m pip install -e .` when editable package metadata is needed.

## Checks

- Run frontend tests with `npm test`.
- Run the production frontend build with `npm run build`.
- Run Python tests with `python3 -m unittest discover -s tests`.
