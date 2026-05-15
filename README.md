# Equibets

Personal eventing results calculator, browser-based results tracker, and data source registry.

## What it does

- Calculates dressage, show jumping, cross-country jumping, and cross-country time penalties.
- Saves horse-and-rider results to local browser storage.
- Ranks saved results from lowest total penalties to highest.
- Tracks public event-results sources for FEI and national-event coverage.

## Results calculator feature

The calculator is designed as a website/application feature where users can add
their own scores, view consolidated public results, and estimate a combination's
likely finishing score at upcoming events.

See `docs/results_calculator_feature.md` for the public-data update flow,
user-score handling, and prediction surface.

## Website development

```bash
npm install
npm run dev
```

## Checks

```bash
npm test
npm run build
```

## Python package setup

Install the package metadata and declared dependencies with:

```bash
python3 -m pip install -e .
```

The FEI browser collector can use Playwright when `data.fei.org` requires its
JavaScript challenge:

```bash
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
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

## Live public scoring update

Use the FEI collector to search current FEI eventing calendar results, pull
result pages, and merge normalized scores into `data/fei_results.json`:

```bash
python3 -m equibets.fei_bot \
  --start-date 2026-05-08 \
  --end-date 2026-05-17 \
  --output data/fei_results.json \
  --raw-dir data/raw/fei \
  --storage-state data/fei_state.json
```

Then generate the live scoring feed that ranks each current event by lowest
penalty score:

```bash
python3 -m equibets.live_scoring \
  --results data/fei_results.json \
  --output data/live_scoring.json \
  --lookback-days 7 \
  --lookahead-days 2
```

The hourly automation can run both commands with a rolling date window. The
collector stores raw FEI HTML for auditability and keeps official `data_fei`
results ahead of duplicate user-entered scores during consolidation.
