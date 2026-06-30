# Equibets

Eventing form guide, results calculator, browser-based score tracker, and data
source registry.

Equibets is currently a non-gambling analytics and free prediction product. It
does not include real-money betting, deposits, withdrawals, paid odds, or
gambling settlement flows.

## What it does

- Calculates dressage, show jumping, cross-country jumping, and cross-country
  time penalties.
- Saves horse-and-rider results to local browser storage with level and country
  metadata.
- Saves richer local horse profile records, including FEI ID, registry name,
  country, owner, and notes.
- Combines saved user scores with public sample results into one consolidated
  form guide.
- Uses source priority to keep official/public results ahead of duplicate
  user-entered scores.
- Estimates a likely finishing score from the most recent consolidated starts.
- Tracks public event-results sources for FEI and national-event coverage.
- Builds `data/horse_index.json` from every collected result so the production
  corpus can cover all horses found in scraped FEI/national eventing data.

## Website application

The website is a finished static application: it works with no backend, ships
with curated public result examples while the full scrape pipeline is being
promoted, and folds any locally saved scores into the same consolidation and
prediction workflow.

The frontend now also ships as an installable app-style PWA. Browsers can use
`public/manifest.webmanifest`, `public/app-icon.svg`, and `public/sw.js` to show
standalone install prompts and cache the app shell for repeat visits.

Production domain setup for `equibets.app` is documented in
`docs/equibets_app_deployment.md`.

See `docs/results_calculator_feature.md` for the consolidation rules, prediction
logic, and future weekly public-data update flow.

See `docs/legal_eventing_mvp_plan.md` for the step-by-step MVP plan covering
rankings, free prediction markets, backend APIs, frontend pages, compliance
boundaries, and the recommended stack.

See `docs/platform_schema.sql` for the target PostgreSQL contract for riders,
horses, combinations, events, results, model runs, free prediction markets, user
predictions, and leaderboards.

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

## Event results source priority

The initial source registry lives in `data/event_sources.json` and is loaded with
`equibets.sources`.

1. `data_fei` (`https://data.fei.org/`) is the primary source for eventing
   results across all FEI member nations.
2. National-event sources fill gaps after FEI data, with priority coverage for
   Europe, the UK, Australia, New Zealand, and the USA.
3. `global_national_federations` is the backfill path for national events from
   every FEI member nation after the priority regions are covered.

Run the source registry checks with:

```bash
python3 -m unittest discover -s tests
```

## FEI Data bot

The FEI crawler lives in `equibets.fei_bot` and stores normalized eventing
results in the same shape used by the results calculator.

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

## Upcoming event refresh

Upcoming global eventing calendar rows are normalized by
`equibets.upcoming_events` and written to `data/upcoming_events.json`.

Example:

```bash
FEI_COOKIE="your-data-fei-session-cookie" \
python3 -m equibets.upcoming_events \
  --days-ahead 180 \
  --output data/upcoming_events.json \
  --storage-state data/fei_state.json
```

The scheduled GitHub Actions workflow at
`.github/workflows/event-data-refresh.yml` runs tests/builds daily, then refreshes
upcoming FEI events and recent FEI results when the `FEI_COOKIE` repository
secret is configured. It uploads the refreshed JSON files as workflow artifacts
for review before any production data publish step.

## Horse index

`equibets.horses` builds a horse index from every collected result. It is the
path to covering all currently active eventing horses as source coverage grows.

Example:

```bash
python3 -m equibets.horses \
  --results data/fei_results.json \
  --output data/horse_index.json \
  --active-window-days 730
```

The scheduled refresh workflow runs this after FEI result collection and uploads
`data/horse_index.json` alongside the raw refresh artifacts.

## Probability engine

The initial free-play probability model lives in `equibets.probability`. It
estimates phase expectations from recent consolidated results and runs a Monte
Carlo simulation for non-gambling market probabilities such as win, top 3, top
10, best dressage, clear show jumping, and clear cross-country.
