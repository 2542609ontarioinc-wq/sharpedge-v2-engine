"""
Subscriber-tab qualification thresholds — single source of truth.

The web frontend (MLBSubscriberView.tsx) mirrors these constants exactly.
When changing any value here, update the matching constants in that file too.
"""

EDGE_MIN  = 3.0   # minimum model edge % (picks with an edge signal must clear this)
PROB_MIN  = 65.0  # minimum win-probability % for all pick types
BOTD_EDGE = 5.0   # Bet of the Day: edge must be >= this
BOTD_PROB = 70.0  # Bet of the Day: win prob must be >= this
EDGE_MAX  = 15.0  # upper sanity cap (mirrors isRealValue check in the frontend)
