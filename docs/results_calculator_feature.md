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

1. Refresh public data weekly from `data/event_sources.json`.
2. Normalize each result into `EventingResult`.
3. Deduplicate by combination, event, date, and level.
4. Keep the lowest `source_priority` when duplicates exist, so `data_fei`
   replaces national or user-entered duplicates.
5. Keep user-entered scores when no official/public result exists for the same
   start.

This gives users a complete working view without letting unverified manual data
override official results.

## Weekly update flow

1. Pull new FEI results from `data.fei.org`.
2. Pull national-event updates from the priority regions.
3. Pull global national-federation results as a backfill.
4. Store raw source payloads for auditability.
5. Normalize records into the common result table.
6. Re-run consolidation and prediction calculations.
7. Show the latest `collected_at` timestamp in the website UI.

## Current-event live scoring flow

The live scoring feature consumes `data/current_event_results.json`, which is a
normalized snapshot produced by the refresh job after it searches official and
public current-event feeds. Automation should:

1. Track the last successful `collected_at` timestamp.
2. Search active and planned sources for new current-event result records.
3. Normalize every found start into the `EventingResult` fields.
4. Add the live-only fields: `status`, optional `division`, and optional
   `source_url`.
5. Write the new snapshot to `data/current_event_results.json`.
6. Use `new_results_since` when only fresh records should be scored.
7. Use `pull_live_scoring_snapshot` to return the searched, deduplicated, ranked
   leaderboard shown by the app.

The app ranks current-event starts by lowest known penalties and uses phase
status as a tiebreaker so more complete results appear ahead of earlier-phase
scores with the same total.

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
