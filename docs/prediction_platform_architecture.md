# Eventing prediction platform architecture

This document defines the target MVP architecture for an FEI/eventing prediction
platform. The platform is an analytics and free-play prediction product, not a
real-money betting system.

## Compliance-first data policy

Before ingesting any source, create a `data_sources` record and complete the
source compliance review:

- confirm terms of service permit the planned use;
- check robots.txt and crawl-delay expectations;
- identify whether pages are copyright-protected beyond factual data;
- prefer official APIs, licensed feeds, manual uploads, CSV exports, or written
  permission when scraping is not allowed;
- store raw source snapshots only when permitted;
- rate-limit and identify the importer;
- keep source URLs and import job logs for audit.

If FEI/Data FEI or a national federation disallows automated scraping for a
specific page type, use one of these alternatives:

1. official API or licensed data feed;
2. manually uploaded start lists/results from permitted exports;
3. admin-entered corrections with source attribution;
4. exclude that page type until access is approved.

## System components

| Component | Responsibility |
| --- | --- |
| Next.js web app | Home, event, horse, rider, admin/data pages; deploys on Vercel. |
| FastAPI backend | Public read APIs, admin import endpoints, prediction run endpoints. |
| PostgreSQL/Supabase | Canonical horses, riders, events, entries, results, rollups, predictions, jobs. |
| Python importers | FEI and permitted national-source ingestion, raw snapshots, normalization. |
| Python prediction engine | Phase averages, level/event adjustments, confidence, predicted rankings. |
| Background jobs | Scheduled upcoming-event, result, entry-list, rollup, and prediction refreshes. |
| Admin tools | Source health, failed imports, manual ID matching, corrections, reruns. |

## Data flow

1. **Source review**
   - Admin creates/updates `data_sources`.
   - Source is marked `approved_for_ingest` only after terms/robots/licence
     review passes.
   - Import CLIs call the source-compliance gate before making network requests.
     The default FEI policy is blocked until a reviewed policy explicitly allows
     `calendar`, `entries`, or `results` jobs.

2. **Upcoming events import**
   - Importer collects permitted FEI/global calendar rows.
   - Normalize to `events` and `competitions`.
   - Record `scrape_jobs`, `scrape_job_events`, and optional raw snapshots.

3. **Entries/start lists import**
   - Import permitted start lists or manual uploads.
   - Normalize riders/horses with FEI IDs where available.
   - Create `entries` with horse/rider/nation/start order.

4. **Historical results import**
   - Import permitted result rows.
   - Normalize `results` and phase rows in `phase_scores`.
   - Preserve completion status: completed, eliminated, retired, withdrawn,
     MER-only, DNS, DQ when available.

5. **Identity matching**
   - Use FEI horse/rider IDs first.
   - Fall back to normalized name + nation + source hints.
   - Queue ambiguous matches in `identity_match_reviews`.

6. **Analytics rollups**
   - Build horse/rider/combination averages by normalized level group.
   - Compute last 3, last 5, 12-month, career-at-level, clear rates,
     completion rates, top-10 rates, and phase averages.

7. **Event difficulty**
   - Calculate historical event/class scoring difficulty when enough past rows
     exist.
   - Store adjustments in `event_difficulty_scores`.

8. **Predictions**
   - For every upcoming competition entry, combine horse, rider, combination,
     recent form, level, format, and event difficulty features.
   - Write one `prediction_runs` row and one `predictions` row per entry.
   - Rank entries by predicted final score, lower is better.

9. **Frontend/API**
   - Home page reads upcoming events and featured predictions.
   - Event pages read entries, predicted rankings, phase breakdowns, confidence,
     and recent form.
   - Horse/rider pages read results, rollups, and next-run predictions.
   - Admin page starts imports, reviews failures, resolves identity matches, and
     reruns predictions.

## MVP pages

### Home

- Upcoming events
- Featured predictions
- Search by horse, rider, event
- Data freshness/source status

### Event page

