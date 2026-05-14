# EquiBets

EquiBets is a static web app for tracking international eventing combinations,
saving favourites, guessing team selections, and reviewing transparent predicted
scores for upcoming events. It also supports the results calculator and source
registry used to build a more complete eventing data store.

## Features

- Easy navigation across dashboard, rider combinations, event forecasts, team
  guesses, and model notes.
- Browser-local favourite rider and horse combinations.
- Team guess builder for international events including the World Equestrian
  Games and Olympics.
- 5-star and 4-star event calendar sections for major form checks.
- Previous result pages for rider and horse combinations.
- Predicted finishing scores with confidence, risk, range, and data-quality
  signals.

## Run locally

```bash
npm start
```

Open `http://localhost:4173`.

## Test

```bash
npm test
```

Run the source registry checks with:

```bash
python3 -m unittest discover -s tests
```

## Results calculator feature

The calculator is designed as a website/application feature where users can add
their own scores, view consolidated public results, and estimate a combination's
likely finishing score at upcoming events.

See `docs/results_calculator_feature.md` for the weekly update flow, user-score
handling, and prediction surface.

## Event results source priority

The initial source registry lives in `data/event_sources.json` and is loaded with
`equibets.sources`.

1. `data_fei` (`https://data.fei.org/`) is the primary source for eventing
   results across all FEI member nations.
2. National-event sources fill gaps after FEI data, with priority coverage for
   Europe, the UK, Australia, New Zealand, and the USA.
3. `global_national_federations` is the backfill path for national events from
   every FEI member nation after the priority regions are covered.

## Betting readiness

The current model is an explainable product foundation, not betting advice. A
betting product would need audited live data feeds, scratch/injury monitoring,
historical back-testing, compliance review, and continuous accuracy reporting.
