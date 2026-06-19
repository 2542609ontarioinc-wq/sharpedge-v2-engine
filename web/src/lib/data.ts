import { supabase } from "./supabase";
import type {
  GradedPick,
  MarketStats,
  MLBMarketStats,
  MLBPlayerProp,
  MLBSafeZonePick,
  MLBSharpPick,
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

  const [{ data: predictions, error: predError }, gamesById] = await Promise.all([
    supabase
      .from("final_soccer_predictions")
      .select("game_id, market, best_pick, confidence, bookmaker, odds_decimal, model_edge")
      .in("game_id", gameIds)
      .order("created_at", { ascending: false }),
    fetchGamesById(gameIds),
  ]);

  if (predError) throw predError;

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

  return (proPicks as FinalProSoccerPick[]).map((pro) => {
    const match = matchPrediction(pro);
    const edge = match ? toNumber(match.model_edge) : null;
    const hasOdds = Boolean(match?.bookmaker && match?.odds_decimal != null && edge !== null);
    const isRealValue = hasOdds && edge !== null && edge > 0 && edge <= 15;

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

export async function getMLBPlayerProps(): Promise<MLBPlayerProp[]> {
  const today = todayTorontoISODate();

  const { data: rows, error } = await supabase
    .from("mlb_player_props")
    .select(
      "game_id, player_name, player_type, team_name, side, prop_market, model_projection, market_line, pick_side, calibrated_over_prob, best_odds_decimal, best_odds_american, model_edge, edge_flag, confidence_note, confidence_tier"
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
    });
}
