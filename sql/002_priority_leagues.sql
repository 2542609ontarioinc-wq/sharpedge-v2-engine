create table if not exists priority_leagues (
    id uuid primary key default gen_random_uuid(),

    sport_key text not null,

    league_id text not null,

    league_name text not null,

    country text,

    priority integer not null default 1,

    enabled boolean not null default true,

    created_at timestamptz not null default now(),

    unique (sport_key, league_id)
);

insert into priority_leagues
(sport_key, league_id, league_name, country, priority)

values

('soccer','1','World Cup','World',1),

('soccer','4','UEFA Euro Championship','Europe',1),

('soccer','39','Premier League','England',1),

('soccer','140','La Liga','Spain',1),

('soccer','78','Bundesliga','Germany',1),

('soccer','135','Serie A','Italy',1),

('soccer','61','Ligue 1','France',1),

('soccer','253','Major League Soccer','USA',1),

('soccer','479','Canadian Premier League','Canada',1),

('soccer','2','UEFA Champions League','Europe',1),

('soccer','3','UEFA Europa League','Europe',1)

on conflict do nothing;
