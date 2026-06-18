# SharpEdge V2 — Feature Architecture

## Core Rule

SharpEdge V2 is not a random picks app.

SharpEdge V2 is a probability engine.

The system must first predict outcomes from data, then only generate picks when the prediction is strong enough.

Flow:

Data
→ Clean storage
→ Feature store
→ Prediction models
→ Pick candidates
→ Final picks
→ Parlays
→ Live grading
→ Analytics

---

# 1. Current Data Source Setup

## Available API Keys

| Source | Status | Purpose |
|---|---|---|
| SportsDataIO | Trial | MLB schedule, teams, players, injuries, boxscores, stadiums, lineups if available |
| Odds API | Paid | Moneyline, spreads, totals, player props, odds movement |
| API-Sports | Soccer + MLB | Soccer fixtures, lineups, stats, events, standings, referees, MLB basic games/stats |
| pybaseball / Baseball Savant | Free Python source | MLB Statcast, xBA, xSLG, xwOBA, exit velocity, barrel %, hard-hit % |

---

# 2. Sport Priority

## Soccer Priority

Primary target:

All Soccer, with FIFA / International priority first.

Priority order:

1. FIFA / International matches
2. World Cup / international tournaments
3. Champions League
4. EPL
5. MLS
6. Other major leagues

Reason:

The engine must handle national team matches, tournament-style games, cards, corners, goals, and high-probability result predictions.

---

## MLB Priority

Recommended priority for high win probability:

1. Player props
2. Pitcher props
3. Team totals
4. Game winners
5. Parlays

Reason:

Player and pitcher props can often be predicted more directly from player-level data than game winners. Parlays should be last because they reduce total probability and should only be created from the safest approved legs.

---

# 3. Soccer Prediction Architecture

## Soccer Models Needed

SharpEdge V2 should not use one soccer model.

It needs separate prediction modules:

1. Match Result Model
2. Goals Model
3. Corners Model
4. Cards Model
5. Player Props Model
6. Parlay Leg Safety Model

---

## 3.1 Soccer Match Result Model

### Predicts

- Home win probability
- Draw probability
- Away win probability
- Double chance probability
- Draw no bet probability

### Input Features

| Feature | Source |
|---|---|
| Team recent form | API-Sports |
| Home/away form | API-Sports |
| League/tournament | API-Sports |
| FIFA/international flag | API-Sports |
| Rest days | Calculated |
| Travel/context | Calculated/manual later |
| Team ranking/standing | API-Sports |
| Goals for/against | API-Sports |
| xG/xGA if available | API-Sports or secondary source |
| Injuries/suspensions | API-Sports |
| Starting XI | API-Sports |
| Odds market probability | Odds API |
| Line movement | Odds API |
| Historical head-to-head | API-Sports |
| Tournament stage | API-Sports/manual classification |

### Output Example

- Argentina win: 62%
- Draw: 23%
- Opponent win: 15%
- Recommended safe result: Argentina +0.5 / Double Chance
- Higher value result: Argentina ML if edge supports it

---

## 3.2 Soccer Goals Model

### Predicts

- Expected total goals
- Over 0.5 / 1.5 / 2.5 / 3.5 goals probability
- Team total goals probability
- Both teams to score probability

### Input Features

| Feature | Source |
|---|---|
| Goals scored L5/L10 | API-Sports |
| Goals allowed L5/L10 | API-Sports |
| Shots | API-Sports |
| Shots on target | API-Sports |
| xG/xGA | API-Sports if available |
| Starting attackers | API-Sports |
| Missing defenders/goalkeeper | API-Sports |
| Match importance | Calculated/manual later |
| Odds totals | Odds API |
| Market movement | Odds API |

### Output Example

- Expected goals: 2.65
- Over 1.5 goals probability: 78%
- Over 2.5 goals probability: 54%
- BTTS probability: 57%

---

## 3.3 Soccer Corners Model

### Predicts

- Expected total corners
- Team corner projection
- Over/under corner line probability

### Input Features

| Feature | Source |
|---|---|
| Team corners for | API-Sports |
| Team corners against | API-Sports |
| Shots volume | API-Sports |
| Attacking pressure | API-Sports |
| Possession | API-Sports |
| Opponent defensive style | Derived |
| Match state tendency | Historical/live later |
| Corner odds line | Odds API if available |

### Output Example

- Expected corners: 9.4
- Over 8.5 corners probability: 63%
- Team A corners over 4.5 probability: 61%

---

## 3.4 Soccer Cards Model

### Predicts

- Expected total cards
- Team card count
- Over/under card line probability
- Player card probability if data supports it

### Input Features

| Feature | Source |
|---|---|
| Referee average cards | API-Sports if available |
| Referee red/yellow tendency | API-Sports if available |
| Team cards for/against | API-Sports |
| Fouls committed | API-Sports |
| Rivalry/tournament intensity | Derived/manual later |
| Player discipline | API-Sports |
| Match importance | Derived |
| Card odds line | Odds API if available |

### Output Example

- Expected cards: 4.8
- Over 3.5 cards probability: 71%
- Referee supports over cards: Yes

---

## 3.5 Soccer Player Props Model

### Predicts

- Shots
- Shots on target
- Goals
- Assists
- Player cards
- Fouls
- Passes/tackles if data available

### Input Features

| Feature | Source |
|---|---|
| Starting XI | API-Sports |
| Minutes projection | Calculated |
| Recent shots/SOT | API-Sports |
| Player role | API-Sports/manual mapping later |
| Penalty/set-piece role | Manual/derived later |
| Opponent weakness | Derived |
| Player prop odds | Odds API |

