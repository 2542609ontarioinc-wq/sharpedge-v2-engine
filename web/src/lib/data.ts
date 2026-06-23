import { supabase } from "./supabase";
import type {
  GradedPick,
  MarketStats,
  MLBDiagnostics,
  MLBLivePickStatus,
  MLBLiveState,
  MLBMarketStats,
  MLBModelAnalytics,
  MLBModelLabGame,
  MLBModelVersionData,
  MLBPickDetail,
  MLBPlayerProp,
  MLBPropDetail,
  MLBSafeZonePick,
  MLBSharpPick,
  MLBSubscriberResults,
  MLBSubscriberSegment,
  MLBTrackRecord,
  SafeZonePick,
  SharpPick,
  TrackRecord,
} from "./types";

const TORONTO_TZ = "America/Toronto";

function todayTorontoISODate(): string {
  // en-CA formats as YYYY-MM-DD, matching the `game_date` column written by the engine.
  return new Intl.DateTimeFormat("en-CA", { timeZone: TORONTO_TZ }).format(new Date());
}

function toNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function norm(value: string | null | undefined): string {
  return (value ?? "").trim().toLowerCase();
}

type GameRow = {
  id: string;
  game_date: string | null;
  start_time_toronto: string | null;
  status: string | null;
};

async function fetchGamesById(gameIds: string[]): Promise<Map<string, GameRow>> {
  const map = new Map<string, GameRow>();
  if (gameIds.length === 0) return map;

  const { data, error } = await supabase
    .from("games")
    .select("id, game_date, start_time_toronto, status")
    .in("id", gameIds);

  if (error) throw error;

  for (const row of data ?? []) {
    map.set(row.id, row as GameRow);
  }
  return map;
}

type FinalProSoccerPick = {
  game_id: string;
  home_team_name: string;
  away_team_name: string;
  pick: string;
  market: string;
  bookmaker: string | null;
  final_value_rating: number | string | null;
  final_tier: string | null;
  confidence_tier: string | null;
  safety_score: number | string | null;
  matchup_score: number | string | null;
  explanation: string | null;
};

type FinalSoccerPrediction = {
  game_id: string;
  market: string | null;
  best_pick: string | null;
  confidence: number | string | null;
  bookmaker: string | null;
  odds_decimal: number | string | null;
  model_edge: number | string | null;
};

/**
 * Sharp Picks = final_pro_soccer_picks (already gated to final_allowed=true,
 * today/upcoming games only, refreshed every engine run) enriched with the
 * calibrated confidence + no-vig edge from final_soccer_predictions.
 *
 * Edge display rule mirrors apply_honest_calibration.py's own REAL / suspect /
 * no-odds classification (edge is only trustworthy when real odds back it and
 * it falls in the sane band the engine itself uses), narrowed to edge > 0
 * since this page only calls something a "value bet" when it is positive value.
 */
export async function getSharpPicks(): Promise<SharpPick[]> {
  const { data: proPicks, error: proError } = await supabase
    .from("final_pro_soccer_picks")
    .select(
      "game_id, home_team_name, away_team_name, pick, market, bookmaker, final_value_rating, final_tier, confidence_tier, safety_score, matchup_score, explanation"
    )
    .order("final_value_rating", { ascending: false });

  if (proError) throw proError;
  if (!proPicks || proPicks.length === 0) return [];

  const gameIds = [...new Set(proPicks.map((p) => p.game_id))];
  const today = todayTorontoISODate();

  // Filter games by date so engine-skip days don't leak yesterday's played picks.
  // Mirrors getSafeZone()'s .gte("game_date", today) guard.
  const [{ data: predictions, error: predError }, { data: gamesData, error: gamesError }] = await Promise.all([
    supabase
      .from("final_soccer_predictions")
      .select("game_id, market, best_pick, confidence, bookmaker, odds_decimal, model_edge")
      .in("game_id", gameIds)
      .order("created_at", { ascending: false }),
    supabase
      .from("games")
      .select("id, game_date, start_time_toronto, status")
      .in("id", gameIds)
      .gte("game_date", today),
  ]);

  if (predError) throw predError;
  if (gamesError) throw gamesError;

  const gamesById = new Map<string, GameRow>();
  for (const g of gamesData ?? []) gamesById.set(g.id, g as GameRow);

  const predsByGame = new Map<string, FinalSoccerPrediction[]>();
  for (const row of predictions ?? []) {
    const list = predsByGame.get(row.game_id) ?? [];
    list.push(row as FinalSoccerPrediction);
    predsByGame.set(row.game_id, list);
  }

  function matchPrediction(pro: FinalProSoccerPick): FinalSoccerPrediction | null {
    const candidates = predsByGame.get(pro.game_id) ?? [];
    if (candidates.length === 0) return null;
    const exact = candidates.find(
      (c) => norm(c.market) === norm(pro.market) && norm(c.best_pick) === norm(pro.pick)
    );
    if (exact) return exact;
    const sameMarket = candidates.find((c) => norm(c.market) === norm(pro.market));
    if (sameMarket) return sameMarket;
    return candidates[0];
  }

  return (proPicks as FinalProSoccerPick[])
    .filter((pro) => gamesById.has(pro.game_id)) // drop stale picks from engine-skip days
    .map((pro) => {
    const match = matchPrediction(pro);
    const edge = match ? toNumber(match.model_edge) : null;
    const hasOdds = Boolean(match?.bookmaker && match?.odds_decimal != null && edge !== null);
    // Cap at 30% — the engine's own sane-band ceiling. Picks above 30% are suspect;
    // picks at 15-30% (e.g. heavy-underdog WC games) are engine-approved and should show the badge.
    const isRealValue = hasOdds && edge !== null && edge > 0 && edge <= 30;

    const game = gamesById.get(pro.game_id);

    return {
      gameId: pro.game_id,
      homeTeam: pro.home_team_name,
      awayTeam: pro.away_team_name,
      pick: pro.pick,
      market: pro.market,
      bookmaker: pro.bookmaker,
      tier: pro.final_tier,
      confidenceTier: pro.confidence_tier,
      finalValueRating: toNumber(pro.final_value_rating),
      safetyScore: toNumber(pro.safety_score),
      matchupScore: toNumber(pro.matchup_score),
      explanation: pro.explanation,
      confidence: match ? toNumber(match.confidence) : null,
      edge,
      isRealValue,
      kickoff: game?.start_time_toronto ?? null,
    };
  });
}

