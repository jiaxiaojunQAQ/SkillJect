#!/bin/bash
# 生成本技能「独立安装包」目录 deep-search-mpro-package/（不含 multi-search-engine、ddg-web-search）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/deep-search-mpro-package"
rm -rf "$OUT"
mkdir -p "$OUT"
rsync -a \
  --exclude 'multi-search-engine' \
  --exclude 'ddg-web-search' \
  --exclude 'temp' \
  --exclude 'deep-search-mpro-package' \
  --exclude '.git' \
  --exclude '.DS_Store' \
  --exclude '*.zip' \
  --exclude 'SKILL.md.backup' \
  --exclude 'SKILL_ANALYSIS_REPORT.md' \
  --exclude 'sk SECURITY_AUDIT_REPORT.md' \
  --exclude 'eval_review_deepsearch.html' \
  --exclude 'eval_set.json' \
  --exclude 'list.md' \
  --exclude 'model-index.md' \
  --exclude 'assets/html-template.html.backup' \
  --exclude 'assets/yonyou-network-competitive-analysis-20260318.html' \
  "$ROOT/" "$OUT/"
chmod +x "$OUT/scripts/check_dependencies.sh" 2>/dev/null || true
chmod +x "$OUT/scripts/build_skill_package.sh" 2>/dev/null || true
echo "Done: $OUT"
du -sh "$OUT"