- Event details, location, country, dates
- Competition/class sections
- Entry list/start order
- Predicted ranking
- Predicted final score and phase breakdown
- Confidence score
- Recent form per horse/rider

### Horse page

- Horse profile and FEI ID
- Level history
- Results table
- Average scores by level
- Last 3/5/12-month form
- Best level and next-run prediction

### Rider page

- Rider profile and FEI ID
- Results and horses ridden
- Average performance by level
- Completion, clear, top-10, and phase rates

### Admin/data page

- Run importer
- View last scrape/import status
- Check failed imports
- Review source compliance
- Manually correct horse/rider matches
- Trigger rollups and prediction generation

## Prediction feature set

For every entry, generate:

- predicted dressage score;
- predicted show jumping penalties;
- predicted cross-country jump penalties;
- predicted cross-country time penalties;
- predicted final score;
- predicted ranking;
- confidence rating;
- feature contribution metadata.

## Starting formulas

Normalize event levels into groups such as `2*`, `3*`, `4*`, `5*` while
preserving short/long format as `S` or `L`.

### Phase prediction

For each phase, use weighted averages:

```text
phase_prediction =
  0.35 * combination_average_at_level
+ 0.25 * horse_average_at_level
+ 0.20 * rider_average_at_level
+ 0.15 * recent_form_average
+ 0.05 * event_difficulty_adjustment
```

If a feature is missing, redistribute its weight across available features and
lower confidence.

### Final score

```text
predicted_final_score =
  predicted_dressage
+ predicted_show_jumping_penalties
+ predicted_xc_jump_penalties
+ predicted_xc_time_penalties
```

### Confidence

Start with a 0-100 score:

- +25 if combination has at least 5 same-level starts;
- +20 if horse has at least 8 same-level starts;
- +15 if rider has at least 12 same-level starts;
- +15 if at least 3 starts in last 12 months;
- +10 if event difficulty has enough historical rows;
- +10 if FEI IDs are matched for horse and rider;
- +5 if source rows were imported from approved official/licensed sources.

Map confidence:

- `high`: 75-100
- `medium`: 45-74
- `low`: below 45

## Backend API endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /events/upcoming` | Upcoming events with competition counts and freshness. |
| `GET /events/{event_id}` | Event details, competitions, source metadata. |
| `GET /competitions/{competition_id}/entries` | Entries/start list. |
| `GET /competitions/{competition_id}/predictions` | Predicted ranking and phase breakdowns. |
| `GET /horses/{horse_id}` | Horse profile, IDs, results, rollups, next prediction. |
| `GET /riders/{rider_id}` | Rider profile, results, rollups, horses. |
| `GET /search?q=` | Horse/rider/event search. |
| `POST /admin/scrape-jobs` | Start permitted importer job. |
| `GET /admin/scrape-jobs/{job_id}` | Job status and failures. |
| `POST /admin/manual-uploads` | Upload permitted CSV/source export. |
| `GET /admin/identity-match-reviews` | Pending match review queue. |
| `POST /admin/identity-match-reviews/{id}/resolve` | Resolve horse/rider match. |
| `POST /admin/prediction-runs` | Trigger prediction generation. |

## Build order

1. Implement PostgreSQL schema and migrations.
2. Add data-source compliance/admin records.
3. Build FEI calendar importer for permitted upcoming events.
4. Build manual CSV upload path for entries/results.
5. Build FEI/national result importers only for approved sources.
6. Implement horse/rider ID matching and review queue.
7. Generate rollups: horse, rider, combination, recent form, event difficulty.
8. Implement deterministic baseline prediction engine.
9. Add event page prediction table.
10. Add horse and rider pages.
11. Add admin source/job/match review pages.
12. Add scheduled imports and prediction reruns.
13. Add monitoring, source quality dashboards, and launch data QA.

## Non-goals for MVP

- No real-money betting.
- No deposits or withdrawals.
- No odds, margins, or stake settlement.
- No scraping where the source terms/robots prohibit it.
