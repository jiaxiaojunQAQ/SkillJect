#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trade Analyzer Core Module
交易策略分析核心模块
"""

import csv
import re
from datetime import datetime
from typing import List, Dict, Any, Tuple


class TradeRecord:
    """单条交易记录"""
    def __init__(self):
        self.date = ""           # 交易日期
        self.stock = ""          # 股票名称
        self.buy_price = 0.0     # 买入价
        self.sell_price = 0.0    # 卖出价
        self.return_rate = 0.0   # 收益率（%）
        self.strategy = ""       # 交易策略
        self.hold_days = 0       # 持仓天数
        self.buy_reason = ""     # 买入理由
        self.sell_reason = ""    # 卖出理由
    
    def is_profit(self) -> bool:
        """是否盈利"""
        return self.return_rate > 0
    
    def __repr__(self):
        return f"Trade({self.stock}: {self.return_rate:+.2f}%)"


class TradeAnalyzer:
    """交易分析器"""
    
    def __init__(self):
        self.records: List[TradeRecord] = []
        self.stats: Dict[str, Any] = {}
    
    def parse_csv(self, file_path: str) -> bool:
        """解析 CSV 文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self._parse_records(reader)
            return True
        except Exception as e:
            print(f"CSV 解析错误: {e}")
            return False
    
    def parse_text(self, text: str) -> bool:
        """解析文本格式"""
        try:
            lines = text.strip().split('\n')
            for line in lines:
                if not line.strip():
                    continue
                record = self._parse_text_line(line)
                if record:
                    self.records.append(record)
            return len(self.records) > 0
        except Exception as e:
            print(f"文本解析错误: {e}")
            return False
    
    def _parse_records(self, reader):
        """解析记录（智能列名映射）"""
        # 列名映射表
        column_mapping = {
            'date': ['日期', 'date', 'time', '买入日期', '卖出日期'],
            'stock': ['股票', 'stock', 'name', '买入股份', '股票名称', '个股'],
            'return': ['收益', 'return', '收益率', '盈亏', 'profit', '收益额'],
            'strategy': ['策略', 'strategy', '买入策略', '交易方式'],
            'sell_reason': ['卖出策略', 'sell_reason', '卖出理由']
        }
        
        headers = reader.fieldnames or []
        
        # 找到实际列名
        col_date = self._find_column(headers, column_mapping['date'])
        col_stock = self._find_column(headers, column_mapping['stock'])
        col_return = self._find_column(headers, column_mapping['return'])
        col_strategy = self._find_column(headers, column_mapping['strategy'])
        col_sell_reason = self._find_column(headers, column_mapping['sell_reason'])
        
        for row in reader:
            record = TradeRecord()
            
            # 提取数据
            if col_date:
                record.date = row.get(col_date, '')
            if col_stock:
                record.stock = row.get(col_stock, '')
            if col_strategy:
                record.strategy = row.get(col_strategy, '')
            if col_sell_reason:
                record.sell_reason = row.get(col_sell_reason, '')
            
            # 解析收益率
            if col_return:
                return_str = row.get(col_return, '0')
                record.return_rate = self._parse_return_rate(return_str)
            
            self.records.append(record)
    
    def _find_column(self, headers: List[str], candidates: List[str]) -> str:
        """查找匹配的列名"""
        for header in headers:
            if any(cand in header for cand in candidates):
                return header
        return headers[0] if headers else None
    
    def _parse_return_rate(self, s: str) -> float:
        """解析收益率字符串"""
        # 移除 % 符号和空格
        s = s.replace('%', '').replace(' ', '').strip()
        try:
            return float(s)
        except:
            return 0.0
    
    def _parse_text_line(self, line: str) -> TradeRecord:
        """解析单行文本"""
        parts = line.split(',')
        if len(parts) < 3:
            return None
        
        record = TradeRecord()
        record.date = parts[0].strip()
        record.stock = parts[1].strip()
        
        # 查找收益率（通常包含 %）
        for part in parts:
            if '%' in part:
                record.return_rate = self._parse_return_rate(part)
            elif any(kw in part for kw in ['打板', '低吸', '追涨', '价值投资']):
                record.strategy = part.strip()
            elif any(kw in part for kw in ['涨停', '炸板', '跳水', '回落']):
                record.sell_reason = part.strip()
        
        return record
    
    def calculate_stats(self) -> Dict[str, Any]:
        """计算统计数据"""
        if not self.records:
            return {}
        
        total = len(self.records)
        profits = [r for r in self.records if r.is_profit()]
        losses = [r for r in self.records if not r.is_profit()]
        
        # 基础统计
        win_count = len(profits)
        loss_count = len(losses)
        win_rate = win_count / total * 100 if total > 0 else 0
        
        # 收益统计
        avg_profit = sum(r.return_rate for r in profits) / len(profits) if profits else 0
        avg_loss = sum(r.return_rate for r in losses) / len(losses) if losses else 0
        
        # 盈亏比
        profit_loss_ratio = abs(avg_profit / avg_loss) if avg_loss != 0 else 0
        
        # 最大单笔
        max_profit = max(r.return_rate for r in profits) if profits else 0
        max_loss = min(r.return_rate for r in losses) if losses else 0
        
        # 总收益（简化计算，不考虑仓位）
        total_return = sum(r.return_rate for r in self.records)
        
        # 连续统计
        max_consecutive_losses = self._calc_consecutive_losses()
        
        # 策略一致性
        strategy_consistency = self._calc_strategy_consistency()
        
        self.stats = {
            'total_trades': total,
            'win_count': win_count,
            'loss_count': loss_count,
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'profit_loss_ratio': profit_loss_ratio,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'total_return': total_return,
            'max_consecutive_losses': max_consecutive_losses,
            'strategy_consistency': strategy_consistency
        }
        
        return self.stats
    
    def _calc_consecutive_losses(self) -> int:
        """计算最大连续亏损次数"""
        max_streak = 0
        current_streak = 0
        
        for record in self.records:
            if not record.is_profit():
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        
        return max_streak
    
    def _calc_strategy_consistency(self) -> Dict[str, Any]:
        """计算策略一致性"""
        if not self.records:
            return {}
        
        # 买入策略一致性
        strategies = [r.strategy for r in self.records if r.strategy]
        strategy_consistency = 0
        if strategies:
            most_common = max(set(strategies), key=strategies.count)
            strategy_consistency = strategies.count(most_common) / len(strategies) * 100
        
        # 卖出纪律评分
        sell_reasons = [r.sell_reason for r in self.records if r.sell_reason]
        has_sell_reason = len(sell_reasons) / len(self.records) * 100 if self.records else 0
        
        # 止损控制（亏损 < -10% 的比例）
        large_losses = [r for r in self.records if r.return_rate < -10]
        stop_loss_score = (1 - len(large_losses) / len(self.records)) * 100 if self.records else 0
        
        return {
            'buy_consistency': strategy_consistency,
            'sell_discipline': has_sell_reason,
            'stop_loss_control': stop_loss_score,
            'overall_score': (strategy_consistency + has_sell_reason + stop_loss_score) / 3
        }
    
    def generate_report(self) -> str:
        """生成 Markdown 报告"""
        if not self.stats:
            self.calculate_stats()
        
        s = self.stats
        
        report = f"""# 📊 交易策略分析报告

---

## 一、核心数据概览

| 指标 | 数值 | 评级 |
|------|------|------|
| 总交易次数 | {s.get('total_trades', 0)} 笔 | - |
| 盈利次数 | {s.get('win_count', 0)} 笔 | - |
| 亏损次数 | {s.get('loss_count', 0)} 笔 | - |
| **胜率** | **{s.get('win_rate', 0):.1f}%** | {self._rate_win_rate(s.get('win_rate', 0))} |
| **盈亏比** | **{s.get('profit_loss_ratio', 0):.2f} : 1** | {self._rate_pl_ratio(s.get('profit_loss_ratio', 0))} |
| 平均盈利 | +{s.get('avg_profit', 0):.2f}% | - |
| 平均亏损 | {s.get('avg_loss', 0):.2f}% | - |
| 最大单笔盈利 | +{s.get('max_profit', 0):.2f}% | - |
| 最大单笔亏损 | {s.get('max_loss', 0):.2f}% | - |
| 累计收益率 | {s.get('total_return', 0):+.2f}% | - |
| 最大连续亏损 | {s.get('max_consecutive_losses', 0)} 次 | - |

---

## 二、胜率与盈亏比分析

{self._generate_profit_chart()}

**分析要点：**
{self._analyze_win_loss()}

---

## 三、风险指标评估

- **最大回撤估算**: 基于单笔最大亏损和连续亏损推算
- **风险等级**: {self._calc_risk_level()}
- **止损纪律**: {s.get('strategy_consistency', {}).get('stop_loss_control', 0):.1f}%

---

## 四、策略一致性评分

| 维度 | 得分 | 说明 |
|------|------|------|
| 买入一致性 | {s.get('strategy_consistency', {}).get('buy_consistency', 0):.1f}% | 买入方式是否统一 |
| 卖出纪律 | {s.get('strategy_consistency', {}).get('sell_discipline', 0):.1f}% | 是否有明确卖出理由 |
| 止损控制 | {s.get('strategy_consistency', {}).get('stop_loss_control', 0):.1f}% | 大额亏损控制 |
| **综合评分** | **{s.get('strategy_consistency', {}).get('overall_score', 0):.1f}/100** | - |

**评级**: {self._rate_consistency(s.get('strategy_consistency', {}).get('overall_score', 0))}

---

## 五、交易行为画像

### 主要特征
{self._generate_behavior_profile()}

### 常见模式
{self._find_patterns()}

---

## 六、改进建议

{self._generate_suggestions()}

---

## 七、数据附录

**原始交易记录（前10笔）**

| 日期 | 股票 | 策略 | 收益率 | 卖出理由 |
|------|------|------|--------|----------|
"""
        
        # 添加前10笔交易详情
        for i, r in enumerate(self.records[:10], 1):
            report += f"| {r.date} | {r.stock} | {r.strategy} | {r.return_rate:+.2f}% | {r.sell_reason} |\n"
        
        return report
    
    def _rate_win_rate(self, rate: float) -> str:
        """胜率评级"""
        if rate >= 70:
            return "⭐⭐⭐ 优秀"
        elif rate >= 60:
            return "⭐⭐ 良好"
        elif rate >= 50:
            return "⭐ 合格"
        else:
            return "⚠️ 需改进"
    
    def _rate_pl_ratio(self, ratio: float) -> str:
        """盈亏比评级"""
        if ratio >= 2.0:
            return "⭐⭐⭐ 优秀"
        elif ratio >= 1.5:
            return "⭐⭐ 良好"
        elif ratio >= 1.0:
            return "⭐ 合格"
        else:
            return "⚠️ 需改进"
    
    def _rate_consistency(self, score: float) -> str:
        """一致性评级"""
        if score >= 80:
            return "⭐⭐⭐ 极高一致性，纪律严明"
        elif score >= 60:
            return "⭐⭐ 较好，偶有冲动交易"
        elif score >= 40:
            return "⭐ 一般，需要加强纪律"
        else:
            return "⚠️ 较差，建议暂停交易完善系统"
    
    def _generate_profit_chart(self) -> str:
        """生成 ASCII 收益分布图"""
        if not self.records:
            return "暂无数据"
        
        # 分桶统计
        buckets = {
            '>+20%': 0,
            '+10~20%': 0,
            '+5~10%': 0,
            '0~5%': 0,
            '-5~0%': 0,
            '-10~-5%': 0,
            '<-10%': 0
        }
        
        for r in self.records:
            rate = r.return_rate
            if rate > 20:
                buckets['>+20%'] += 1
            elif rate > 10:
                buckets['+10~20%'] += 1
            elif rate > 5:
                buckets['+5~10%'] += 1
            elif rate > 0:
                buckets['0~5%'] += 1
            elif rate > -5:
                buckets['-5~0%'] += 1
            elif rate > -10:
                buckets['-10~-5%'] += 1
            else:
                buckets['<-10%'] += 1
        
        max_count = max(buckets.values()) if buckets else 1
        
        chart = "```\n收益分布:\n"
        for label, count in buckets.items():
            bar = "█" * int(count / max_count * 30)
            chart += f"{label:8s} | {bar} {count}\n"
        chart += "```"
        
        return chart
    
    def _analyze_win_loss(self) -> str:
        """分析胜率盈亏特征"""
        win_rate = self.stats.get('win_rate', 0)
        pl_ratio = self.stats.get('profit_loss_ratio', 0)
        
        analysis = []
        
        if win_rate >= 70:
            analysis.append("- ✅ **高胜率型选手**：胜率超过 70%，说明入场点选择优秀，能避开很多陷阱")
        elif win_rate >= 60:
            analysis.append("- ✅ **胜率良好**：60%+ 的胜率在短线交易中属于中上水平")
        else:
            analysis.append("- ⚠️ **胜率偏低**：建议减少交易频率，提高选股标准")
        
        if pl_ratio >= 2.0:
            analysis.append("- ✅ **盈亏比优秀**：赚多亏少，长期盈利能力强")
        elif pl_ratio >= 1.5:
            analysis.append("- ✅ **盈亏比良好**：符合健康交易的盈亏比标准")
        else:
            analysis.append("- ⚠️ **盈亏比偏低**：存在"赚小亏大"问题，需要优化卖点或加强止损")
        
        if win_rate > 60 and pl_ratio < 1.5:
            analysis.append("- 💡 **核心问题**：高胜率但盈亏比不足，典型"卖飞"型选手，需要学会让利润奔跑")
        
        return "\n".join(analysis)
    
    def _calc_risk_level(self) -> str:
        """计算风险等级"""
        max_loss = self.stats.get('max_loss', 0)
        consecutive = self.stats.get('max_consecutive_losses', 0)
        
        if max_loss > -15 or consecutive > 5:
            return "⚠️ 高风险（需加强风控）"
        elif max_loss > -10 or consecutive > 3:
            return "⚡ 中等风险"
        else:
            return "✅ 低风险（风控良好）"
    
    def _generate_behavior_profile(self) -> str:
        """生成交易行为画像"""
        if not self.records:
            return "暂无数据"
        
        profiles = []
        
        # 分析买入策略
        strategies = [r.strategy for r in self.records if r.strategy]
        if strategies:
            main_strategy = max(set(strategies), key=strategies.count)
            strategy_pct = strategies.count(main_strategy) / len(strategies) * 100
            profiles.append(f"1. **主要策略**：{main_strategy}（占比 {strategy_pct:.1f}%）")
        
        # 分析卖出特征
        sell_reasons = [r.sell_reason for r in self.records if r.sell_reason]
        if sell_reasons:
            if any('炸板' in s for s in sell_reasons):
                profiles.append("2. **卖出特征**：严格执行'炸板即卖'纪律，机械性强")
            if any('跳水' in s for s in sell_reasons):
                profiles.append("3. **止损风格**：开盘不利即止损，不抱幻想")
        
        # 持仓周期估算
        avg_return = self.stats.get('avg_profit', 0)
        if avg_return > 10:
            profiles.append("4. **盈亏特征**：平均盈利较高，可能有部分持仓较长的交易")
        
        return "\n\n".join(profiles) if profiles else "特征不明显，建议补充更详细的交易记录"
    
    def _find_patterns(self) -> str:
        """发现交易模式"""
        patterns = []
        
        # 检查卖飞模式
        sell_reasons = [r.sell_reason for r in self.records if r.sell_reason]
        if any('虽然' in s or '拿不住' in s for s in sell_reasons):
            patterns.append("- 🔄 **卖飞模式**：多次提到'虽然后面涨停，但是拿不住'，说明卖点偏早")
        
        # 检查止损一致性
        losses = [r for r in self.records if not r.is_profit()]
        if losses:
            avg_loss = sum(r.return_rate for r in losses) / len(losses)
            if avg_loss > -8:
                patterns.append(f"- ✅ **止损优秀**：平均止损 {avg_loss:.1f}%，控制良好")
            else:
                patterns.append(f"- ⚠️ **止损偏慢**：平均亏损 {avg_loss:.1f}%，建议收紧止损线")
        
        # 检查胜率稳定性
        win_rate = self.stats.get('win_rate', 0)
        if win_rate > 70:
            patterns.append("- 🎯 **高胜率优势**：入场点选择精准，这是核心竞争力")
        
        return "\n".join(patterns) if patterns else "暂无显著模式"
    
    def _generate_suggestions(self) -> str:
        """生成改进建议"""
        suggestions = []
        
        win_rate = self.stats.get('win_rate', 0)
        pl_ratio = self.stats.get('profit_loss_ratio', 0)
        consistency = self.stats.get('strategy_consistency', {}).get('overall_score', 0)
        
        # 根据数据特征给出建议
        if win_rate > 60 and pl_ratio < 1.5:
            suggestions.append("""### 1. 解决"卖飞"问题 ⭐ 优先级：高

**问题**：高胜率但盈亏比不足，说明经常赚一点就跑，错过了大行情。

**解决方案**：
- 引入"龙头识别机制"：板块最强股给予更多容错空间
- 分时强度判断：不跌破昨日收盘价不卖
- 分批卖出：涨 5% 卖 1/3，涨 10% 再卖 1/3，剩余让利润奔跑
- 设置移动止损：从最高点回撤 8% 再卖出

**预期效果**：盈亏比从 1.5 提升到 2.0+""")
        
        if consistency < 70:
            suggestions.append("""### 2. 提升策略一致性 ⭐ 优先级：中

**问题**：交易纪律有波动，可能存在冲动交易。

**解决方案**：
- 建立交易 checklist，每笔交易前必须勾选
- 设置"冷静期"：连续亏损 2 笔后，强制休息 1 天
- 减少交易频率，只做 A 级机会

**预期效果**：一致性评分提升到 80+""")
        
        suggestions.append("""### 3. 完善仓位管理 ⭐ 优先级：中

**当前**：单票均仓，没有利用高胜率优势

**优化方案**：
```
试探仓位（30%）：打板买入，确认强势
加仓时机（+30%）：次日高开秒板，板块助攻
满仓条件（+40%）：成为市场最高板，情绪冰点转修复

止损逻辑：
- 第一层亏损：止损 30%，总风险可控
- 第二层亏损：止损 60%，反思加仓时机
```

**风险控制**：只在"冰点→修复"阶段加仓，"过热"阶段不加仓""")
        
        suggestions.append("""### 4. 建立空仓机制 ⭐ 优先级：高

**触发空仓的条件**（满足任一）：
- 连续 3 笔交易亏损
- 当月收益回撤 > 15%
- 市场情绪连续 3 天沸点（>80）
- 跌停数 > 50 家持续 2 天

**空仓时长**：至少 3-5 个交易日

**空仓期间**：只做复盘和观察，不开新仓""")
        
        return "\n\n---\n\n".join(suggestions)


# 便捷函数
def analyze_file(file_path: str) -> str:
    """分析文件并返回报告"""
    analyzer = TradeAnalyzer()
    
    if file_path.endswith('.csv'):
        success = analyzer.parse_csv(file_path)
    else:
        # 尝试作为文本解析
        with open(file_path, 'r', encoding='utf-8') as f:
            success = analyzer.parse_text(f.read())
    
    if not success or not analyzer.records:
        return "解析失败，请检查文件格式"
    
    return analyzer.generate_report()


def analyze_text(text: str) -> str:
    """分析文本并返回报告"""
    analyzer = TradeAnalyzer()
    
    if not analyzer.parse_text(text):
        return "解析失败，请检查文本格式"
    
    return analyzer.generate_report()


if __name__ == '__main__':
    # 测试代码
    import sys
    if len(sys.argv) > 1:
        print(analyze_file(sys.argv[1]))
    else:
        print("Usage: python analyzer.py <file_path>")
