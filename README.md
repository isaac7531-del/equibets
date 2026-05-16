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
2. National-event sources fill gaps after FEI data for every FEI member nation
   and every national-to-local level bucket, including national championships,
   elite/advanced through introductory divisions, regional, local, club,
   grassroots, schooling, starter, and pony/youth events.
3. Priority connectors cover Europe, the UK, Australia, New Zealand, and the
   USA first, while `global_national_federations` remains the all-country,
   all-level backfill after higher-priority sources are covered.
4. Use `sources_for_region`, `sources_for_country`, and
   `sources_for_event_level` to choose the right source set for a refresh.

Run the source registry checks with:

```bash
python3 -m unittest discover -s tests
```
