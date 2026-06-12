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

## Dependency setup

This repository has frontend dependencies declared in `package.json` and pinned
in `package-lock.json`. Install them before running website commands:

```bash
npm ci
```

## Website development

```bash
npm run dev
```

## Checks

```bash
npm test
npm run build
python3 -m unittest discover -s tests
```

## Python package setup

Install the package metadata and declared dependencies with:

```bash
python3 -m pip install -e .
```

## Event results source priority

The initial source registry lives in `data/event_sources.json` and is loaded with
`equibets.sources`. Country and level coverage groups live in
`data/source_coverage.json`, which records FEI Database country/NOC codes and
the national-event level scopes used by the registry.

1. `data_fei` (`https://data.fei.org/`) is the primary source for eventing
   results across all FEI member nations.
2. National-event sources fill gaps after FEI data, with priority coverage for
   Europe, the UK, Australia, New Zealand, and the USA.
3. `global_national_federations` is the backfill path for national events from
   every FEI member nation after the priority regions are covered.

Use the source helpers to resolve planned coverage by region, country, or
source-level tag:

```python
from equibets.sources import sources_for_country_and_event_level

sources_for_country_and_event_level("GBR", "national")
```

National-event crawlers are still marked `planned`; these helpers describe
coverage intent and priority order without treating unimplemented crawlers as
active ingestion.

Run the source registry checks with:

```bash
python3 -m unittest discover -s tests
```

## FEI Data bot

The FEI crawler lives in `equibets.fei_bot` and stores normalized eventing
results in the same shape used by the results calculator.

Example:

```bash
python3 -m pip install -r requirements.txt
FEI_COOKIE="your-data-fei-session-cookie" \
python3 -m equibets.fei_bot \
  --start-date 2026-05-01 \
  --end-date 2026-05-31 \
  --output data/fei_results.json \
  --raw-dir data/raw/fei \
  --verify warn
```

The bot defaults to a Playwright browser driver so FEI's JavaScript challenge
can run before search pages are submitted. It opens
`https://data.fei.org/Calendar/Search.aspx`, fills FEI dates as `dd/MM/yyyy`,
keeps ASP.NET hidden form fields such as `__VIEWSTATE`, opens each discovered
event, follows its result links, and writes deduplicated `data_fei` records.
Use `--storage-state data/fei_state.json` to reuse browser cookies,
`--form-field name=value` for FEI form controls that need explicit values in a
particular session, `--event-url` to crawl a known event page directly, and
`FEI_COOKIE` or `--cookie` when the FEI Data session requires login.
