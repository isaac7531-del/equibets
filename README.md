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

1. `data_fei` (`https://data.fei.org/`) is the primary source for FEI eventing
   results across FEI member nations.
2. National-event sources fill gaps after FEI data and are marked with
   `all_eventing_levels` when they cover every local, regional, national, and
   international eventing level available from that source.
3. `global_national_federations` is the `all_countries` backfill path for
   national events from every country after higher-priority country or regional
   sources are covered.

Use `sources_for_country(country, level=...)` or
`sources_for_region(region, level=...)` to select sources for a specific data
refresh scope.

Run the source registry checks with:

```bash
python3 -m unittest discover -s tests
```
