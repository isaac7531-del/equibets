# Live results feed

The website can pull current-event scoring data from a JSON feed and rank each
combination by total eventing penalties. By default it requests:

```text
/live-results.json
```

Set `VITE_LIVE_RESULTS_URL` during the Vite build to point at another hosted
feed.

## Feed shape

```json
{
  "collectedAt": "2026-05-16T17:00:00Z",
  "source": {
    "id": "data_fei",
    "name": "FEI Database"
  },
  "results": [
    {
      "id": "fei-2026-05-16-1",
      "rider": "Avery Stone",
      "horse": "Juniper",
      "eventName": "Current Spring Horse Trials",
      "eventDate": "2026-05-16",
      "level": "CCI2*-S",
      "country": "USA",
      "dressagePenalties": 29.2,
      "showJumpingPenalties": 4,
      "crossCountryJumpPenalties": 0,
      "crossCountryTimePenalties": 0,
      "status": "provisional"
    }
  ]
}
```

Snake-case keys from the Python `EventingResult` model are also accepted, such
as `rider_name`, `horse_name`, `event_name`, `event_date`, `dressage_score`,
`show_jumping_penalties`, `cross_country_jump_penalties`, and
`cross_country_time_penalties`.

## Scoring behavior

Live feeds should provide dressage as penalties, not a percentage. The frontend
adds dressage penalties, show jumping penalties, cross-country jumping
penalties, and cross-country time penalties, rounds each phase to tenths, and
sorts the live leaderboard from lowest total penalties to highest.
