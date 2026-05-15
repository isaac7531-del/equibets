# Equibets

Personal eventing results calculator, browser-based results tracker, and data source registry.

## What it does

- Calculates dressage, show jumping, cross-country jumping, and cross-country time penalties.
- Saves horse-and-rider results to local browser storage.
- Ranks saved results from lowest total penalties to highest.
- Tracks public event-results sources for FEI and national-event coverage.
- Searches pulled current-event records and ranks live scoring leaderboards.

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

## Current-event live scoring

Hourly or weekly refresh jobs can write normalized current-event records to
`data/current_event_results.json`. The browser app reads that feed at build time,
and `equibets.live_scoring` can load, search, deduplicate, and rank the same
records for automation workflows.

Each record uses the common result shape from `EventingResult`, plus:

- `status`: one of `not_started`, `dressage`, `show_jumping`,
  `cross_country`, or `final`
- `division`: optional display division, defaulting to `level`
- `source_url`: optional URL back to the official or public live result

Use `pull_live_scoring_snapshot()` to get a searched and ranked leaderboard:

```python
from equibets.live_scoring import pull_live_scoring_snapshot

snapshot = pull_live_scoring_snapshot(search_text="CCI3")
for entry in snapshot.entries:
    print(entry.rank, entry.live_result.result.horse_name, entry.live_result.finishing_score)
```
