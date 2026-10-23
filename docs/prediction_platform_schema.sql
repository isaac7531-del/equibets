-- PostgreSQL schema for the FEI/eventing prediction platform.
-- This schema supports analytics and free-play predictions only.
-- It intentionally excludes betting odds, balances, deposits, withdrawals, and staking settlement.

create extension if not exists pgcrypto;

create table data_sources (
  id text primary key,
  display_name text not null,
  source_type text not null
    check (source_type in ('official_api', 'licensed_feed', 'permitted_scrape', 'manual_upload', 'public_reference')),
  base_url text,
  robots_url text,
  terms_url text,
  licence_notes text,
  source_priority integer not null,
  is_active boolean not null default true,
  approved_for_ingest boolean not null default false,
  raw_storage_allowed boolean not null default false,
  last_compliance_review_at timestamptz,
  compliance_reviewed_by uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table scrape_jobs (
  id uuid primary key default gen_random_uuid(),
  source_id text not null references data_sources(id),
  job_type text not null
    check (job_type in ('calendar', 'entries', 'results', 'horse_profile', 'rider_profile', 'manual_upload')),
  status text not null
    check (status in ('queued', 'running', 'succeeded', 'failed', 'partial', 'skipped')),
  requested_window_start date,
  requested_window_end date,
  started_at timestamptz,
  completed_at timestamptz,
  records_seen integer not null default 0,
  records_inserted integer not null default 0,
  records_updated integer not null default 0,
  records_failed integer not null default 0,
  error_message text,
  initiated_by uuid,
  created_at timestamptz not null default now()
);

create table scrape_job_events (
  id uuid primary key default gen_random_uuid(),
  scrape_job_id uuid not null references scrape_jobs(id) on delete cascade,
  severity text not null check (severity in ('info', 'warning', 'error')),
  message text not null,
  source_url text,
  source_record_id text,
  created_at timestamptz not null default now()
);

create table raw_source_snapshots (
  id uuid primary key default gen_random_uuid(),
  scrape_job_id uuid not null references scrape_jobs(id) on delete cascade,
  source_id text not null references data_sources(id),
  source_url text not null,
  content_hash text not null,
  storage_url text,
  captured_at timestamptz not null default now(),
  unique (source_id, content_hash)
);

create table horses (
  id uuid primary key default gen_random_uuid(),
  display_name text not null,
  normalized_name text not null,
  fei_horse_id text unique,
  country_code char(3),
  sex text,
  birth_year integer,
  color text,
  owner_name text,
  source_confidence text not null default 'low'
    check (source_confidence in ('low', 'medium', 'high')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table riders (
  id uuid primary key default gen_random_uuid(),
  display_name text not null,
  normalized_name text not null,
  fei_rider_id text unique,
  nation_code char(3),
  source_confidence text not null default 'low'
    check (source_confidence in ('low', 'medium', 'high')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table horse_rider_combinations (
  id uuid primary key default gen_random_uuid(),
  horse_id uuid not null references horses(id),
  rider_id uuid not null references riders(id),
  first_seen_on date,
  last_seen_on date,
  created_at timestamptz not null default now(),
  unique (horse_id, rider_id)
);

create table events (
  id uuid primary key default gen_random_uuid(),
  source_id text references data_sources(id),
  source_event_id text,
  name text not null,
  normalized_name text not null,
  venue text,
  location text,
  country_code char(3),
  starts_on date not null,
  ends_on date,
  source_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (source_id, source_event_id)
);

create table competitions (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references events(id) on delete cascade,
  source_id text references data_sources(id),
  source_competition_id text,
  competition_name text,
  level_code text not null,
  level_group text not null,
  format text check (format in ('short', 'long', 'unknown')),
  section_name text,
  class_name text,
  optimum_time_seconds integer,
  source_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table entries (
  id uuid primary key default gen_random_uuid(),
  competition_id uuid not null references competitions(id) on delete cascade,
  horse_id uuid not null references horses(id),
  rider_id uuid not null references riders(id),
  combination_id uuid not null references horse_rider_combinations(id),
  source_id text references data_sources(id),
  source_entry_id text,
  horse_fei_id text,
  rider_fei_id text,
  nation_code char(3),
  entry_number text,
  start_order integer,
  entry_status text not null default 'entered'
    check (entry_status in ('entered', 'accepted', 'waitlisted', 'withdrawn', 'started', 'completed', 'eliminated', 'retired')),
  imported_at timestamptz not null default now(),
  unique (competition_id, horse_id, rider_id)
);

create table results (
  id uuid primary key default gen_random_uuid(),
  competition_id uuid not null references competitions(id) on delete cascade,
  entry_id uuid references entries(id),
  horse_id uuid not null references horses(id),
  rider_id uuid not null references riders(id),
  combination_id uuid not null references horse_rider_combinations(id),
  source_id text not null references data_sources(id),
  source_result_id text not null,
  event_date date not null,
  nation_code char(3),
  placing integer,
  completion_status text not null
    check (completion_status in ('completed', 'eliminated', 'retired', 'withdrawn', 'dns', 'dq', 'mer_only', 'unknown')),
  dressage_score numeric(6, 2),
  show_jumping_penalties numeric(6, 2),
  cross_country_jump_penalties numeric(6, 2),
  cross_country_time_penalties numeric(6, 2),
  final_score numeric(7, 2),
  mer_status text,
  collected_at timestamptz not null,
  created_at timestamptz not null default now(),
  unique (source_id, source_result_id)
);

create table phase_scores (
  id uuid primary key default gen_random_uuid(),
  result_id uuid not null references results(id) on delete cascade,
  phase text not null check (phase in ('dressage', 'show_jumping', 'cross_country')),
  score numeric(7, 2),
  penalties numeric(7, 2),
  jumping_penalties numeric(7, 2),
  time_penalties numeric(7, 2),
  time_seconds integer,
  status text check (status in ('clear', 'faults', 'eliminated', 'retired', 'withdrawn', 'unknown')),
  unique (result_id, phase)
);

create table performance_rollups (
  id uuid primary key default gen_random_uuid(),
  subject_type text not null check (subject_type in ('horse', 'rider', 'combination')),
  horse_id uuid references horses(id),
  rider_id uuid references riders(id),
  combination_id uuid references horse_rider_combinations(id),
  level_group text not null,
  format text check (format in ('short', 'long', 'all')),
  window text not null check (window in ('last_3', 'last_5', 'last_12_months', 'career_at_level')),
  start_count integer not null,
  avg_dressage_score numeric(6, 2),
  avg_show_jumping_penalties numeric(6, 2),
  avg_cross_country_jump_penalties numeric(6, 2),
  avg_cross_country_time_penalties numeric(6, 2),
  avg_final_score numeric(7, 2),
  completion_rate numeric(6, 5),
  clear_show_jumping_rate numeric(6, 5),
  clear_cross_country_rate numeric(6, 5),
  top_10_rate numeric(6, 5),
  calculated_at timestamptz not null default now(),
  check (
    (subject_type = 'horse' and horse_id is not null)
    or (subject_type = 'rider' and rider_id is not null)
    or (subject_type = 'combination' and combination_id is not null)
  )
);

create table event_difficulty_scores (
  id uuid primary key default gen_random_uuid(),
  event_id uuid references events(id) on delete cascade,
  competition_id uuid references competitions(id) on delete cascade,
  level_group text not null,
  sample_size integer not null,
  dressage_adjustment numeric(6, 2) not null default 0,
  show_jumping_adjustment numeric(6, 2) not null default 0,
  cross_country_jump_adjustment numeric(6, 2) not null default 0,
  cross_country_time_adjustment numeric(6, 2) not null default 0,
  final_score_adjustment numeric(7, 2) not null default 0,
  confidence text not null check (confidence in ('low', 'medium', 'high')),
  calculated_at timestamptz not null default now()
);

create table prediction_runs (
  id uuid primary key default gen_random_uuid(),
  competition_id uuid not null references competitions(id) on delete cascade,
  model_name text not null,
  model_version text not null,
  status text not null check (status in ('running', 'succeeded', 'failed')),
  input_result_count integer not null,
  entry_count integer not null,
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  error_message text
);

create table predictions (
  id uuid primary key default gen_random_uuid(),
  prediction_run_id uuid not null references prediction_runs(id) on delete cascade,
  competition_id uuid not null references competitions(id) on delete cascade,
  entry_id uuid not null references entries(id) on delete cascade,
  horse_id uuid not null references horses(id),
  rider_id uuid not null references riders(id),
  predicted_dressage_score numeric(6, 2) not null,
  predicted_show_jumping_penalties numeric(6, 2) not null,
  predicted_cross_country_jump_penalties numeric(6, 2) not null,
  predicted_cross_country_time_penalties numeric(6, 2) not null,
  predicted_final_score numeric(7, 2) not null,
  predicted_rank integer not null,
  confidence_score numeric(5, 2) not null,
  confidence_label text not null check (confidence_label in ('low', 'medium', 'high')),
  feature_summary jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (prediction_run_id, entry_id)
);

create table identity_match_reviews (
  id uuid primary key default gen_random_uuid(),
  entity_type text not null check (entity_type in ('horse', 'rider')),
  source_id text not null references data_sources(id),
  source_entity_id text,
  source_name text not null,
  source_nation_code char(3),
  suggested_horse_id uuid references horses(id),
  suggested_rider_id uuid references riders(id),
  status text not null default 'pending'
    check (status in ('pending', 'resolved', 'rejected')),
  resolution_notes text,
  resolved_by uuid,
  resolved_at timestamptz,
  created_at timestamptz not null default now()
);

create index horses_normalized_name_idx on horses(normalized_name);
create unique index competitions_event_level_section_class_uidx
  on competitions (event_id, level_code, coalesce(section_name, ''), coalesce(class_name, ''));
create index riders_normalized_name_idx on riders(normalized_name);
create index events_starts_on_idx on events(starts_on);
create index competitions_event_id_idx on competitions(event_id);
create index entries_competition_id_idx on entries(competition_id);
create index results_horse_level_date_idx on results(horse_id, event_date desc);
create index results_rider_level_date_idx on results(rider_id, event_date desc);
create index phase_scores_result_id_idx on phase_scores(result_id);
create index performance_rollups_subject_idx on performance_rollups(subject_type, level_group, window);
create index predictions_competition_rank_idx on predictions(competition_id, predicted_rank);
create index scrape_jobs_source_status_idx on scrape_jobs(source_id, status, created_at desc);
