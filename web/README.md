# SharpEdge Web

Read-only Next.js + Tailwind picks dashboard for the SharpEdge soccer engine. Lives in its own `/web` folder and never writes to Supabase or touches the Python engine in the rest of this repo.

## Setup

```bash
cd web
npm install
npm run dev
```

Env vars (`web/.env.local`, already populated for this project — see `.env.local.example` for a blank template):

```
SUPABASE_URL=
SUPABASE_ANON_KEY=
```

These are read **server-side only** (Server Components), so the anon key never ships to the browser bundle even though it's not prefixed `NEXT_PUBLIC_`. `SUPABASE_ANON_KEY` was carried over from the existing `frontend/elite_soccer_picks.html` dashboard, which already uses it for public reads against this same Supabase project.

### RLS

This app reads from `final_pro_soccer_picks`, `final_soccer_predictions`, `soccer_safe_zone`, and `games` using the **anon** key. If a table doesn't have a public `select` policy, that query comes back empty (not an error) and the UI just shows its empty state. If you add a new table to the dashboard later, make sure it has an RLS policy granting `select` to the `anon` role.

## What each section shows and why

- **Sharp Picks** reads `final_pro_soccer_picks`, which the engine already restricts to `final_allowed = true` rows for today/upcoming games only (see `src/models/build_soccer_calibrated_value.py` and `build_final_pro_soccer_picks.py`). It's joined (in `src/lib/data.ts`, in application code — there's no FK between these tables) against `final_soccer_predictions` to pull the **calibrated** confidence and no-vig edge that `apply_honest_calibration.py` computes.

  The edge badge only shows when it represents a real, positive value bet: real odds must back it (`bookmaker` + `odds_decimal` present) and the edge must fall in the same sane band (`0% < edge <= 15%`) that the engine's own honesty layer uses to flag an edge as `REAL` rather than `suspect` or `no-odds`. If a pick has no odds-backed edge, the card just omits the badge instead of showing a misleading number.

- **Safe Zone** reads `soccer_safe_zone` (`balanced_pick`/`balanced_prob`, `banker_pick`/`banker_prob`). That table has no date column and the engine never prunes it, so this app joins it against `games.game_date` to only show today/upcoming matches.

## PWA

`app/manifest.ts` + code-generated icons (`app/icon.tsx`, `app/apple-icon.tsx`, `app/icons/[size]/route.tsx`) + `public/sw.js` (network-first, falls back to cache only when offline — picks data is never served stale while online). Installable on Android/desktop Chrome and addable to the home screen on iOS Safari.

## Notes

- Next.js 16 / React 19 — this is a newer major version than older docs/training data may assume; see `node_modules/next/dist/docs` for the bundled docs if something looks unfamiliar.
- No MLB data — the engine only has a working soccer pipeline today, so there's nothing else to read yet.
