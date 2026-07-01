# Results calculator feature

The results calculator is a feature inside the website/application, not a
separate product. It stores eventing results, accepts user-entered scores, and
shows how horse/rider combinations are performing before upcoming events.

## User goals

- Search a horse/rider combination and see recent finishing scores.
- Compare FEI result history with private scores the user has added manually.
- See a likely finishing score for upcoming events.
- Track FEI Eventing results across nations from the FEI Database.

## Data consolidation

The current static website ships with curated FEI-only sample results in
`src/publicResults.ts`. Local browser scores stay private and are not copied into
the FEI database. Future FEI refreshes should follow the same rules:

1. Refresh FEI data daily from `https://data.fei.org/Calendar/Search.aspx`.
2. Normalize each FEI result into the shared event-result shape.
3. Deduplicate by combination, event, date, and level.
4. Copy only `data_fei` result rows into PostgreSQL.
5. Preserve the FEI source URL and raw crawl logs for auditability.

This gives users a one-stop FEI results and horse-performance view without
mixing in unverified manual or national-federation data.

## Daily update flow

1. Pull new FEI results from `data.fei.org`.
2. Store raw source payloads for auditability.
3. Normalize records into the PostgreSQL result tables.
4. Enrich each horse with FEI horse-history results.
5. Re-run prediction calculations.
6. Show the latest `collected_at` timestamp in the website UI.

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

- Add my score form: rider, horse, event, date, level, country, phase scores.
- Saved local results table ranked from lowest total penalties to highest.
- FEI form guide: FEI result rows copied from the database.
- Combination prediction panel: likely score, confidence, source IDs, best and
  worst recent scores.
- Data freshness badge: latest FEI `collected_at` timestamp.
- Source badges: FEI only for public/database records.

Future pages can split this single-page application into dedicated combination
profiles and upcoming-event views after a backend or static refresh pipeline is
available.
