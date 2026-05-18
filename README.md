# Equibets

Eventing form guide, results calculator, browser-based score tracker, and data
source registry.

## What it does

- Calculates dressage, show jumping, cross-country jumping, and cross-country
  time penalties.
- Saves horse-and-rider results to local browser storage with level and country
  metadata.
- Combines saved user scores with public sample results into one consolidated
  form guide.
- Uses source priority to keep official/public results ahead of duplicate
  user-entered scores.
- Estimates a likely finishing score from the most recent consolidated starts.
- Tracks public event-results sources for FEI and national-event coverage.

## Website application

The website is a finished static application: it works with no backend, ships
with curated public result examples, and folds any locally saved scores into the
same consolidation and prediction workflow.

See `docs/results_calculator_feature.md` for the consolidation rules, prediction
logic, and future weekly public-data update flow.

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
