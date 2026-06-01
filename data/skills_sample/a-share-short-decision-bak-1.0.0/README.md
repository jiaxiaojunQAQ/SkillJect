# a-share-short-decision

A股短线（1-5日）决策 Skill，基于 AkShare 实时/历史数据进行情绪、板块、个股与资金流分析。

## 目录结构

```text
a-share-short-decision/
├── tools/
│   ├── __init__.py
│   ├── settings.py
│   ├── market_data.py
│   ├── indicators.py
│   ├── sentiment.py
│   ├── money_flow.py
│   ├── fusion_engine.py
│   ├── risk_control.py
│   ├── reporting.py
│   └── decision_eval.py
├── prompts/
│   └── analysis_prompt.txt
├── data/
│   └── decision_log.jsonl
├── scheduler.yaml
├── config.json
├── main.py
├── SKILL.md
└── README.md
```

## 安装

```bash
pip install akshare pandas
```

## 常用命令

```bash
# 当日短线信号
python main.py short_term_signal_engine

# 指定日期短线信号
python main.py short_term_signal_engine --date 2026-02-12

# 记录指定日期预测
python main.py run_prediction_for_date --date 2026-02-12

# 对比预测与实际表现
python main.py compare_prediction_with_market --prediction-date 2026-02-12 --actual-date 2026-02-13

# 生成日报
python main.py generate_daily_report --date 2026-02-12

# 调试模式
python main.py short_term_signal_engine --date 2026-02-12 --debug
```

## 数据策略

- 默认严格真实数据模式：`config.json` 中 `data_source.fallback_enabled=false`
- 当关键数据不可用时，返回 `data_source: unavailable` 和友好提示，不返回模拟股票

## 筛股参数配置

筛股参数位于 `config.json` 的 `strategy.screener`。

主要字段：
- `prefilter_change_pct`：初筛涨幅阈值（实时池）
- `min_change_pct`：最终候选最低涨幅
- `min_volume_ratio`：最低量比阈值
- `trend_lookback`：趋势判断回看天数
- `min_history_days`：最小历史K线天数
- `volume_baseline_days`：量比基准窗口
- `high_volume_bearish_drop_pct`：高位巨量阴线跌幅阈值
- `high_volume_bearish_vol_ratio`：高位巨量阴线量比阈值
- `historical_mode.*`：历史日期模式专用阈值

---

## 三档模板（可直接复制）

使用方式：将 `config.json` 里的 `strategy.screener` 整段替换为以下任意一档。

### 1) 激进（更多标的，容忍噪音）

```json
"screener": {
  "prefilter_change_pct": 3.0,
  "min_change_pct": 3.5,
  "min_volume_ratio": 1.1,
  "trend_lookback": 2,
  "min_history_days": 5,
  "volume_baseline_days": 4,
  "high_volume_bearish_drop_pct": -4.0,
  "high_volume_bearish_vol_ratio": 3.0,
  "historical_mode": {
    "min_change_pct": 2.0,
    "trend_lookback": 2,
    "min_volume_ratio": 1.0,
    "high_volume_bearish_drop_pct": -4.5,
    "high_volume_bearish_vol_ratio": 3.2,
    "relaxed_pick_from_pool_when_empty": true
  }
}
```

适用：情绪强周期、想要更多候选、可接受更高回撤。

### 2) 平衡（默认推荐）

```json
"screener": {
  "prefilter_change_pct": 4.5,
  "min_change_pct": 5.0,
  "min_volume_ratio": 1.5,
  "trend_lookback": 3,
  "min_history_days": 6,
  "volume_baseline_days": 5,
  "high_volume_bearish_drop_pct": -2.0,
  "high_volume_bearish_vol_ratio": 2.2,
  "historical_mode": {
    "min_change_pct": 3.0,
    "trend_lookback": 2,
    "min_volume_ratio": 1.2,
    "high_volume_bearish_drop_pct": -3.0,
    "high_volume_bearish_vol_ratio": 2.8,
    "relaxed_pick_from_pool_when_empty": true
  }
}
```

适用：大多数常规短线场景。

### 3) 保守（数量更少，质量优先）

```json
"screener": {
  "prefilter_change_pct": 6.0,
  "min_change_pct": 7.0,
  "min_volume_ratio": 1.8,
  "trend_lookback": 4,
  "min_history_days": 8,
  "volume_baseline_days": 6,
  "high_volume_bearish_drop_pct": -1.5,
  "high_volume_bearish_vol_ratio": 1.8,
  "historical_mode": {
    "min_change_pct": 4.5,
    "trend_lookback": 3,
    "min_volume_ratio": 1.4,
    "high_volume_bearish_drop_pct": -2.2,
    "high_volume_bearish_vol_ratio": 2.2,
    "relaxed_pick_from_pool_when_empty": false
  }
}
```

适用：震荡期/弱市，优先控制误判与回撤。

---

## 风险说明

本工具仅用于策略研究与辅助决策，不构成投资建议。股市有风险，入市需谨慎。
