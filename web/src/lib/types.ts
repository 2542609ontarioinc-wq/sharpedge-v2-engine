export type MarketStats = {
  market: string;
  totalPicks: number;
  wins: number;
  losses: number;
  voids: number;
  winRate: number | null;
  totalUnits: number | null;
  roiPercent: number | null;
};

export type GradedPick = {
  gameId: string;
  homeTeam: string;
  awayTeam: string;
  pick: string;
  market: string;
  grade: "WIN" | "LOSS" | "VOID";
  oddsDecimal: number | null;
  noOdds: boolean;
  unitsResult: number | null;
  homeScore: number | null;
  awayScore: number | null;
  gradedAt: string | null;
};

export type TrackRecord = {
  summary: MarketStats[];
  picks: GradedPick[];
};

export type SharpPick = {
  gameId: string;
  homeTeam: string;
  awayTeam: string;
  pick: string;
  market: string;
  bookmaker: string | null;
  tier: string | null;
  confidenceTier: string | null;
  finalValueRating: number | null;
  safetyScore: number | null;
  matchupScore: number | null;
  explanation: string | null;
  confidence: number | null;
  edge: number | null;
  isRealValue: boolean;
  kickoff: string | null;
};

export type SafeZonePick = {
  gameId: string;
  homeTeam: string;
  awayTeam: string;
  balancedPick: string | null;
  balancedProb: number | null;
  bankerPick: string | null;
  bankerProb: number | null;
  kickoff: string | null;
};

export type MLBSharpPick = {
  gameId: string;
  homeTeam: string;
  awayTeam: string;
  pick: string;
  market: string;
  bookmaker: string | null;
  oddsDecimal: number | null;
  oddsAmerican: number | null;
  calibratedConfidence: number | null;
  edge: number | null;
  isRealValue: boolean;
  secondaryPick: string | null;
  secondaryMarket: string | null;
  gameTime: string | null;
  confidenceTier: string | null;
};

export type MLBSafeZonePick = {
  gameId: string;
  homeTeam: string;
  awayTeam: string;
  sharpPick: string | null;
  sharpMarket: string | null;
  balancedPick: string | null;
  balancedProb: number | null;
  bankerPick: string | null;
  bankerProb: number | null;
  gameTime: string | null;
};

export type MLBMarketStats = {
  market: string;
  totalPredictions: number;
  correct: number;
  incorrect: number;
  accuracy: number | null;
  avgOddsDecimal: number | null;
  roi: number | null;
};

export type MLBTrackRecord = {
  byMarket: MLBMarketStats[];
  totalPredictions: number;
  totalCorrect: number;
  overallAccuracy: number | null;
  overallRoi: number | null;
};

export type MLBPlayerProp = {
  gameId: string;
  homeTeam: string;
  awayTeam: string;
  playerName: string;
  playerType: "pitcher" | "batter";
  playerMlbId: number | null;
  teamName: string | null;
  side: string | null;
  propMarket: string;
  modelProjection: number | null;
  marketLine: number | null;
  pickSide: "Over" | "Under" | null;
  calibratedOverProb: number | null;
  bestOddsDecimal: number | null;
  bestOddsAmerican: number | null;
  modelEdge: number | null;
  edgeFlag: string | null;
  confidenceNote: string | null;
  confidenceTier: string | null;
  gameTime: string | null;
};

export type MLBModelVersionData = {
  version: string;
  expectedHomeRuns: number | null;
  expectedAwayRuns: number | null;
  expectedTotalRuns: number | null;
  homeWinProb: number | null;
  awayWinProb: number | null;
  over85Prob: number | null;
  under85Prob: number | null;
  // From mlb_model_picks — null if that table has no row for this game+model
  bestPick: string | null;
  market: string | null;
  calibratedConfidence: number | null;
  balancedPick: string | null;
  balancedProb: number | null;
};

