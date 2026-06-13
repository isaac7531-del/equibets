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
`equibets.sources`. The registry declares the target country, region, and event
level coverage in addition to the ordered source list.

1. `data_fei` (`https://data.fei.org/`) is the primary source for FEI
   international eventing results across all FEI member nations.
2. Regional national-federation registries cover Africa, Asia, Central
   America/Caribbean, Europe, the Middle East, North America, Oceania, and South
   America across starter through national five-star levels.
3. Country-priority sources fill richer national-event gaps for the UK,
   Australia, New Zealand, and the USA.
4. `global_national_federations` is the backfill path for every FEI member
   nation and every national eventing level after higher-priority sources are
   covered.

Useful helpers:

- `load_event_source_registry()` loads sources plus coverage targets.
- `sources_for_region(region, level=...)` selects global and regional sources.
- `sources_for_country(country, level=...)` selects exact-country and global
  all-country sources.
- `sources_for_event_level(level)` selects sources that cover a national or FEI
  international level.

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
