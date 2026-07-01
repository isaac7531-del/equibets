# Equibets

FEI Eventing results mirror, horse-performance database, prediction app, and
private score calculator.

## What it does

- Calculates dressage, show jumping, cross-country jumping, and cross-country
  time penalties.
- Saves private calculator results to local browser storage with level and
  country metadata.
- Scrapes FEI Calendar Search for Eventing competitions with results and copies
  FEI event, class, result, rider, horse, and combination history into
  PostgreSQL.
- Keeps the public results database FEI-only; national federation results are
  intentionally out of scope.
- Estimates a likely finishing score range from FEI horse/rider history and
  transparent evidence metrics.

## Website application

The website can run as a static preview with curated FEI-only examples. Private
calculator scores stay in local browser storage and do not enter the FEI
database, form guide, or prediction evidence.

See `docs/results_calculator_feature.md` for the legacy calculator notes. The
current collection target is FEI-only.

## Dependency setup

This repository has frontend dependencies declared in `package.json` and pinned
in `package-lock.json`. Install them before running website commands:

```bash
npm ci
```

## Website development

```bash
npm run dev
```

## Checks

```bash
npm test
npm run build
python3 -m unittest discover -s tests
```

## Python package setup

Install the package metadata and declared dependencies with:

```bash
python3 -m pip install -e .
```

## FEI-only results source

The initial source registry lives in `data/event_sources.json` and is loaded with
`equibets.sources`.

`data_fei` (`https://data.fei.org/`) is the only configured results source.
Daily jobs copy FEI Eventing rows into our PostgreSQL database so Equibets can
act as a one-stop shop for FEI results and horse-performance history.

Run the source registry checks with:

```bash
python3 -m unittest discover -s tests
```

## FEI Data bot

The FEI crawler lives in `equibets.fei_bot` and stores normalized FEI Eventing
results in the same shape copied into PostgreSQL by the pipeline.

Example:

```bash
python3 -m pip install -r requirements.txt
FEI_COOKIE="your-data-fei-session-cookie" \
python3 -m equibets.fei_bot \
  --start-date 2026-05-01 \
  --end-date 2026-05-31 \
  --output data/fei_results.json \
  --raw-dir data/raw/fei \
  --verify warn
```

The bot defaults to a Playwright browser driver so FEI's JavaScript challenge
can run before search pages are submitted. It opens
`https://data.fei.org/Calendar/Search.aspx`, fills FEI dates as `dd/MM/yyyy`,
keeps ASP.NET hidden form fields such as `__VIEWSTATE`, opens each discovered
event, follows its result links, and writes deduplicated `data_fei` records.
Use `--storage-state data/fei_state.json` to reuse browser cookies,
`--form-field name=value` for FEI form controls that need explicit values in a
particular session, `--event-url` to crawl a known event page directly, and
`FEI_COOKIE` or `--cookie` when the FEI Data session requires login.

## FEI Eventing PostgreSQL pipeline and API

The production collection path writes the rolling 12-month FEI Eventing dataset
to PostgreSQL, enriches every discovered horse with FEI horse-history results,
and stores transparent prediction evidence. The database schema rejects
non-`data_fei` result rows:

```bash
python3 -m pip install -e .
DATABASE_URL="postgresql://user:password@localhost:5432/equibets" \
python3 -m equibets.pipeline \
  --driver browser \
  --storage-state data/fei_state.json \
  --raw-dir data/raw/fei
```

The pipeline creates and upserts the required tables: `events`, `classes`,
`result_rows`, `horses`, `riders`, `combinations`, `horse_result_history`,
`predictions`, and `scrape_logs`. By default it searches
`https://data.fei.org/Calendar/Search.aspx` for Eventing competitions with
results from the previous 365 days. Use `--event-url` to rerun one FEI event.

Run the API with:

```bash
DATABASE_URL="postgresql://user:password@localhost:5432/equibets" \
uvicorn api.main:app --reload
```

Suggested daily schedule:

```cron
15 3 * * * cd /path/to/equibets && DATABASE_URL="postgresql://..." python3 -m equibets.pipeline --driver browser --storage-state data/fei_state.json >> data/fei_pipeline.log 2>&1
```