export type MLBModelLabGame = {
  gameId: string;
  homeTeam: string;
  awayTeam: string;
  gameTime: string | null;
  models: Record<string, MLBModelVersionData>;
  hasDisagreement: boolean;
};

export type MLBModelAnalytics = {
  modelVersion: string;
  gamesGraded: number;
  // win_rate stored as fraction (0–1); direction_accuracy same
  // roi_percent stored as actual % (e.g. 5.2 for 5.2%); mae in run units
  mae: number | null;
  brierScore: number | null;
  directionAccuracy: number | null;
  winRate: number | null;
  roiPercent: number | null;
  avgClv: number | null;
};

// Enriched per-pick diagnostic row (from mlb_pick_detail).
export type MLBPickDetail = {
  gameId: string;
  gameDate: string | null;
  homeTeam: string;
  awayTeam: string;
  market: string;
  pick: string;
  pickLine: number | null;
  pickSide: string | null;
  isHomePick: boolean | null;
  isOver: boolean | null;
  isFavorite: boolean | null;
  modelProjTotal: number | null;
  modelProjHome: number | null;
  modelProjAway: number | null;
  calibratedConf: number | null;  // percentage, 50–100 scale
  rawConfidence: number | null;
  modelEdge: number | null;
  edgeBucket: string | null;       // '<2%', '2-5%', '5%+'
  confBucket: string | null;       // '<55%', '55-65%', '65-75%', '75%+'
  oddsDecimal: number | null;
  edgeFlag: string | null;
  noOdds: boolean;
  homeScore: number | null;
  awayScore: number | null;
  actualTotal: number | null;
  actualDiff: number | null;
  totalBias: number | null;        // model_proj_total - actual_total; positive = ran too high
  grade: "WIN" | "LOSS" | "VOID" | null;
  unitsResult: number | null;
  roiPercent: number | null;
  clv: number | null;
  beatClose: boolean | null;
  gradedAt: string | null;
};

// Enriched per-prop diagnostic row (from mlb_prop_detail).
export type MLBPropDetail = {
  gameId: string;
  gameDate: string | null;
  playerName: string | null;
  playerMlbId: number | null;
  playerType: "pitcher" | "batter" | null;
  propMarket: string;
  marketLine: number | null;
  pickSide: "Over" | "Under" | null;
  modelProjection: number | null;
  calibratedProb: number | null;
  modelEdge: number | null;
  bestOddsDecimal: number | null;
  edgeFlag: string | null;
  actualValue: number | null;
  propBias: number | null;         // model_projection - actual_value; positive = projected too high
  grade: "WIN" | "LOSS" | "VOID" | null;
  unitsResult: number | null;
  gradedAt: string | null;
};

export type MLBDiagnostics = {
  picks: MLBPickDetail[];
  props: MLBPropDetail[];
};

export type MLBSubscriberSegment = {
  pickCount: number;
  winCount: number;
  lossCount: number;
  winRate: number | null;    // fraction 0–1
  unitsProfit: number | null;
  roiPercent: number | null;
  avgEdge: number | null;    // mean model edge %
  avgWinProb: number | null; // mean win-probability % at pick time
  avgClv: number | null;
  clvBeatRate: number | null; // fraction 0–1
};

export type MLBSubscriberResults = {
  all: MLBSubscriberSegment | null;
  betOfDay: MLBSubscriberSegment | null;
};

// Live linescore state for a single game (from mlb_live_state, display-only).
export type MLBLiveState = {
  gameId: string;
  homeScore: number | null;
  awayScore: number | null;
  inning: number | null;
  inningHalf: string | null;  // 'Top' | 'Bottom'
  outs: number | null;
  gameStatus: string | null;  // 'Live' | 'Final' | 'Preview' | 'Postponed' | etc.
  homePitcher: string | null;
  awayPitcher: string | null;
  capturedAt: string | null;
};

// Transient per-pick live status — never persisted to grades.
export type MLBLivePickStatus = "currently_winning" | "currently_losing" | "too_close" | null;
