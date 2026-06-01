# Trade Analyzer - 使用示例

## 快速开始

### 方式一：分析 CSV 文件

```python
from analyzer import analyze_file

report = analyze_file("交易记录.csv")
print(report)
```

### 方式二：分析文本数据

```python
from analyzer import analyze_text

text_data = """
4月30日,全筑股份,打板,5月7日,涨停炸板,20%
5月6日,川润股份,打板,5月7日,开盘跳水,4%
"""

report = analyze_text(text_data)
print(report)
```

### 方式三：直接使用分析器

```python
from analyzer import TradeAnalyzer

analyzer = TradeAnalyzer()

# 解析数据
analyzer.parse_csv("交割单.csv")
# 或
analyzer.parse_text(text_data)

# 获取统计数据
stats = analyzer.calculate_stats()
print(f"胜率: {stats['win_rate']:.1f}%")
print(f"盈亏比: {stats['profit_loss_ratio']:.2f}")

# 生成完整报告
report = analyzer.generate_report()
```

## CSV 文件格式要求

### 标准格式
```csv
日期,股票,买入策略,卖出日期,卖出策略,收益
4月30日,全筑股份,打板,5月7日,涨停炸板,20%
5月6日,川润股份,打板,5月7日,开盘跳水,4%
```

### 支持的列名变体

**日期列**：日期、date、time、买入日期、卖出日期

**股票列**：股票、stock、name、买入股份、股票名称、个股

**收益列**：收益、return、收益率、盈亏、profit、收益额

**策略列**：策略、strategy、买入策略、交易方式

**卖出理由**：卖出策略、sell_reason、卖出理由

> 提示：系统会自动识别常见列名，不需要严格匹配。

## 输出报告解读

### 核心数据概览
- **胜率**：盈利次数占比，>70% 为优秀
- **盈亏比**：平均盈利/平均亏损，>1.5 为良好
- **总收益率**：累计收益，参考性指标

### 策略一致性评分
- **买入一致性**：是否使用统一的买入方式
- **卖出纪律**：是否有明确的卖出规则
- **止损控制**：大额亏损的控制能力

### 改进建议
根据数据特征自动生成的个性化建议，包括：
- 卖点优化（解决卖飞）
- 仓位管理升级
- 空仓机制建立
- 交易纪律强化

## 高级用法

### 自定义分析

```python
from analyzer import TradeAnalyzer

analyzer = TradeAnalyzer()
analyzer.parse_csv("交割单.csv")

# 获取原始记录
for record in analyzer.records:
    print(f"{record.stock}: {record.return_rate}%")

# 自定义统计
profits = [r for r in analyzer.records if r.is_profit()]
print(f"盈利交易数: {len(profits)}")
```

## 常见问题

**Q: 支持哪些文件格式？**
A: CSV (.csv) 和文本格式。Excel (.xlsx) 需要配合 document-pro 技能使用。

**Q: 列名必须严格匹配吗？**
A: 不需要，系统支持智能列名映射，能识别常见的中文列名。

**Q: 数据格式不标准怎么办？**
A: 建议先整理成 CSV 格式，或使用 parse_text 方法传入清理后的文本。

**Q: 能分析多少条记录？**
A: 建议单次分析 <1000 条，太多会影响性能。

## 示例报告预览

```markdown
# 📊 交易策略分析报告

## 一、核心数据概览

| 指标 | 数值 | 评级 |
|------|------|------|
| 总交易次数 | 49 笔 | - |
| **胜率** | **73.5%** | ⭐⭐⭐ 优秀 |
| **盈亏比** | **1.53 : 1** | ⭐⭐ 良好 |
| 平均盈利 | +9.8% | - |
| 平均亏损 | -6.4% | - |

...
```
