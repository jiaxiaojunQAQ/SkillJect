# 两层搜索策略详细指南

## 概述
本指南说明数据采集仅使用 Agent 内置的 `web_search` 与 `web_fetch`。
无需 API key；当两层都无法获取到足够信息时，需要明确标注“数据暂不可得”。

---

## 🎯 两层搜索策略流程

### 第1层：Agent 内置 `web_search`
- 快速获取基础信息
- 预计时间：5-10 秒
- 失败判断：结果为空或与查询不相关

### 第2层：Agent 内置 `web_fetch`
- 深度抓取页面内容并解析关键片段
- 预计时间：10-20 秒
- 失败判断：返回内容为空、超时错误或触发验证码/拦截

### 两层均失败
- 标注“数据暂不可得”
- 说明缺失数据可能影响的范围
- 给出可替代的检索方向或关键字调整建议

---

## 📊 第1层：web_search

### 使用方法（示例）
```markdown
web_search(
  query="中国护肤市场规模 2024",
  max_results=5
)
```

### 推荐参数
- `max_results`: 3-10（根据数据重要性调整）

---

## 📊 第2层：web_fetch

### 使用方法（示例）
```markdown
# 基础搜索
web_fetch(url="https://www.baidu.com/s?wd=中国护肤市场规模+2024")

# 站点限定
web_fetch(url="https://www.google.com/search?q=site:iresearch.cn+护肤市场")

# 搜索特定文件类型
web_fetch(url="https://www.google.com/search?q=护肤行业报告+filetype:pdf")

# 时间过滤（可选）
web_fetch(url="https://www.google.com/search?q=AI+news&tbs=qdr:w")
```

### 高级操作符（常用）
| 操作符 | 示例 | 说明 |
|--------|------|------|
| `site:` | `site:gov.cn 护肤` | 限定特定网站 |
| `filetype:` | `filetype:pdf 报告` | 搜索特定文件类型 |
| `""` | `"护肤品市场规模"` | 精确匹配短语 |

---

## 🔍 数据提取与验证

### 数据提取流程
1. 识别搜索结果中的关键数据
   - 定量数据：数值、单位、时间
   - 定性数据：观点、趋势、案例
2. 提取数据来源信息
   - 标题、URL、发布时间（如可得）
   - 来源类型（官网、报告、新闻）
3. 组织数据结构
   - 按章节分类
   - 按优先级排序
   - 标注数据类型

### 多源验证标准（建议）
- P0：至少 2 个独立来源
- P1：至少 2 个来源
- P2：至少 1 个来源

