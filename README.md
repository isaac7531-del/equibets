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

1. `data_fei` (`https://data.fei.org/`) is the primary source for FEI
   international eventing results across all countries.
2. National-event sources fill gaps after FEI data, with priority coverage for
   Europe, the UK, Australia, New Zealand, and the USA across all eventing
   levels.
3. `global_national_federations` is the backfill path for national events from
   every country and every eventing level after the priority regions are
   covered.

The registry uses the `all_countries` and `all_eventing_levels` coverage
wildcards. Use `sources_for_country(country, level=...)` for country-level
refreshes and `sources_for_region(region, level=...)` for regional refreshes.

Run the source registry checks with:

```bash
python3 -m unittest discover -s tests
```
