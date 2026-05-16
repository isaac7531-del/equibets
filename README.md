# Equibets

Personal eventing results calculator, browser-based results tracker, and data source registry.

## What it does

- Calculates dressage, show jumping, cross-country jumping, and cross-country time penalties.
- Saves horse-and-rider results to local browser storage.
- Ranks saved results from lowest total penalties to highest.
- Builds source-prioritized current-event result searches and imports public JSON result feeds for live scoring.
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

## Current-event live scoring

The website includes a current-event panel that:

1. Builds search links against the FEI database first, then regional/national sources.
2. Pulls a JSON feed containing normalized `EventingResult` records.
3. Calculates live standings from the pulled dressage, jumping, and cross-country penalties.
4. Lets a pulled live score be saved into local results history.

Automation jobs can use `equibets.current_events.build_current_event_searches`
to discover source-specific searches, then normalize pulled result feeds with
`equibets.current_events.results_from_payload`.
