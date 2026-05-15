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

The implemented refresh path is `python3 -m equibets.live_scoring`. It accepts a
search manifest, result JSON files, directories, or URLs; follows discovered
`result_urls`/`search_results`; normalizes results into `EventingResult`; and
writes a live-scoring snapshot with consolidated results and predictions. A
search manifest can be as small as:

```json
{
  "search_results": [
    { "url": "fei-results-2026-05-15.json" },
    { "url": "national-results-2026-05-15.json" }
  ]
}
```

Result payloads can use either a flat `results` list or an event-grouped
`events` list. Event-grouped payloads inherit event metadata:

```json
{
  "source_id": "data_fei",
  "events": [
    {
      "event_name": "Kentucky Spring Horse Trials",
      "event_date": "2026-05-14",
      "level": "CCI3-S",
      "country": "USA",
      "results": [
        {
          "source_record_id": "fei-100",
          "rider_name": "Alex Rider",
          "horse_name": "Pocket Rocket",
          "dressage_score": 29.8,
          "show_jumping_penalties": 0,
          "cross_country_jump_penalties": 0,
          "cross_country_time_penalties": 2.4
        }
      ]
    }
  ]
}
```

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