type SoccerSafeZoneRow = {
  game_id: string;
  home_team_name: string;
  away_team_name: string;
  balanced_pick: string | null;
  balanced_prob: number | string | null;
  banker_pick: string | null;
  banker_prob: number | string | null;
};

/**
 * Safe Zone = soccer_safe_zone, which the engine never prunes by date, so we
 * scope it to today/upcoming games ourselves via the `games` table (same
 * Toronto-date convention the engine uses everywhere else).
 */
export async function getSafeZone(): Promise<SafeZonePick[]> {
  const { data: rows, error } = await supabase
    .from("soccer_safe_zone")
    .select("game_id, home_team_name, away_team_name, balanced_pick, balanced_prob, banker_pick, banker_prob");

  if (error) throw error;
  if (!rows || rows.length === 0) return [];

  const gameIds = [...new Set(rows.map((r) => r.game_id))];
  const today = todayTorontoISODate();

  const { data: games, error: gamesError } = await supabase
    .from("games")
    .select("id, game_date, start_time_toronto, status")
    .in("id", gameIds)
    .gte("game_date", today);

  if (gamesError) throw gamesError;

  const gamesById = new Map<string, GameRow>();
  for (const g of games ?? []) gamesById.set(g.id, g as GameRow);

  const picks: SafeZonePick[] = (rows as SoccerSafeZoneRow[])
    .filter((r) => gamesById.has(r.game_id))
    .map((r) => {
      const game = gamesById.get(r.game_id)!;
      return {
        gameId: r.game_id,
        homeTeam: r.home_team_name,
        awayTeam: r.away_team_name,
        balancedPick: r.balanced_pick,
        balancedProb: toNumber(r.balanced_prob),
        bankerPick: r.banker_pick,
        bankerProb: toNumber(r.banker_prob),
        kickoff: game.start_time_toronto,
      };
    });

  picks.sort((a, b) => {
    if (a.kickoff && b.kickoff) return a.kickoff.localeCompare(b.kickoff);
    if (a.kickoff) return -1;
    if (b.kickoff) return 1;
    return (b.balancedProb ?? 0) - (a.balancedProb ?? 0);
  });

  return picks;
}

type PickResultsRow = {
  market: string;
  total_picks: number;
  wins: number;
  losses: number;
  voids: number;
  win_rate: number | string | null;
  total_units: number | string | null;
  roi_percent: number | string | null;
};

type GradedPickRow = {
  game_id: string;
  home_team_name: string;
  away_team_name: string;
  market: string;
  pick: string;
  grade: string;
  odds_decimal: number | string | null;
  no_odds: boolean | null;
  units_result: number | string | null;
  home_score: number | null;
  away_score: number | null;
  graded_at: string | null;
};

