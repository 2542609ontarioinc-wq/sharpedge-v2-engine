-- SharpEdge V2 Core Schema
-- Prediction Engine First. Picks Second.

create extension if not exists "uuid-ossp";

-- =========================
-- CORE SPORTS
-- =========================

create table if not exists sports (
  id uuid primary key default uuid_generate_v4(),
  sport_key text unique not null,
  name text not null,
  active boolean default true,
  created_at timestamptz default now()
);

create table if not exists leagues (
  id uuid primary key default uuid_generate_v4(),
  sport_key text not null,
  league_key text unique not null,
  name text not null,
  country text,
  season text,
  active boolean default true,
  created_at timestamptz default now()
);

create table if not exists teams (
  id uuid primary key default uuid_generate_v4(),
  sport_key text not null,
  league_key text,
  external_team_id text,
  name text not null,
  short_name text,
  abbreviation text,
  city text,
  country text,
  logo_url text,
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now(),
  unique(sport_key, external_team_id)
);

create table if not exists players (
  id uuid primary key default uuid_generate_v4(),
  sport_key text not null,
  external_player_id text,
  team_id uuid references teams(id) on delete set null,
  full_name text not null,
  position text,
  handedness text,
  birth_date date,
  nationality text,
  active boolean default true,
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now(),
  unique(sport_key, external_player_id)
);

-- =========================
-- VENUES / OFFICIALS
-- =========================

create table if not exists venues (
  id uuid primary key default uuid_generate_v4(),
  sport_key text not null,
  external_venue_id text,
  name text not null,
  city text,
  country text,
  surface text,
  roof_type text,
  capacity integer,
  latitude numeric,
  longitude numeric,
  park_factor jsonb default '{}'::jsonb,
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now(),
  unique(sport_key, external_venue_id)
);

create table if not exists officials (
  id uuid primary key default uuid_generate_v4(),
  sport_key text not null,
  external_official_id text,
  full_name text not null,
  role text,
  avg_cards numeric,
  avg_fouls numeric,
  avg_penalties numeric,
  avg_strike_zone_bias numeric,
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now(),
  unique(sport_key, external_official_id)
);

-- =========================
-- GAMES
-- =========================

create table if not exists games (
  id uuid primary key default uuid_generate_v4(),
  sport_key text not null,
  league_key text,
  external_game_id text not null,
  season text,
  game_date date not null,
  start_time_utc timestamptz,
  start_time_toronto timestamptz,
  home_team_id uuid references teams(id) on delete set null,
  away_team_id uuid references teams(id) on delete set null,
  home_team_name text not null,
  away_team_name text not null,
  venue_id uuid references venues(id) on delete set null,
  official_id uuid references officials(id) on delete set null,
  status text default 'scheduled',
  period text,
  clock text,
  home_score numeric default 0,
  away_score numeric default 0,
  source text,
  raw_json jsonb default '{}'::jsonb,
  last_synced_at timestamptz default now(),
  created_at timestamptz default now(),
  unique(sport_key, external_game_id)
);

create index if not exists idx_games_date on games(game_date);
create index if not exists idx_games_sport_date on games(sport_key, game_date);
create index if not exists idx_games_status on games(status);

-- =========================
-- LIVE DATA
-- =========================

create table if not exists live_game_snapshots (
  id uuid primary key default uuid_generate_v4(),
  game_id uuid references games(id) on delete cascade,
  captured_at timestamptz default now(),
  status text,
  period text,
  clock text,
  home_score numeric,
  away_score numeric,
  live_stats jsonb default '{}'::jsonb,
  raw_json jsonb default '{}'::jsonb
);

