# Legal eventing analytics and prediction MVP

Equibets should start as a legal analytics product and free prediction game for
horse eventing. It must not handle real money, deposits, withdrawals, paid odds,
or gambling flows until specialist legal advice and gambling licences are in
place for every operating jurisdiction.

## Product position

- **Now:** eventing form guide, rankings, phase analytics, and free-to-play
  predictions.
- **Next:** richer probability markets, user accounts, leaderboards, event
  import tooling, manual horse data management, and admin review queues.
- **Later:** licensed betting can be evaluated as a separate regulated product,
  not as a hidden extension of the analytics MVP.

## MVP stack

- **Frontend:** keep the current React/Vite app for the static MVP; move to
  Next.js when server-rendered profiles, authenticated dashboards, and SEO
  pages matter.
- **Backend:** Python FastAPI for ingestion, modelling, admin tools, and API
  routes; the current `equibets` package can become the shared domain layer.
- **Database:** PostgreSQL, hosted through Supabase for the first MVP if managed
  auth and row-level security are useful.
- **Auth:** Supabase Auth or Clerk for email/social login; no payment provider in
  the free-play phase.
- **Jobs:** scheduled GitHub Actions, Supabase cron, or a small worker for FEI
  and national source refreshes.
- **Hosting:** Vercel/Netlify for frontend, Render/Fly.io/Railway for FastAPI,
  Supabase for Postgres/Auth/Storage.

## Data model milestones

1. **Results foundation**
   - `riders`, `horses`, `horse_rider_combinations`
   - `events`, `event_divisions`, `event_entries`
   - `result_imports`, `event_results`, `result_phase_scores`
   - `upcoming_events` refresh output from global public calendars
2. **Analytics**
   - rider rankings
   - horse rankings
   - combination ratings
   - event difficulty ratings
   - form trends, phase averages, clear rates, time penalties, withdrawals, and
     eliminations
3. **Free prediction markets**
   - market templates for win, top 3, top 10, best dressage, clear show jumping,
     clear cross-country, head-to-head, and score over/under
   - market instances per division
   - user predictions with points, not money
   - leaderboard snapshots
4. **Admin and audit**
   - source registry
   - import runs
   - data-quality flags
   - manual correction workflow
   - horse-profile edit/review workflow
   - model run logs

## First backend API

| Route | Purpose |
| --- | --- |
| `GET /events` | upcoming and recent events |
| `GET /events/{event_id}/divisions` | classes/sections at an event |
| `GET /divisions/{division_id}/entries` | declared field |
| `GET /divisions/{division_id}/results` | official/public results |
| `GET /riders/{rider_id}` | rider profile, rankings, recent form |
| `GET /horses/{horse_id}` | horse profile and form |
| `GET /combinations/{combination_id}` | horse/rider combination rating |
| `GET /divisions/{division_id}/markets` | free-play prediction markets |
| `POST /predictions` | submit a free prediction |
| `GET /leaderboards` | free-play leaderboard |
| `POST /admin/import-runs` | start or register a data import |

## Data refresh path

- Use FEI Data as the first global eventing calendar and results source.
- Refresh upcoming events daily into `data/upcoming_events.json`.
- Refresh recent completed results daily into `data/fei_results.json`.
- Upload refreshed JSON as artifacts first; promote to production only after
  schema validation and source-quality checks pass.
- Add national federation adapters one at a time after FEI calendar/result
  refresh is stable.
- Preserve raw source HTML or API payloads where permitted for auditability.

## Probability model path

1. **Baseline:** weighted recent-form model from public results.
2. **Phase model:** estimate dressage, show jumping, cross-country jumping, and
   cross-country time separately.
3. **Monte Carlo markets:** simulate final scores to produce win, top 3, top 10,
   best dressage, and clear-round probabilities.
4. **Ratings:** add Elo-style rider, horse, and combination ratings by level.
5. **Bayesian updates:** shrink sparse combinations toward level/event priors.
6. **Event difficulty:** normalize scores by venue, level, ground conditions, and
   historical class strength.
7. **Non-completion:** replace priors with observed withdrawal, elimination, and
   retirement rates once source feeds include status history.

The initial executable version lives in `equibets.probability` and deliberately
returns probabilities only. It does not calculate odds, margin, stake limits, or
settlement for money.

## Frontend MVP pages

- **Dashboard:** summary cards, latest data refresh, top trending combinations.
- **Event page:** divisions, entries, market probabilities, prediction widgets.
- **Rider profile:** results, level history, rankings, phase trends.
- **Horse profile:** performance trends, riders, levels, phase reliability.
- **Combination profile:** recent form, expected finishing score, phase model,
  similar combinations.
- **Prediction game:** open markets, submitted predictions, points rules.
- **Leaderboard:** global, friends, event-specific, and season-specific views.
- **Admin panel:** imports, source health, duplicate review, manual corrections.

## Compliance boundary for the free MVP

- Use points, badges, and leaderboards only.
- Keep all copy framed as analytics and free predictions.
- Do not display decimal, fractional, or American betting odds.
- Do not accept payment, hold balances, settle stakes, or promote winnings.
- Keep source provenance and model run logs for auditability.
- Add jurisdiction-specific terms before public launch.