export async function getTrackRecord(): Promise<TrackRecord> {
  const [summaryRes, picksRes] = await Promise.all([
    supabase
      .from("soccer_pick_results")
      .select(
        "market, total_picks, wins, losses, voids, win_rate, total_units, roi_percent"
      )
      .order("market"),
    supabase
      .from("soccer_pick_grades_v2")
      .select(
        "game_id, home_team_name, away_team_name, market, pick, grade, odds_decimal, no_odds, units_result, home_score, away_score, graded_at"
      )
      .in("grade", ["WIN", "LOSS"])
      .order("graded_at", { ascending: false }),
  ]);

  const MARKET_ORDER = ["overall", "goals", "btts", "winner"];

  const summary: MarketStats[] = ((summaryRes.data ?? []) as PickResultsRow[])
    .sort(
      (a, b) => MARKET_ORDER.indexOf(a.market) - MARKET_ORDER.indexOf(b.market)
    )
    .map((r) => ({
      market: r.market,
      totalPicks: r.total_picks,
      wins: r.wins,
      losses: r.losses,
      voids: r.voids,
      winRate: toNumber(r.win_rate),
      totalUnits: toNumber(r.total_units),
      roiPercent: toNumber(r.roi_percent),
    }));

  const picks: GradedPick[] = ((picksRes.data ?? []) as GradedPickRow[]).map(
    (r) => ({
      gameId: r.game_id,
      homeTeam: r.home_team_name,
      awayTeam: r.away_team_name,
      pick: r.pick,
      market: r.market,
      grade: r.grade as GradedPick["grade"],
      oddsDecimal: toNumber(r.odds_decimal),
      noOdds: Boolean(r.no_odds),
      unitsResult: toNumber(r.units_result),
      homeScore: r.home_score,
      awayScore: r.away_score,
      gradedAt: r.graded_at,
    })
  );

  return { summary, picks };
}

// ─── MLB ────────────────────────────────────────────────────────────────────

const MLB_SPORT_KEY = "baseball_mlb";

type MLBFinalPredictionRow = {
  game_id: string;
  home_team_name: string;
  away_team_name: string;
  best_pick: string;
  market: string;
  bookmaker: string | null;
  odds_decimal: number | string | null;
  odds_american: number | null;
  calibrated_confidence: number | string | null;
  model_edge: number | string | null;
  edge_flag: string | null;
  secondary_pick: string | null;
  secondary_market: string | null;
  confidence_tier: string | null;
};

type MLBSafeZoneRow = {
  game_id: string;
  home_team_name: string;
  away_team_name: string;
  sharp_pick: string | null;
  sharp_market: string | null;
  balanced_pick: string | null;
  balanced_prob: number | string | null;
  banker_pick: string | null;
  banker_prob: number | string | null;
};

type MLBBacktestRow = {
  market: string;
  total_predictions: number;
  correct: number;
  incorrect: number;
  accuracy: number | string | null;
  avg_odds_decimal: number | string | null;
  roi: number | string | null;
};

async function fetchMLBGamesById(gameIds: string[]): Promise<Map<string, GameRow>> {
  const map = new Map<string, GameRow>();
  if (gameIds.length === 0) return map;
  const { data, error } = await supabase
    .from("games")
    .select("id, game_date, start_time_toronto, status")
    .in("id", gameIds)
    .eq("sport_key", MLB_SPORT_KEY);
  if (error) throw error;
  for (const row of data ?? []) map.set(row.id, row as GameRow);
  return map;
}

export async function getMLBSharpPicks(): Promise<MLBSharpPick[]> {
  const { data: rows, error } = await supabase
    .from("mlb_final_predictions")
    .select(
      "game_id, home_team_name, away_team_name, best_pick, market, bookmaker, odds_decimal, odds_american, calibrated_confidence, model_edge, edge_flag, secondary_pick, secondary_market, confidence_tier"
    );
  if (error) throw error;
  if (!rows || rows.length === 0) return [];

  const gameIds = [...new Set(rows.map((r) => r.game_id))];
  const today = todayTorontoISODate();

  const { data: games, error: gamesError } = await supabase
    .from("games")
    .select("id, game_date, start_time_toronto, status")
    .in("id", gameIds)
    .eq("sport_key", MLB_SPORT_KEY)
    .gte("game_date", today);
  if (gamesError) throw gamesError;

  const gamesById = new Map<string, GameRow>();
  for (const g of games ?? []) gamesById.set(g.id, g as GameRow);

  return (rows as MLBFinalPredictionRow[])
    .filter((r) => gamesById.has(r.game_id))
    .map((r) => {
      const edge = toNumber(r.model_edge);
      const isRealValue =
        r.edge_flag === "REAL" && edge !== null && edge > 0 && edge <= 15;
      const game = gamesById.get(r.game_id);
      return {
        gameId: r.game_id,
        homeTeam: r.home_team_name,
        awayTeam: r.away_team_name,
        pick: r.best_pick,
        market: r.market,
        bookmaker: r.bookmaker,
        oddsDecimal: toNumber(r.odds_decimal),
        oddsAmerican: r.odds_american,
        calibratedConfidence: toNumber(r.calibrated_confidence),
        edge,
        isRealValue,
        secondaryPick: r.secondary_pick,
        secondaryMarket: r.secondary_market,
        gameTime: game?.start_time_toronto ?? null,
        confidenceTier: r.confidence_tier,
      };
    });
}