create table if not exists live_events (
  id uuid primary key default uuid_generate_v4(),
  game_id uuid references games(id) on delete cascade,
  external_event_id text,
  event_time_toronto timestamptz,
  period text,
  clock text,
  team_id uuid references teams(id) on delete set null,
  player_id uuid references players(id) on delete set null,
  event_type text,
  description text,
  value numeric,
  raw_json jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

-- =========================
-- ODDS / MARKETS
-- =========================

create table if not exists odds_snapshots (
  id uuid primary key default uuid_generate_v4(),
  game_id uuid references games(id) on delete cascade,
  sportsbook text not null,
  market_type text not null,
  selection text not null,
  line numeric,
  odds_american integer,
  odds_decimal numeric,
  implied_probability numeric,
  no_vig_probability numeric,
  captured_at timestamptz default now(),
  source text,
  raw_json jsonb default '{}'::jsonb
);

create index if not exists idx_odds_game_market on odds_snapshots(game_id, market_type);
create index if not exists idx_odds_captured on odds_snapshots(captured_at);

-- =========================
-- INJURIES / LINEUPS
-- =========================

create table if not exists injuries (
  id uuid primary key default uuid_generate_v4(),
  sport_key text not null,
  game_id uuid references games(id) on delete cascade,
  team_id uuid references teams(id) on delete set null,
  player_id uuid references players(id) on delete set null,
  player_name text,
  status text,
  injury text,
  notes text,
  reported_at timestamptz,
  source text,
  raw_json jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create table if not exists lineups (
  id uuid primary key default uuid_generate_v4(),
  game_id uuid references games(id) on delete cascade,
  team_id uuid references teams(id) on delete set null,
  player_id uuid references players(id) on delete set null,
  player_name text not null,
  lineup_status text,
  batting_order integer,
  position text,
  is_starter boolean default false,
  is_confirmed boolean default false,
  source text,
  raw_json jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

-- =========================
-- WEATHER
-- =========================

create table if not exists weather_snapshots (
  id uuid primary key default uuid_generate_v4(),
  game_id uuid references games(id) on delete cascade,
  captured_at timestamptz default now(),
  temperature numeric,
  wind_speed numeric,
  wind_direction text,
  humidity numeric,
  precipitation_probability numeric,
  condition text,
  impact_score numeric,
  raw_json jsonb default '{}'::jsonb
);

-- =========================
-- SOCCER STATS
-- =========================

create table if not exists soccer_match_stats (
  id uuid primary key default uuid_generate_v4(),
  game_id uuid references games(id) on delete cascade,
  team_id uuid references teams(id) on delete set null,
  possession numeric,
  shots numeric,
  shots_on_target numeric,
  xg numeric,
  corners numeric,
  fouls numeric,
  yellow_cards numeric,
  red_cards numeric,
  passes numeric,
  tackles numeric,
  raw_json jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create table if not exists soccer_player_stats (
  id uuid primary key default uuid_generate_v4(),
  game_id uuid references games(id) on delete cascade,
  player_id uuid references players(id) on delete set null,
  team_id uuid references teams(id) on delete set null,
  minutes numeric,
  goals numeric,
  assists numeric,
  shots numeric,
  shots_on_target numeric,
  xg numeric,
  xa numeric,
  passes numeric,
  tackles numeric,
  fouls_committed numeric,
  fouls_drawn numeric,
  yellow_cards numeric,
  red_cards numeric,
  raw_json jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

-- =========================
-- MLB STATS
-- =========================

create table if not exists mlb_team_stats (
  id uuid primary key default uuid_generate_v4(),
  game_id uuid references games(id) on delete cascade,
  team_id uuid references teams(id) on delete set null,
  runs numeric,
  hits numeric,
  errors numeric,
  walks numeric,
  strikeouts numeric,
  bullpen_innings numeric,
  bullpen_runs_allowed numeric,
  raw_json jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create table if not exists mlb_batter_stats (
  id uuid primary key default uuid_generate_v4(),
  game_id uuid references games(id) on delete cascade,
  player_id uuid references players(id) on delete set null,
  team_id uuid references teams(id) on delete set null,
  at_bats numeric,
  hits numeric,
  runs numeric,
  rbi numeric,
  total_bases numeric,
  walks numeric,
  strikeouts numeric,
  home_runs numeric,
  raw_json jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create table if not exists mlb_pitcher_stats (
  id uuid primary key default uuid_generate_v4(),
  game_id uuid references games(id) on delete cascade,
  player_id uuid references players(id) on delete set null,
  team_id uuid references teams(id) on delete set null,
  innings_pitched numeric,
  earned_runs numeric,
  hits_allowed numeric,
  walks numeric,
  strikeouts numeric,
  pitches numeric,
  is_starter boolean default false,
  raw_json jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create table if not exists mlb_statcast_daily (
  id uuid primary key default uuid_generate_v4(),
  player_id uuid references players(id) on delete set null,
  player_name text,
  team_id uuid references teams(id) on delete set null,
  stat_date date,
  stat_type text,
  exit_velocity numeric,
  launch_angle numeric,
  barrel_rate numeric,
  hard_hit_rate numeric,
  xba numeric,
  xslg numeric,
  xwoba numeric,
  k_rate numeric,
  bb_rate numeric,
  raw_json jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

-- =========================
-- FEATURE STORE
-- =========================

create table if not exists model_features (
  id uuid primary key default uuid_generate_v4(),
  game_id uuid references games(id) on delete cascade,
  sport_key text not null,
  feature_version text default 'v1',
  team_features jsonb default '{}'::jsonb,
  player_features jsonb default '{}'::jsonb,
  market_features jsonb default '{}'::jsonb,
  context_features jsonb default '{}'::jsonb,
  data_quality_score numeric,
  created_at timestamptz default now()
);

-- =========================
-- MODEL PREDICTIONS
-- =========================

create table if not exists model_predictions (
  id uuid primary key default uuid_generate_v4(),
  game_id uuid references games(id) on delete cascade,
  sport_key text not null,
  model_name text not null,
  model_version text default 'v1',
  prediction_type text not null,
  selection text,
  projected_value numeric,
  probability numeric,
  fair_odds_decimal numeric,
  confidence_score numeric,
  risk_score numeric,
  explanation jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create index if not exists idx_model_predictions_game on model_predictions(game_id);
create index if not exists idx_model_predictions_type on model_predictions(prediction_type);

-- =========================
-- PICK ENGINE
-- =========================

create table if not exists pick_candidates (
  id uuid primary key default uuid_generate_v4(),
  game_id uuid references games(id) on delete cascade,
  prediction_id uuid references model_predictions(id) on delete set null,
  sport_key text not null,
  league_key text,
  pick_type text not null,
  bet_description text not null,
  selection text,
  line numeric,
  odds_american integer,
  odds_decimal numeric,
  model_probability numeric,
  market_probability numeric,
  edge numeric,
  confidence_score numeric,
  risk_level text,
  tier text,
  reason text,
  supporting_data jsonb default '{}'::jsonb,
  status text default 'candidate',
  created_at timestamptz default now()
);

create table if not exists final_picks (
  id uuid primary key default uuid_generate_v4(),
  candidate_id uuid references pick_candidates(id) on delete set null,
  game_id uuid references games(id) on delete cascade,
  sport_key text not null,
  league_key text,
  game_date date not null,
  game_time_toronto timestamptz,
  pick_type text not null,
  bet_description text not null,
  odds_american integer,
  odds_decimal numeric,
  model_probability numeric,
  edge numeric,
  confidence_score numeric,
  risk_level text,
  tier text,
  access text default 'free',
  is_featured boolean default false,
  is_global_featured boolean default false,
  result text default 'Pending',
  units numeric default 1,
  profit_loss_units numeric default 0,
  notes text,
  why_json jsonb default '{}'::jsonb,
  created_at timestamptz default now(),
  graded_at timestamptz
);

create index if not exists idx_final_picks_date on final_picks(game_date);
create index if not exists idx_final_picks_result on final_picks(result);

-- =========================
-- PARLAYS
-- =========================

create table if not exists parlays (
  id uuid primary key default uuid_generate_v4(),
  sport_key text,
  parlay_name text,
  game_date date not null,
  combined_probability numeric,
  combined_odds_decimal numeric,
  risk_level text,
  confidence_score numeric,
  status text default 'Pending',
  notes text,
  created_at timestamptz default now(),
  graded_at timestamptz
);

create table if not exists parlay_legs (
  id uuid primary key default uuid_generate_v4(),
  parlay_id uuid references parlays(id) on delete cascade,
  final_pick_id uuid references final_picks(id) on delete cascade,
  leg_order integer,
  leg_probability numeric,
  created_at timestamptz default now()
);

-- =========================
-- BACKTESTING / ANALYTICS
-- =========================

create table if not exists model_backtests (
  id uuid primary key default uuid_generate_v4(),
  sport_key text not null,
  model_name text not null,
  model_version text not null,
  start_date date,
  end_date date,
  total_picks integer,
  wins integer,
  losses integer,
  pushes integer,
  win_rate numeric,
  roi numeric,
  units numeric,
  metrics jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create table if not exists analytics_daily (
  id uuid primary key default uuid_generate_v4(),
  report_date date not null,
  sport_key text,
  league_key text,
  total_picks integer default 0,
  wins integer default 0,
  losses integer default 0,
  pushes integer default 0,
  voids integer default 0,
  win_rate numeric default 0,
  units numeric default 0,
  roi numeric default 0,
  created_at timestamptz default now(),
  unique(report_date, sport_key, league_key)
);

-- =========================
-- SOURCE LOGGING
-- =========================

create table if not exists ingestion_runs (
  id uuid primary key default uuid_generate_v4(),
  source text not null,
  sport_key text,
  job_name text not null,
  status text not null,
  started_at timestamptz default now(),
  finished_at timestamptz,
  rows_processed integer default 0,
  error_message text,
  metadata jsonb default '{}'::jsonb
);

-- =========================
-- SEED SPORTS
-- =========================

insert into sports (sport_key, name)
values
  ('soccer', 'Soccer'),
  ('baseball_mlb', 'MLB'),
  ('football_nfl', 'NFL'),
  ('basketball_nba', 'NBA'),
  ('hockey_nhl', 'NHL'),
  ('tennis', 'Tennis')
on conflict (sport_key) do nothing;