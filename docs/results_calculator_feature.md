# Results calculator feature

The results calculator should be a feature inside the website/application, not a
separate product. It stores eventing results, accepts user-entered scores, and
shows how horse/rider combinations are performing before upcoming events.

## User goals

- Search a horse/rider combination and see recent finishing scores.
- Compare official/public results with scores the user has added manually.
- See a likely finishing score for upcoming events.
- Track all nations over time, while prioritizing richer national-event data
  from Europe, the UK, Australia, New Zealand, and the USA.

## Data consolidation

1. Refresh public data from `data/event_sources.json`; current-event scoring can
   run hourly while slower national backfills can remain weekly.
2. Normalize each result into `EventingResult`.
3. Deduplicate by combination, event, date, and level.
4. Keep the lowest `source_priority` when duplicates exist, so `data_fei`
   replaces national or user-entered duplicates.
5. Keep user-entered scores when no official/public result exists for the same
   start.

This gives users a complete working view without letting unverified manual data
override official results.

## Public update flow

1. Search FEI's eventing calendar on `data.fei.org` for a rolling current-event
   window.
2. Pull result pages for discovered events and normalize live phase scores into
   `EventingResult`.
3. Pull national-event updates from the priority regions when FEI data does not
   cover the start.
4. Pull global national-federation results as a backfill.
5. Store raw source payloads for auditability.
6. Merge records into the common result table and re-run consolidation.
7. Generate `data/live_scoring.json` from current events, ranked by lowest
   penalty score.
8. Re-run prediction calculations and show the latest `collected_at` timestamp
   in the website UI.

## Prediction logic

`predict_finishing_score` uses the most recent consolidated starts for a
combination. Recent starts carry more weight than older starts, because they
usually reflect current fitness, level, and form more accurately.

The first prediction output includes:

- likely finishing score
- recent result count
- best and worst recent scores
- contributing source IDs
- confidence level based on result count

## Website feature outline

- Combination profile page: recent starts, phase penalties, and likely score.
- Upcoming event page: predicted finishing scores for entered combinations.
- Add my score form: rider, horse, event, date, level, country, phase scores.
- Data freshness badge: last weekly public-data refresh and source coverage.
- Source badges: FEI, national federation, global backfill, or user-entered.