export async function getMLBSafeZone(): Promise<MLBSafeZonePick[]> {
  const { data: rows, error } = await supabase
    .from("mlb_safe_zone")
    .select(
      "game_id, home_team_name, away_team_name, sharp_pick, sharp_market, balanced_pick, balanced_prob, banker_pick, banker_prob"
    );
  if (error) throw error;
  if (!rows || rows.length === 0) return [];

  const gameIds = [...new Set(rows.map((r) => r.game_id))];
  const today = todayTorontoISODate();

  const { data: games, error: gamesError } = await supabase
    .from("games")
    .select("id, game_date, start_time_toronto, status")
    .in("id", gameIds)
    .eq("sport_key", MLB_SPORT_KEY)
    .gte("game_date", today);
  if (gamesError) throw gamesError;

  const gamesById = new Map<string, GameRow>();
  for (const g of games ?? []) gamesById.set(g.id, g as GameRow);

  const picks: MLBSafeZonePick[] = (rows as MLBSafeZoneRow[])
    .filter((r) => gamesById.has(r.game_id))
    .map((r) => {
      const game = gamesById.get(r.game_id)!;
      return {
        gameId: r.game_id,
        homeTeam: r.home_team_name,
        awayTeam: r.away_team_name,
        sharpPick: r.sharp_pick,
        sharpMarket: r.sharp_market,
        balancedPick: r.balanced_pick,
        balancedProb: toNumber(r.balanced_prob),
        bankerPick: r.banker_pick,
        bankerProb: toNumber(r.banker_prob),
        gameTime: game.start_time_toronto,
      };
    });

  picks.sort((a, b) => {
    if (a.gameTime && b.gameTime) return a.gameTime.localeCompare(b.gameTime);
    if (a.gameTime) return -1;
    if (b.gameTime) return 1;
    return 0;
  });

  return picks;
}

export async function getMLBTrackRecord(): Promise<MLBTrackRecord> {
  const { data: rows, error } = await supabase
    .from("mlb_backtest_results")
    .select("market, total_predictions, correct, incorrect, accuracy, avg_odds_decimal, roi")
    .order("market");
  if (error) throw error;

  const aggregated = new Map<
    string,
    { totalPredictions: number; correct: number; incorrect: number; roiSum: number; roiCount: number; oddsSum: number; oddsCount: number }
  >();

  for (const r of (rows ?? []) as MLBBacktestRow[]) {
    const existing = aggregated.get(r.market) ?? {
      totalPredictions: 0,
      correct: 0,
      incorrect: 0,
      roiSum: 0,
      roiCount: 0,
      oddsSum: 0,
      oddsCount: 0,
    };
    existing.totalPredictions += r.total_predictions ?? 0;
    existing.correct += r.correct ?? 0;
    existing.incorrect += r.incorrect ?? 0;
    const roi = toNumber(r.roi);
    if (roi !== null) { existing.roiSum += roi; existing.roiCount++; }
    const odds = toNumber(r.avg_odds_decimal);
    if (odds !== null) { existing.oddsSum += odds; existing.oddsCount++; }
    aggregated.set(r.market, existing);
  }

  const MLB_MARKET_ORDER = ["moneyline", "totals", "run_line"];
  const byMarket: MLBMarketStats[] = [...aggregated.entries()]
    .sort(([a], [b]) => MLB_MARKET_ORDER.indexOf(a) - MLB_MARKET_ORDER.indexOf(b))
    .map(([market, agg]) => ({
      market,
      totalPredictions: agg.totalPredictions,
      correct: agg.correct,
      incorrect: agg.incorrect,
      accuracy: agg.totalPredictions > 0 ? (agg.correct / agg.totalPredictions) * 100 : null,
      avgOddsDecimal: agg.oddsCount > 0 ? agg.oddsSum / agg.oddsCount : null,
      roi: agg.roiCount > 0 ? agg.roiSum / agg.roiCount : null,
    }));

  const totalPredictions = byMarket.reduce((s, r) => s + r.totalPredictions, 0);
  const totalCorrect = byMarket.reduce((s, r) => s + r.correct, 0);
  const overallAccuracy = totalPredictions > 0 ? (totalCorrect / totalPredictions) * 100 : null;
  const roiEntries = byMarket.filter((r) => r.roi !== null);
  const overallRoi = roiEntries.length > 0
    ? roiEntries.reduce((s, r) => s + r.roi!, 0) / roiEntries.length
    : null;

  return { byMarket, totalPredictions, totalCorrect, overallAccuracy, overallRoi };
}

// ─── MLB Player Props ────────────────────────────────────────────────────────

type MLBPlayerPropRow = {
  game_id: string;
  player_name: string;
  player_type: string;
  player_mlb_id: number | null;
  team_name: string | null;
  side: string | null;
  prop_market: string;
  model_projection: number | string | null;
  market_line: number | string | null;
  pick_side: string | null;
  calibrated_over_prob: number | string | null;
  best_odds_decimal: number | string | null;
  best_odds_american: number | null;
  model_edge: number | string | null;
  edge_flag: string | null;
  confidence_note: string | null;
  confidence_tier: string | null;
};

