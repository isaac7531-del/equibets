# Equibets

Personal eventing results calculator, browser-based results tracker, and data source registry.

## What it does

- Calculates dressage, show jumping, cross-country jumping, and cross-country time penalties.
- Searches the current-event feed and pulls live public scores into the calculator.
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

## Current-event live scoring feed

The app reads `data/current_events.json` as the current-event feed snapshot. An
hourly pull job can replace this file with fresh FEI or national-source rows in
the same shape, then the website will expose search, live totals, and a "Pull
live score" action.

Python helpers in `equibets.current_events` can load a local JSON file or HTTPS
URL, search rows, rank the live leaderboard, and normalize rows into
`EventingResult` records:

```python
from equibets.current_events import load_current_event_results, search_current_event_results

results = load_current_event_results("data/current_events.json")
matches = search_current_event_results(results, "Copper Chance")
```
