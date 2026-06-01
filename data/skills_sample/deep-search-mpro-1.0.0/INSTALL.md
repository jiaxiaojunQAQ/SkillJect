# deep-search-mpro 独立安装包

本目录为 **deep-search-mpro** 自有内容，**不包含** `multi-search-engine`、`ddg-web-search`（请单独安装为并列技能）。

## 目录说明

| 路径 | 说明 |
|------|------|
| `SKILL.md` | 技能主文件（必需） |
| `references/` | 领域框架、工作流、模型、技术说明 |
| `assets/` | HTML/Markdown 模板与样式 |
| `scripts/` | 辅助脚本（如 `check_dependencies.sh` 仅检测并列技能，不强制） |
| `evals/` | 可选回归用例 |
| `README.md` | 使用说明 |
| `打包说明.md` | 中文打包与安装参考（若随包提供） |

## 安装建议

1. 将本文件夹整体复制到宿主环境的技能目录，文件夹名建议为 **`deep-search-mpro`**。
2. 若需第 3～4 层增强检索，另安装 **`multi-search-engine`**、**`ddg-web-search`**，与本事放在**同一父目录**（兄弟文件夹）。
3. 运行 `scripts/check_dependencies.sh` 可查看并列技能是否已安装。