type MLBGameWithTeams = GameRow & { home_team_name: string; away_team_name: string };

async function fetchMLBGamesWithTeams(gameIds: string[]): Promise<Map<string, MLBGameWithTeams>> {
  const map = new Map<string, MLBGameWithTeams>();
  if (gameIds.length === 0) return map;
  const { data, error } = await supabase
    .from("games")
    .select("id, game_date, start_time_toronto, status, home_team_name, away_team_name")
    .in("id", gameIds)
    .eq("sport_key", MLB_SPORT_KEY);
  if (error) throw error;
  for (const row of data ?? []) map.set(row.id, row as MLBGameWithTeams);
  return map;
}

// ─── MLB Model Lab ───────────────────────────────────────────────────────────

type MLBRunPredictionRow = {
  game_id: string;
  model_version: string;
  home_team_name: string;
  away_team_name: string;
  expected_home_runs: number | string | null;
  expected_away_runs: number | string | null;
  expected_total_runs: number | string | null;
  home_win_probability: number | string | null;
  away_win_probability: number | string | null;
  over_85_probability: number | string | null;
  under_85_probability: number | string | null;
};

type MLBModelPickRow = {
  game_id: string;
  model_version: string;
  home_team_name: string | null;
  away_team_name: string | null;
  best_pick: string | null;
  market: string | null;
  calibrated_confidence: number | string | null;
  balanced_pick: string | null;
  balanced_prob: number | string | null;
};

function emptyModelVersion(version: string): MLBModelVersionData {
  return {
    version,
    expectedHomeRuns: null,
    expectedAwayRuns: null,
    expectedTotalRuns: null,
    homeWinProb: null,
    awayWinProb: null,
    over85Prob: null,
    under85Prob: null,
    bestPick: null,
    market: null,
    calibratedConfidence: null,
    balancedPick: null,
    balancedProb: null,
  };
}

export async function getMLBModelLab(): Promise<MLBModelLabGame[]> {
  const today = todayTorontoISODate();

  const { data: games, error: gamesError } = await supabase
    .from("games")
    .select("id, game_date, start_time_toronto, status")
    .eq("sport_key", MLB_SPORT_KEY)
    .gte("game_date", today);
  if (gamesError) throw gamesError;
  if (!games || games.length === 0) return [];

  const gameIds = games.map((g) => g.id);
  const gamesById = new Map(games.map((g) => [g.id, g as GameRow]));

  const [{ data: runRows, error: runError }, { data: pickRows, error: pickError }] =
    await Promise.all([
      supabase
        .from("mlb_run_predictions")
        .select(
          "game_id, model_version, home_team_name, away_team_name, expected_home_runs, expected_away_runs, expected_total_runs, home_win_probability, away_win_probability, over_85_probability, under_85_probability"
        )
        .in("game_id", gameIds),
      supabase
        .from("mlb_model_picks")
        .select(
          "game_id, model_version, home_team_name, away_team_name, best_pick, market, calibrated_confidence, balanced_pick, balanced_prob"
        )
        .in("game_id", gameIds),
    ]);
  if (runError) throw runError;
  if (pickError) throw pickError;

  // Build combined model data per (game_id, model_version)
  type GameEntry = { models: Record<string, MLBModelVersionData>; homeTeam: string; awayTeam: string };
  const byGame = new Map<string, GameEntry>();

  for (const row of (runRows ?? []) as MLBRunPredictionRow[]) {
    if (!byGame.has(row.game_id)) {
      byGame.set(row.game_id, { models: {}, homeTeam: row.home_team_name, awayTeam: row.away_team_name });
    }
    const entry = byGame.get(row.game_id)!;
    entry.models[row.model_version] = {
      ...emptyModelVersion(row.model_version),
      expectedHomeRuns: toNumber(row.expected_home_runs),
      expectedAwayRuns: toNumber(row.expected_away_runs),
      expectedTotalRuns: toNumber(row.expected_total_runs),
      homeWinProb: toNumber(row.home_win_probability),
      awayWinProb: toNumber(row.away_win_probability),
      over85Prob: toNumber(row.over_85_probability),
      under85Prob: toNumber(row.under_85_probability),
    };
  }

  for (const row of (pickRows ?? []) as MLBModelPickRow[]) {
    if (!byGame.has(row.game_id)) {
      byGame.set(row.game_id, {
        models: {},
        homeTeam: row.home_team_name ?? "",
        awayTeam: row.away_team_name ?? "",
      });
    }
    const entry = byGame.get(row.game_id)!;
    const existing = entry.models[row.model_version] ?? emptyModelVersion(row.model_version);
    existing.bestPick = row.best_pick;
    existing.market = row.market;
    existing.calibratedConfidence = toNumber(row.calibrated_confidence);
    existing.balancedPick = row.balanced_pick;
    existing.balancedProb = toNumber(row.balanced_prob);
    entry.models[row.model_version] = existing;
  }

  if (byGame.size === 0) return [];

  const result: MLBModelLabGame[] = [];

  for (const [gameId, { models, homeTeam, awayTeam }] of byGame.entries()) {
    const game = gamesById.get(gameId);
    if (!game) continue;

    const v2 = models["poisson_v2"];
    const v2Total = v2?.expectedTotalRuns ?? null;
    const v2Lean = v2?.over85Prob != null ? (v2.over85Prob > 50 ? "Over" : "Under") : null;

    let hasDisagreement = false;
    if (v2) {
      for (const [ver, m] of Object.entries(models)) {
        if (ver === "poisson_v2") continue;
        const mLean = m.over85Prob != null ? (m.over85Prob > 50 ? "Over" : "Under") : null;
        const diff =
          v2Total != null && m.expectedTotalRuns != null
            ? Math.abs(m.expectedTotalRuns - v2Total)
            : null;
        if (mLean !== null && v2Lean !== null && mLean !== v2Lean) { hasDisagreement = true; break; }
        if (diff !== null && diff > 0.5) { hasDisagreement = true; break; }
        // Pick-level divergence: same market, different side
        if (v2.bestPick && m.bestPick && v2.market && m.market === v2.market && m.bestPick !== v2.bestPick) {
          hasDisagreement = true; break;
        }
      }
    }

    result.push({ gameId, homeTeam, awayTeam, gameTime: game.start_time_toronto ?? null, models, hasDisagreement });
  }

  result.sort((a, b) => (a.gameTime ?? "").localeCompare(b.gameTime ?? ""));
  return result;
}

