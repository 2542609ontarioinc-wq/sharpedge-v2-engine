# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

SharpEdge V2 is a sports betting probability engine (per `docs/FEATURE_ARCHITECTURE.md`: "not a random picks app... a probability engine"). It ingests fixtures/odds from external APIs into Supabase (Postgres), builds feature tables, runs prediction models, calibrates them against market odds, and publishes only the picks that clear a safety/value bar. The only sport with a working end-to-end pipeline today is **soccer**. MLB is designed in `docs/FEATURE_ARCHITECTURE.md` and `requirements.txt` already includes `pybaseball`/`xgboost`/`lightgbm`/`scikit-learn`, but no MLB ingestion/model code exists yet — don't assume those libraries are wired up to anything.

Read `docs/FEATURE_ARCHITECTURE.md` for the full intended model architecture (per-market models, feature lists, output shapes) before adding a new model or feature.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in keys below
```

Required env vars (validated by `src/config/settings.validate_settings()`): `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `ODDS_API_KEY`, `SPORTSDATA_KEY`, `APISPORTS_KEY`, `OPENWEATHER_API_KEY`. There is no local database — all reads/writes go straight to the Supabase project referenced by `SUPABASE_URL`, including from a dev machine.

## Running things

There is no test framework (no pytest/unittest anywhere). "Testing" here means either:
- `scripts/test_*.py` — manual scripts that hit a real external API (apisports, odds API, sportsdataio, supabase) and print the raw response. Run directly, e.g. `python -m scripts.test_apisports`.
- `scripts/check_*.py` — one per table, queries Supabase and prints rows for eyeballing after a pipeline run, e.g. `python -m scripts.check_final_predictions`.

Every module is run with `python -m`, never executed as a bare script, because they import via the `src.` package path:

```bash
python -m src.ingestion.sync_soccer_games
python -m src.models.build_final_pro_soccer_picks
```

**Pipeline orchestrators** (`scripts/run_*.py`) are plain lists of `python -m ...` commands run via `subprocess`, in dependency order. Two are live and distinct; the others are superseded earlier drafts kept around — check git history / comments before trusting one blindly:
- `scripts/run_sharp_engine.py` — canonical end-to-end soccer build (ingest → history/foundation → per-game features → Dixon-Coles model → multi-market selection → calibration/no-vig honesty layer → data quality gate → pro value/safety features → final picks → cleanup). Numbered comment blocks in the file describe each stage. Run daily via `.github/workflows/soccer_daily_automation.yml` (confirmed: the workflow calls `scripts.run_sharp_engine`, not the older `run_full_soccer_engine`).
- `scripts/run_soccer_live_monitor.py` — short loop for in-progress/recently-finished games: live odds/lineups → safety engine v3 → elite score → promotion events → grading → adaptive weights → master picks → analytics feedback → CLV tracking. Runs every 10 minutes via `.github/workflows/soccer_live_monitor.yml`.
- `scripts/run_full_soccer_engine.py` / `run_full_soccer_engine_fixed.py` / `run_soccer_daily_pipeline.py` — earlier iterations of the daily build, missing later stages (calibration map, data quality gate, Dixon-Coles v3). Prefer `run_sharp_engine.py` for new work.

## Architecture

**Data flow:** `External APIs → Supabase tables (raw) → feature tables → prediction models → calibration/honesty layer → safety/value scoring → final pick tables → grading → analytics feedback → adaptive weights (loops back into predictions)`.

**Package layout under `src/`** (mirrors the flow above; `scripts/` holds orchestration + one-off/debug scripts, never imported by `src/`):
- `ingestion/` — pulls from external APIs (`apisports_client.py` wraps API-Sports football/baseball endpoints with `tenacity` retry) and upserts into raw Supabase tables (`games`, `teams`, `venues`, `soccer_odds`, etc.).
- `features/` — reads raw + history tables, computes/derives feature tables (form, rolling stats, opponent strength, rest/travel, weather, referee history, league baselines, global priors). Pure transform: read Supabase → compute → upsert Supabase.
- `models/` — prediction generation (`generate_*`), ensembling/selection (`build_final_predictions*`), the calibration/"honesty" layer (`build_calibration_map`, `apply_honest_calibration`, `apply_calibration`), value/safety scoring (`build_soccer_market_value`, `build_soccer_model_safety_flags`, `apply_safety_to_market_value`, `build_soccer_safety_engine_v2/v3`), and final publish tables (`build_final_pro_soccer_picks`, `build_soccer_master_picks`).
- `grading/` — scores settled picks against final results (`grade_soccer_picks.py`).
- `analytics/` — turns graded history into feedback: `build_soccer_analytics_feedback.py` buckets picks (by market/tier/confidence/CLV) and computes win rate/ROI per bucket; `build_soccer_adaptive_weights.py` turns that into weight adjustments; `apply_soccer_adaptive_weights.py` applies them to live predictions. This is the self-tuning loop — it reads its own pipeline's graded output, not external data.
- `live/`, `picks/`, `parlays/`, `utils/` — currently empty directories; parlay logic actually lives in `src/models/build_parlay_builder.py`. Don't assume code lives in the directory its name suggests — check `src/models/` first.

**Module conventions** (every ingestion/feature/model script follows this shape — match it for new modules):
```python
from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
# ... read via supabase.table(...).select(...).execute().data
# ... transform in plain Python (pandas is a dependency but most scripts use raw dicts/lists)
# ... write via supabase.table(...).upsert(data, on_conflict="...").execute()
def main(): ...
if __name__ == "__main__":
    main()
```
Status output uses plain `print(...)`, with a `✅` prefix on the final summary line — no logging framework. Timestamps/dates are bucketed in `America/Toronto` time (`ZoneInfo("America/Toronto")`), not UTC — game dates, "today", and run dates all key off Toronto local date because that's the product's audience timezone, not the API's.

**SQL migrations** (`sql/NNN_description.sql`) are plain `create table if not exists` files, numbered sequentially, applied by hand against Supabase — there's no migration runner. When adding a table, add the next-numbered file; check the highest existing number first (currently 055).

**Frontend** (`frontend/elite_soccer_picks.html`): a single static HTML file with the Supabase JS client embedded directly (hardcoded URL + anon key — that's expected for a Supabase anon/RLS setup, not a leak). It queries views like `soccer_master_today_view` directly; it is not built/bundled and has no connection to the Python pipeline beyond reading the tables that pipeline writes. `*_backup.html` / `*_before_v2.html` are kept-around snapshots, not active code.

**`web/`**: a separate Next.js (App Router, TypeScript, Tailwind v4) + Supabase dashboard — see `web/README.md`. It's a second, independent frontend (not a replacement for `frontend/elite_soccer_picks.html`), reads the same Supabase project read-only via the anon key in `web/.env.local`, and has its own `package.json`/`node_modules` isolated from the Python engine. Run it with `cd web && npm run dev`. Next.js here is v16 — newer than most training data assumes; check `web/node_modules/next/dist/docs` before assuming an older-Next pattern still applies.

## Git state gotcha

Most of this repository (`src/`, most of `scripts/`, `sql/`, `docs/`, `frontend/`, `exports/`) is currently **untracked** in git — only a handful of files (the GitHub workflows, `README.md`, `requirements.txt`, and a few live-monitor/master-picks modules) are committed. Don't assume `git log`/`git blame` on an untracked file will tell you anything; check `git status` before relying on history for context.
