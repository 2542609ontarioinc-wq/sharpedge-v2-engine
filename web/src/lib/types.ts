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