type MLBModelAnalyticsRow = {
  model_version: string;
  games_graded: number | null;
  mae_total_xr: number | string | null;
  brier_score: number | string | null;
  direction_accuracy: number | string | null;
  win_rate: number | string | null;
  roi_percent: number | string | null;
  avg_clv: number | string | null;
};

export async function getMLBModelAnalytics(): Promise<MLBModelAnalytics[]> {
  const { data, error } = await supabase
    .from("mlb_model_analytics")
    .select(
      "model_version, games_graded, mae_total_xr, brier_score, direction_accuracy, win_rate, roi_percent, avg_clv"
    );
  if (error) throw error;
  return ((data ?? []) as MLBModelAnalyticsRow[]).map((r) => ({
    modelVersion: r.model_version,
    gamesGraded: r.games_graded ?? 0,
    mae: toNumber(r.mae_total_xr),
    brierScore: toNumber(r.brier_score),
    directionAccuracy: toNumber(r.direction_accuracy),
    winRate: toNumber(r.win_rate),
    roiPercent: toNumber(r.roi_percent),
    avgClv: toNumber(r.avg_clv),
  }));
}

export async function getMLBPlayerProps(): Promise<MLBPlayerProp[]> {
  const today = todayTorontoISODate();

  const { data: rows, error } = await supabase
    .from("mlb_player_props")
    .select(
      "game_id, player_name, player_type, player_mlb_id, team_name, side, prop_market, model_projection, market_line, pick_side, calibrated_over_prob, best_odds_decimal, best_odds_american, model_edge, edge_flag, confidence_note, confidence_tier"
    )
    .gte("game_date", today)
    .order("confidence_tier", { ascending: true });

  if (error) throw error;
  if (!rows || rows.length === 0) return [];

  const gameIds = [...new Set(rows.map((r) => r.game_id))];
  const gamesById = await fetchMLBGamesWithTeams(gameIds);

  return (rows as MLBPlayerPropRow[])
    .filter((r) => gamesById.has(r.game_id))
    .map((r) => {
      const game = gamesById.get(r.game_id)!;
      return {
      gameId: r.game_id,
      homeTeam: game.home_team_name,
      awayTeam: game.away_team_name,
      playerName: r.player_name,
      playerType: r.player_type as "pitcher" | "batter",
      playerMlbId: r.player_mlb_id ?? null,
      teamName: r.team_name,
      side: r.side,
      propMarket: r.prop_market,
      modelProjection: toNumber(r.model_projection),
      marketLine: toNumber(r.market_line),
      pickSide: r.pick_side as "Over" | "Under" | null,
      calibratedOverProb: toNumber(r.calibrated_over_prob),
      bestOddsDecimal: toNumber(r.best_odds_decimal),
      bestOddsAmerican: r.best_odds_american,
      modelEdge: toNumber(r.model_edge),
      edgeFlag: r.edge_flag,
      confidenceNote: r.confidence_note,
      confidenceTier: r.confidence_tier,
      gameTime: game.start_time_toronto ?? null,
      };
    })
    .sort((a, b) => {
      if (!a.gameTime && !b.gameTime) return 0;
      if (!a.gameTime) return 1;
      if (!b.gameTime) return -1;
      return a.gameTime < b.gameTime ? -1 : a.gameTime > b.gameTime ? 1 : 0;
    });
}

