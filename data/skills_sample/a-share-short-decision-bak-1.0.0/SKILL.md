---
name: A股短线交易决策 A-Share Short-Term Decision
slug: a-share-short-decision
description: A-share short-term trading decision skill for 1-5 day horizon. Use when you need real-data market sentiment, sector rotation, strong stock scanning, capital flow confirmation, date-based short-term signal scoring, prediction logging, and next-day market comparison for CN A-share momentum trading.
---

# A-Share Short-Term Decision Skill

Implement in sequence:

1. Run `short_term_signal_engine(analysis_date)` for target date.
2. If needed, persist prediction with `run_prediction_for_date(analysis_date)`.
3. Compare prediction vs actual market with `compare_prediction_with_market(prediction_date, actual_date)`.
4. Output report with `generate_daily_report(analysis_date)`.

## Tool Contracts

### `short_term_signal_engine(analysis_date=None)`

- `analysis_date`: `YYYY-MM-DD` or `YYYYMMDD`
- Returns weighted short-term score and recommendation status.
- Always returns friendly `no_recommendation_message` when no tradable candidate exists.

### `run_prediction_for_date(analysis_date)`

- Runs signal engine for the specified date.
- Appends decision snapshot into `data/decision_log.jsonl`.

### `compare_prediction_with_market(prediction_date, actual_date=None)`

- Loads prediction from log (or auto-generates if missing).
- Compares predicted candidates against real market closes on `actual_date`.
- Returns per-stock return and summary statistics.

## No-Recommendation Behavior

Required behavior:
- Never return empty output.
- If `candidates` is empty or signal is `NO_TRADE`, explicitly say: `当前暂无可执行短线买入标的`.
- Include reason and next action.

## Runtime

```bash
python3 main.py short_term_signal_engine --date 2026-02-12
python3 main.py run_prediction_for_date --date 2026-02-12
python3 main.py compare_prediction_with_market --prediction-date 2026-02-12 --actual-date 2026-02-13
python3 main.py generate_daily_report --date 2026-02-12
```

## Subskills Workflow

For recurring optimize-then-recommend flow, run:

```bash
python3 subskills/config-optimization/optimize_from_aggressive.py --analysis-period "2026-02-01 to 2026-02-12"
python3 subskills/daily-recommendation/generate_daily_recommendation.py --date 2026-02-14
```

All generated artifacts are stored under `data/`.