### Output Example

- Player shots on target over 0.5: 68%
- Player card over 0.5: 24%
- Player goal probability: 31%

---

# 4. MLB Prediction Architecture

## MLB Models Needed

SharpEdge V2 needs separate MLB prediction modules:

1. MLB Game Winner Model
2. MLB Team Total Model
3. MLB Batter Prop Model
4. MLB Pitcher Prop Model
5. MLB Bullpen Model
6. MLB Parlay Leg Safety Model

---

## 4.1 MLB Game Winner Model

### Predicts

- Home win probability
- Away win probability
- Run line probability

### Input Features

| Feature | Source |
|---|---|
| Starting pitcher | SportsDataIO / API-Sports |
| Team recent form | SportsDataIO / API-Sports |
| Home/away split | SportsDataIO / API-Sports |
| Bullpen strength | Calculated |
| Bullpen fatigue | Calculated |
| Lineups | SportsDataIO / API-Sports |
| Injuries | SportsDataIO |
| Weather | SportsDataIO / weather source later |
| Stadium/park factor | SportsDataIO + calculated |
| Umpire | SportsDataIO if available |
| Moneyline odds | Odds API |
| Run line odds | Odds API |
| Line movement | Odds API |
| Statcast team/batter/pitcher quality | pybaseball |

### Output Example

- Blue Jays win probability: 57%
- Yankees win probability: 43%
- Best safe side: Blue Jays +1.5
- Moneyline only if edge is strong

---

## 4.2 MLB Team Total Model

### Predicts

- Projected team runs
- Team total over/under probability
- Full game total probability

### Input Features

| Feature | Source |
|---|---|
| Starting pitcher weakness | SportsDataIO + Statcast |
| Bullpen weakness | Calculated |
| Batter lineup strength | SportsDataIO + Statcast |
| Park factor | SportsDataIO + calculated |
| Weather/wind | SportsDataIO/weather |
| Team OPS/wRC+ proxy | Statcast/pybaseball |
| Odds team totals | Odds API |

### Output Example

- Blue Jays projected runs: 4.8
- Blue Jays team total over 3.5 probability: 69%
- Full game over 8.5 probability: 58%

---

## 4.3 MLB Batter Prop Model

### Predicts

- Hit probability
- Total bases probability
- Run probability
- RBI probability
- Walk probability
- Strikeout probability

### Input Features

| Feature | Source |
|---|---|
| Batter L5/L10/L20 | SportsDataIO / pybaseball |
| Batter vs pitcher handedness | pybaseball |
| Pitcher pitch mix | pybaseball |
| Pitcher weakness | pybaseball |
| Batter exit velocity | pybaseball |
| Batter hard-hit rate | pybaseball |
| Batter barrel rate | pybaseball |
| Batter xBA/xSLG/xwOBA | pybaseball |
| Batting order | SportsDataIO/API-Sports |
| Confirmed lineup | SportsDataIO/API-Sports |
| Park/weather | SportsDataIO/weather |
| Prop line and odds | Odds API |

### Output Example

- Batter over 0.5 hits probability: 74%
- Batter total bases over 1.5 probability: 52%
- Batter RBI probability: 28%

---

## 4.4 MLB Pitcher Prop Model

### Predicts

- Strikeout projection
- Outs projection
- Earned runs projection
- Walks allowed projection

### Input Features

| Feature | Source |
|---|---|
| Pitcher L5/L10 starts | SportsDataIO / pybaseball |
| Pitch count trend | SportsDataIO |
| K rate | pybaseball |
| BB rate | pybaseball |
| Opponent K rate | pybaseball |
| Umpire strike-zone bias | SportsDataIO if available / later source |
| Weather/park | SportsDataIO/weather |
| Opponent lineup handedness | SportsDataIO/API-Sports |
| Odds prop line | Odds API |

### Output Example

- Pitcher strikeouts projection: 5.6
- Under 6.5 strikeouts probability: 66%
- Over 4.5 strikeouts probability: 72%

---

## 4.5 MLB Bullpen Model

### Predicts

- Bullpen strength score
- Bullpen fatigue score
- Late-game risk score

### Input Features

| Feature | Source |
|---|---|
| Relief pitcher innings last 3 days | SportsDataIO/API-Sports |
| Bullpen ERA | Calculated |
| Bullpen WHIP | Calculated |
| Bullpen runs allowed recent | Calculated |
| Back-to-back use | Calculated |
| Closer availability | SportsDataIO if available |

### Output Example

- Bullpen strength: 78/100
- Bullpen fatigue: High
- Late-game risk: Elevated

---

# 5. Market and Odds Features

## Odds API Usage

The Odds API is critical because it gives the market view.

### Collect

- Moneyline
- Spread/run line
- Totals
- Team totals
- Player props
- Pitcher props
- Soccer result odds
- Soccer totals
- Corners/cards if available
- Odds by sportsbook
- Timestamped snapshots

### Calculate

- Implied probability
- No-vig probability
- Market average
- Best available odds
- Line movement
- Reverse line movement
- Closing line value after game starts

---

# 6. Feature Store Design

Every game should have one complete feature object before prediction.

Stored in:

`model_features`

### team_features

Examples:

```json
{
  "home_form_l5": 0.6,
  "away_form_l5": 0.4,
  "home_goals_l5": 1.8,
  "away_goals_allowed_l5": 1.4
}