// ---------------------------------------------------------------------------
// MLB Diagnostics — per-pick detail + prop detail for model analysis
// Returns empty arrays gracefully if tables don't exist yet (SQL 086 not run).
// ---------------------------------------------------------------------------
export async function getMLBDiagnostics(): Promise<MLBDiagnostics> {
  const [picksRes, propsRes] = await Promise.all([
    supabase
      .from("mlb_pick_detail")
      .select("*")
      .order("game_date", { ascending: false }),
    supabase
      .from("mlb_prop_detail")
      .select("*")
      .order("game_date", { ascending: false }),
  ]);

  const picks: MLBPickDetail[] = picksRes.error
    ? []
    : (picksRes.data ?? []).map((r) => ({
        gameId: r.game_id,
        gameDate: r.game_date ?? null,
        homeTeam: r.home_team ?? "",
        awayTeam: r.away_team ?? "",
        market: r.market ?? "",
        pick: r.pick ?? "",
        pickLine: toNumber(r.pick_line),
        pickSide: r.pick_side ?? null,
        isHomePick: r.is_home_pick ?? null,
        isOver: r.is_over ?? null,
        isFavorite: r.is_favorite ?? null,
        modelProjTotal: toNumber(r.model_proj_total),
        modelProjHome: toNumber(r.model_proj_home),
        modelProjAway: toNumber(r.model_proj_away),
        calibratedConf: toNumber(r.calibrated_conf),
        rawConfidence: toNumber(r.raw_confidence),
        modelEdge: toNumber(r.model_edge),
        edgeBucket: r.edge_bucket ?? null,
        confBucket: r.conf_bucket ?? null,
        oddsDecimal: toNumber(r.odds_decimal),
        edgeFlag: r.edge_flag ?? null,
        noOdds: r.no_odds ?? false,
        homeScore: r.home_score ?? null,
        awayScore: r.away_score ?? null,
        actualTotal: r.actual_total ?? null,
        actualDiff: r.actual_diff ?? null,
        totalBias: toNumber(r.total_bias),
        grade: r.grade ?? null,
        unitsResult: toNumber(r.units_result),
        roiPercent: toNumber(r.roi_percent),
        clv: toNumber(r.clv),
        beatClose: r.beat_close ?? null,
        gradedAt: r.graded_at ?? null,
      }));

  const props: MLBPropDetail[] = propsRes.error
    ? []
    : (propsRes.data ?? []).map((r) => ({
        gameId: r.game_id,
        gameDate: r.game_date ?? null,
        playerName: r.player_name ?? null,
        playerMlbId: r.player_mlb_id ?? null,
        playerType: r.player_type ?? null,
        propMarket: r.prop_market ?? "",
        marketLine: toNumber(r.market_line),
        pickSide: r.pick_side ?? null,
        modelProjection: toNumber(r.model_projection),
        calibratedProb: toNumber(r.calibrated_prob),
        modelEdge: toNumber(r.model_edge),
        bestOddsDecimal: toNumber(r.best_odds_decimal),
        edgeFlag: r.edge_flag ?? null,
        actualValue: toNumber(r.actual_value),
        propBias: toNumber(r.prop_bias),
        grade: r.grade ?? null,
        unitsResult: toNumber(r.units_result),
        gradedAt: r.graded_at ?? null,
      }));

  return { picks, props };
}

// ---------------------------------------------------------------------------
// Subscriber track-record aggregates (from mlb_subscriber_results).
// Returns gracefully if the table doesn't exist yet (SQL 089 not run).
// ---------------------------------------------------------------------------
type SubscriberResultRow = {
  segment: string;
  pick_count: number | null;
  win_count: number | null;
  loss_count: number | null;
  win_rate: number | null;
  units_profit: number | null;
  roi_percent: number | null;
  avg_edge: number | null;
  avg_win_prob: number | null;
  avg_clv: number | null;
  clv_beat_rate: number | null;
};

function rowToSegment(r: SubscriberResultRow): MLBSubscriberSegment {
  return {
    pickCount:   r.pick_count   ?? 0,
    winCount:    r.win_count    ?? 0,
    lossCount:   r.loss_count   ?? 0,
    winRate:     toNumber(r.win_rate),
    unitsProfit: toNumber(r.units_profit),
    roiPercent:  toNumber(r.roi_percent),
    avgEdge:     toNumber(r.avg_edge),
    avgWinProb:  toNumber(r.avg_win_prob),
    avgClv:         toNumber(r.avg_clv),
    clvBeatRate:    toNumber(r.clv_beat_rate),
    clvSampleCount: 0, // mlb_subscriber_results has no clv_sample_count column; field unused (deprecated path)
  };
}

