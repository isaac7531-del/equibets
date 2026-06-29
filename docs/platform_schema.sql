-- PostgreSQL schema for the legal analytics and free prediction MVP.
-- No real-money betting, balances, deposits, withdrawals, or settlement tables.

create table data_sources (
  id text primary key,
  display_name text not null,
  homepage_url text not null,
  source_priority integer not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table riders (
  id uuid primary key default gen_random_uuid(),
  display_name text not null,
  country_code char(3),
  fei_person_id text unique,
  created_at timestamptz not null default now()
);

create table horses (
  id uuid primary key default gen_random_uuid(),
  display_name text not null,
  country_code char(3),
  fei_horse_id text unique,
  created_at timestamptz not null default now()
);

create table horse_rider_combinations (
  id uuid primary key default gen_random_uuid(),
  rider_id uuid not null references riders(id),
  horse_id uuid not null references horses(id),
  first_seen_on date,
  last_seen_on date,
  created_at timestamptz not null default now(),
  unique (rider_id, horse_id)
);

create table events (
  id uuid primary key default gen_random_uuid(),
  source_id text references data_sources(id),
  source_event_id text,
  name text not null,
  country_code char(3),
  venue text,
  starts_on date not null,
  ends_on date,
  created_at timestamptz not null default now(),
  unique (source_id, source_event_id)
);

create table event_divisions (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references events(id) on delete cascade,
  level text not null,
  division_name text,
  optimum_time_seconds integer,
  created_at timestamptz not null default now(),
  unique (event_id, level, division_name)
);

create table event_entries (
  id uuid primary key default gen_random_uuid(),
  division_id uuid not null references event_divisions(id) on delete cascade,
  combination_id uuid not null references horse_rider_combinations(id),
  entry_number text,
  status text not null default 'entered'
    check (status in ('entered', 'started', 'completed', 'withdrawn', 'eliminated', 'retired')),
  created_at timestamptz not null default now(),
  unique (division_id, combination_id)
);

create table result_imports (
  id uuid primary key default gen_random_uuid(),
  source_id text not null references data_sources(id),
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  status text not null check (status in ('running', 'succeeded', 'failed', 'partial')),
  raw_artifact_url text,
  notes text
);

create table event_results (
  id uuid primary key default gen_random_uuid(),
  entry_id uuid not null references event_entries(id) on delete cascade,
  import_id uuid references result_imports(id),
  source_id text not null references data_sources(id),
  source_record_id text not null,
  source_priority integer not null,
  result_status text not null
    check (result_status in ('completed', 'withdrawn', 'eliminated', 'retired')),
  dressage_score numeric(5, 1),
  show_jumping_penalties numeric(5, 1),
  cross_country_jump_penalties numeric(5, 1),
  cross_country_time_penalties numeric(5, 1),
  final_score numeric(6, 1),
  placing integer,
  collected_at timestamptz not null,
  created_at timestamptz not null default now(),
  unique (source_id, source_record_id)
);

create table model_runs (
  id uuid primary key default gen_random_uuid(),
  division_id uuid references event_divisions(id),
  model_name text not null,
  model_version text not null,
  run_at timestamptz not null default now(),
  input_result_count integer not null,
  simulation_count integer,
  notes text
);

create table entry_model_predictions (
  id uuid primary key default gen_random_uuid(),
  model_run_id uuid not null references model_runs(id) on delete cascade,
  entry_id uuid not null references event_entries(id) on delete cascade,
  expected_dressage_score numeric(5, 1) not null,
  expected_show_jumping_penalties numeric(5, 1) not null,
  expected_cross_country_jump_penalties numeric(5, 1) not null,
  expected_cross_country_time_penalties numeric(5, 1) not null,
  expected_finishing_score numeric(6, 1) not null,
  elimination_probability numeric(6, 5) not null,
  retirement_probability numeric(6, 5) not null,
  withdrawal_probability numeric(6, 5) not null,
  win_probability numeric(6, 5) not null,
  top_3_probability numeric(6, 5) not null,
  top_10_probability numeric(6, 5) not null,
  best_dressage_probability numeric(6, 5) not null,
  clear_show_jumping_probability numeric(6, 5) not null,
  clear_cross_country_probability numeric(6, 5) not null,
  confidence text not null check (confidence in ('low', 'medium', 'high')),
  unique (model_run_id, entry_id)
);

create table user_profiles (
  id uuid primary key,
  display_name text not null,
  country_code char(3),
  created_at timestamptz not null default now()
);

create table prediction_markets (
  id uuid primary key default gen_random_uuid(),
  division_id uuid not null references event_divisions(id) on delete cascade,
  market_type text not null
    check (market_type in ('win', 'top_3', 'top_10', 'best_dressage', 'clear_show_jumping', 'clear_cross_country', 'head_to_head', 'final_score_over_under')),
  title text not null,
  status text not null default 'open'
    check (status in ('draft', 'open', 'locked', 'scored', 'void')),
  closes_at timestamptz not null,
  created_at timestamptz not null default now()
);

create table prediction_options (
  id uuid primary key default gen_random_uuid(),
  market_id uuid not null references prediction_markets(id) on delete cascade,
  entry_id uuid references event_entries(id),
  label text not null,
  line_value numeric(6, 1),
  model_probability numeric(6, 5),
  is_correct boolean,
  unique (market_id, label)
);

create table user_predictions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references user_profiles(id),
  market_id uuid not null references prediction_markets(id) on delete cascade,
  option_id uuid not null references prediction_options(id),
  points_staked integer not null default 1 check (points_staked between 1 and 10),
  points_awarded integer,
  submitted_at timestamptz not null default now(),
  unique (user_id, market_id)
);

create table leaderboard_snapshots (
  id uuid primary key default gen_random_uuid(),
  scope text not null check (scope in ('global', 'event', 'season')),
  scope_id uuid,
  user_id uuid not null references user_profiles(id),
  points integer not null,
  rank integer not null,
  calculated_at timestamptz not null default now()
);

create index event_results_entry_id_idx on event_results(entry_id);
create index event_results_collected_at_idx on event_results(collected_at desc);
create index entry_model_predictions_model_run_idx on entry_model_predictions(model_run_id);
create index prediction_markets_division_status_idx on prediction_markets(division_id, status);
create index user_predictions_user_id_idx on user_predictions(user_id);
