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

## Live current-event scoring feed

Hourly or event-day jobs can now publish a normalized current-event JSON feed
for the website to read from `/current-events.json` or from
`VITE_LIVE_RESULTS_URL`.

The feed supports either a flat `results` list or an `events` list with
event-level defaults:

```json
{
  "generated_at": "2026-05-16T19:00:00+00:00",
  "source_ids": ["data_fei"],
  "results": [
    {
      "source_id": "data_fei",
      "source_record_id": "fei-live-1",
      "source_priority": 0,
      "rider_name": "Avery Stone",
      "horse_name": "Juniper",
      "event_name": "Current Spring International",
      "event_date": "2026-05-16",
      "level": "CCI3",
      "country": "GBR",
      "status": "live",
      "dressage_score": 29.4,
      "show_jumping_penalties": 4,
      "cross_country_jump_penalties": null,
      "cross_country_time_penalties": null,
      "phase_statuses": {
        "dressage": "complete",
        "show_jumping": "complete",
        "cross_country": "not_started"
      },
      "collected_at": "2026-05-16T19:00:00+00:00",
      "source_url": "https://data.fei.org/"
    }
  ]
}
```

Use `python3 -m equibets.live_scoring --feed-url <url> --output
public/current-events.json --pretty` to pull configured JSON feeds, dedupe
duplicate starts by source priority, and emit the frontend feed. Add `--query`
to search a horse, rider, event, level, country, or source before writing the
payload.

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