/** @deprecated mlb_subscriber_results is never read by the frontend (computeSegment runs client-side). Step 12 removed from run_mlb_engine.py. Delete this if mlb_subscriber_results is never wired up. */
export async function getMLBSubscriberResults(): Promise<MLBSubscriberResults> {
  const { data, error } = await supabase
    .from("mlb_subscriber_results")
    .select(
      "segment, pick_count, win_count, loss_count, win_rate, units_profit, "
      + "roi_percent, avg_edge, avg_win_prob, avg_clv, clv_beat_rate"
    );

  if (error || !data) return { all: null, betOfDay: null };

  let all: MLBSubscriberSegment | null = null;
  let betOfDay: MLBSubscriberSegment | null = null;

  for (const r of data as unknown as SubscriberResultRow[]) {
    if (r.segment === "all")        all      = rowToSegment(r);
    if (r.segment === "bet_of_day") betOfDay = rowToSegment(r);
  }

  return { all, betOfDay };
}

// ---------------------------------------------------------------------------
// Live game state (from mlb_live_state, written hourly by sync_mlb_live_state).
// Display-only: never used to set or modify grades.
// ---------------------------------------------------------------------------
type MLBLiveStateRow = {
  game_id: string;
  home_score: number | null;
  away_score: number | null;
  inning: number | null;
  inning_half: string | null;
  outs: number | null;
  game_status: string | null;
  home_pitcher: string | null;
  away_pitcher: string | null;
  captured_at: string | null;
};

export async function getMLBLiveState(): Promise<Map<string, MLBLiveState>> {
  const { data, error } = await supabase
    .from("mlb_live_state")
    .select(
      "game_id, home_score, away_score, inning, inning_half, outs, "
      + "game_status, home_pitcher, away_pitcher, captured_at"
    );

  const map = new Map<string, MLBLiveState>();
  if (error || !data) return map;

  for (const r of data as unknown as MLBLiveStateRow[]) {
    map.set(r.game_id, {
      gameId:      r.game_id,
      homeScore:   r.home_score ?? null,
      awayScore:   r.away_score ?? null,
      inning:      r.inning ?? null,
      inningHalf:  r.inning_half ?? null,
      outs:        r.outs ?? null,
      gameStatus:  r.game_status ?? null,
      homePitcher: r.home_pitcher ?? null,
      awayPitcher: r.away_pitcher ?? null,
      capturedAt:  r.captured_at ?? null,
    });
  }
  return map;
}

/**
 * Compute a non-binding live pick status from current score.
 * Display-only — never written to any grades table.
 *
 * Returns null when the game is not live or the pick type can't be assessed.
 */
export function computeLivePickStatus(
  market: string,
  pick: string,
  homeTeam: string,
  awayTeam: string,
  live: MLBLiveState,
): MLBLivePickStatus {
  const status = (live.gameStatus ?? "").toLowerCase();
  if (!status.includes("live") && !status.includes("in progress")) return null;

  const homeScore = live.homeScore ?? 0;
  const awayScore = live.awayScore ?? 0;
  const total = homeScore + awayScore;
  const m = market.toLowerCase();
  const p = pick.toLowerCase().trim();

  if (m === "moneyline" || m === "safe_balanced" || m === "safe_banker") {
    const homeNorm = homeTeam.toLowerCase().trim();
    const awayNorm = awayTeam.toLowerCase().trim();
    const pickNorm = p;

    // Determine if the pick is for the home or away team.
    const isHome = homeNorm.includes(pickNorm) || pickNorm.includes(homeNorm.split(" ").at(-1) ?? "");
    const isAway = awayNorm.includes(pickNorm) || pickNorm.includes(awayNorm.split(" ").at(-1) ?? "");

    if (!isHome && !isAway) return null;
    const pickScore  = isHome ? homeScore : awayScore;
    const otherScore = isHome ? awayScore : homeScore;
    if (pickScore > otherScore)  return "currently_winning";
    if (pickScore < otherScore)  return "currently_losing";
    return "too_close";
  }

  if (m === "totals") {
    const mat = p.match(/^(over|under)\s+([\d.]+)$/);
    if (!mat) return null;
    const direction = mat[1];
    const line = parseFloat(mat[2]);
    if (direction === "over")  return total > line ? "currently_winning" : total === line ? "too_close" : "currently_losing";
    if (direction === "under") return total < line ? "currently_winning" : total === line ? "too_close" : "currently_losing";
    return null;
  }

  if (m === "run_line") {
    // e.g. "New York Yankees -1.5" — the pick team must cover the spread.
    const spreadMat = p.match(/^(.+?)\s+([-+][\d.]+)$/);
    if (!spreadMat) return null;
    const pickTeamPart = spreadMat[1].trim();
    const spread = parseFloat(spreadMat[2]);

    const homeNorm = homeTeam.toLowerCase();
    const isHome = homeNorm.includes(pickTeamPart) || pickTeamPart.includes(homeNorm.split(" ").at(-1) ?? "");
    const diff = isHome ? homeScore - awayScore : awayScore - homeScore;
    const covers = diff + spread;
    if (covers > 0)  return "currently_winning";
    if (covers < 0)  return "currently_losing";
    return "too_close";
  }

  return null;
}
