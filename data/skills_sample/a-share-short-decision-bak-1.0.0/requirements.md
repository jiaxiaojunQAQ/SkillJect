12 files changed
+539
-218



README.md
这是一套专门为 A股短线（1~5日） 设计的 OpenClaw Skill 方案,请实现.
🎯 一、短线模型核心逻辑
A股短线最重要的 4 件事：
情绪强度（涨停家数、连板高度）
板块强度（行业轮动）
成交量放大
资金流向（主力/北向）
技术指标在短线里权重较低。
🧠 二、短线模型结构（重构版）
市场情绪监测
      ↓
强势板块识别
      ↓
个股强弱筛选
      ↓
量能确认
      ↓
资金确认
      ↓
评分引擎
      ↓
风控过滤
      ↓
OpenClaw解释 + 推送

🏗 三、Tool 设计
短线专用工具,数据来源AkShare
1️⃣ Tool: get_market_sentiment ⭐⭐⭐
短线最重要模块。
数据：
今日涨停家数
连板高度
跌停家数
炸板率
成交额
输出：
{
  "limit_up": 65,
  "limit_down": 4,
  "max_height": 4,
  "break_rate": 0.18,
  "market_sentiment_score": 72
}

评分逻辑：
涨停 > 50 → 情绪强
跌停 < 10 → 风险低
连板 ≥ 3 → 投机活跃
2️⃣ Tool: get_sector_rotation ⭐⭐⭐
找出当天强势板块。
数据：
板块涨幅
板块成交额
板块涨停数量
输出：
{
  "top_sectors": [
    {"name": "算力", "strength": 85},
    {"name": "AI", "strength": 78}
  ]
}

3️⃣ Tool: scan_strong_stocks ⭐⭐⭐
在强势板块中筛选个股：
筛选条件：
今日涨幅 > 5%
成交量放大 > 1.5
近3日趋势向上
未处于高位巨量阴线
输出：
[
  {
    "code": "300XXX",
    "volume_ratio": 2.3,
    "strength_rank": 1
  }
]

4️⃣ Tool: analyze_capital_flow
短线非常关键。
关注：
主力净流入
北向连续流入天数
资金强度排名
输出：
{
  "main_flow": 180000000,
  "flow_trend": "3-day-inflow"
}

5️⃣ Tool: short_term_signal_engine（核心重构）
短线评分模型（0~100）：
因子权重
市场情绪
25%
板块强度
25%
个股量能
20%
资金流入
20%
技术结构
10%
规则：
score ≥ 75 → 强势短线标的
60~75 → 观察
<60 → 放弃
输出：
{
  "score": 82,
  "signal": "SHORT_BUY",
  "holding_days": "1-3",
  "confidence": 0.68
}

6️⃣ Tool: short_term_risk_control ⭐⭐⭐
短线必须风控严格。
规则：
单股仓位 ≤ 15%
跌破5日线止损
-6% 自动止损
市场情绪 < 40 禁止开仓
输出：
{
  "max_position": 0.15,
  "stop_loss": -6,
  "take_profit": 12,
  "market_filter": true
}

📜 四、短线 Agent Prompt（重写）
System Prompt：
你是A股短线交易策略分析师。

目标：
1-3日交易周期
优先考虑情绪与量能
严格风险控制

请输出：
- 当前市场情绪判断
- 强势板块
- 推荐个股（如有）
- 入场逻辑
- 止损建议
- 风险提示

避免长期投资逻辑。

� 五、完整 Skill 目录结构建议
a-share-short-decision/
│
├── tools/
│   ├── market_data.py
│   ├── indicators.py
│   ├── sentiment.py
│   ├── money_flow.py
│   ├── fusion_engine.py
│   └── risk_control.py
│
├── prompts/
│   └── analysis_prompt.txt
│
├── scheduler.yaml
├── config.json
└── README.md

�📅 六、短线每日流程设计
14:30 盘中扫描
情绪判断
强板块识别
强势个股初筛
15:10 收盘确认
量能是否确认
是否封板
是否放量回落
15:20 推送报告
📨 七、每日推送格式
【A股短线日报】

市场情绪：偏强（涨停62家）
最高连板：4板
炸板率：18%

强势板块：
1. AI算力
2. 存储芯片

短线关注：
300XXX
- 量能放大2.3倍
- 主力净流入1.8亿
- 板块龙头

建议：
轻仓试错（≤15%）
止损 -6%
目标 +10~15%

风险：
指数接近压力位

🔥 八、短线模型关键升级点
你可以继续升级：
1️⃣ 打板模型
2️⃣ 低吸模型
3️⃣ 反包模型
4️⃣ 龙头战法
5️⃣ 连板博弈模型
⚠️ 九、短线必须知道的现实
A股短线：
极端波动
情绪切换快
黑天鹅多
必须：
小仓位
严格止损
只做情绪上升期