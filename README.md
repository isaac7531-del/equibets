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

The source registry lives in `data/event_sources.json` and is loaded with
`equibets.sources`. The registry declares versioned coverage targets for all FEI
member nations, eventing as the discipline, every domestic national/regional
level, and FEI international levels from CCI Intro through CCI5*-L and
championships.

1. `data_fei` (`https://data.fei.org/`) is the primary source for eventing
   results across all FEI member nations and FEI eventing levels.
2. Regional national-federation registries fill domestic-level gaps for Africa,
   Asia, Europe, the Middle East, North America, Central America/Caribbean,
   South America, and Oceania.
3. Country-priority national sources cover Great Britain, Australia, New
   Zealand, and the USA across all configured domestic eventing levels.
4. `global_national_federations` is the final backfill path for national events
   from every FEI member nation and every configured domestic level.

Source helpers can load the complete registry or return sources by country,
region, or event level:

```python
from equibets.sources import (
    load_event_source_registry,
    sources_for_country,
    sources_for_event_level,
    sources_for_region,
)

registry = load_event_source_registry()
usa_sources = sources_for_country("USA")
cci5_sources = sources_for_event_level("CCI5*-L")
oceania_sources = sources_for_region("oceania")
```

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
