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

See `docs/results_calculator_feature.md` for the weekly update flow, user-score
handling, and prediction surface.

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

## FEI current-event results

The FEI crawler lives in `equibets.fei_bot` and normalizes `data.fei.org`
eventing result tables into the common `EventingResult` JSON shape.

Install the optional browser dependency before live FEI pulls:

```bash
python3 -m pip install -r requirements.txt
```

Example FEI pull:

```bash
FEI_COOKIE="your-data-fei-session-cookie" \
python3 -m equibets.fei_bot \
  --start-date 2026-05-12 \
  --end-date 2026-05-16 \
  --output data/fei_results.json \
  --raw-dir data/raw/fei \
  --storage-state data/fei_state.json
```

The bot uses a Playwright browser driver by default so FEI's JavaScript
challenge can run before search pages are submitted. Use `--driver http` only
for saved/simple FEI pages that do not require the browser challenge path.

## Live scoring refresh

`equibets.live_scoring` is the cron-friendly entry point for current-event
scoreboards. It can search FEI for new eventing results, merge them into
`data/fei_results.json`, and write ranked live scores to
`public/live_scores.json` for the website to display.

```bash
python3 -m equibets.live_scoring \
  --refresh-fei \
  --on-date 2026-05-15 \
  --lookback-days 3 \
  --lookahead-days 1 \
  --storage-state data/fei_state.json \
  --raw-dir data/raw/fei \
  --output public/live_scores.json
```

The output report includes the refresh window, latest source `collected_at`
timestamp, event/class groups, and ranked rows with phase penalties and total
penalties for live display.
