# 通用搜索使用指南

本技能的数据采集仅依赖 Agent 内置的 `web_search` 与 `web_fetch`。
无需 API key；建议为每次检索设置合理的数量/字数上限，以控制 Token 与访问范围。

---

## 1. 参数控制

### `web_search`
用于快速获取基础线索。
- `query`: 检索关键词（中英文均可）
- `max_results`: 返回条目数量（建议 3-10）

示例：
```markdown
web_search(
  query="your topic keywords",
  max_results=5
)
```

### `web_fetch`
用于抓取指定 URL 的页面内容（或搜索结果页面）并提取关键片段。
- `url`: 目标 URL（可以包含你需要的关键词/运算符）
- `extractMode`: 建议 `"text"`（非 markdown），便于抽取长文本
- `maxChars`: 限制抓取/提取的最大字符数（建议 5000-10000）

示例：
```markdown
web_fetch(
  url="https://example.com/search?q=your+keywords",
  extractMode="text",
  maxChars=8000
)
```

---

## 2. 常用检索“运算符”（写法示例）

不同站点/搜索入口的支持程度可能不同，但一般可以用以下思路构造 URL 或查询条件：
- `site:`：限定到某个站点/域名
  - 示例：`site:example.com your keywords`
- `filetype:`：限定文件类型（如报告/论文的 PDF）
  - 示例：`filetype:pdf your keywords`
- 时间过滤：用对应参数限定时间窗
  - 示例：`...&tbs=qdr:w`（以站点实际参数为准）

说明：以上仅作“构造关键词”的示例；具体参数请以你使用的站点实际支持为准。

---

## 3. 失败与降级

当抓取结果为空、超时或内容被拦截时：
1. 调整 `query`（缩小范围/换同义词/加时间限定）
2. 调整 `url`（换站点限定 `site:` 或文件类型 `filetype:`）
3. 如果仍无法获得足够证据，明确标注“数据暂不可得”，并说明会影响报告的哪些结论。

---

## 4. 数据提取与验证建议

- 对 P0/P1 关键指标至少准备 2 个独立来源（同一来源的转引不计入“独立”）
- 保留 `title/URL/发布时间（如可得）`，用于报告中的可追溯引用
- 重要结论与关键数字必须能回到抓取页面内容（避免凭空编造）

