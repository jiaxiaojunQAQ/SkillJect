# Changelog

All notable changes to Lucid will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [0.5.0] — 2026-03-27

### Fixed
- Portability fixes: removed hardcoded `/root/clawd` paths, fixed config loading in `trend_detection.py` to look relative to script dir first, fixed loop bug where `args.days` (could be None) was used instead of resolved `days` variable, cleared hardcoded telegram topic from default config

## [0.4.0] — 2026-03-25

### Added
- **Trend Detection** module (`scripts/trend_detection.py`) — analyzes patterns across 14 days of daily notes:
  - **Recurring Issues** — flags topics/problems appearing on 3+ separate days (e.g., "backup failed", "tailscale down")
  - **Stale Project Detection** — finds projects in MEMORY.md not mentioned in any daily note for 30+ days
  - **Escalated Patterns** — detects the same lesson/mistake appearing in 3+ daily notes (repeated mistakes not yet fixed)
- New `## Trends` section in nightly review output (`memory/review/YYYY-MM-DD.md`)
- Trend history tracking in `state.json` under `trends` key (accumulates across runs, keeps last 30 entries)
- Nightly review prompt updated with Step 7b to invoke trend detection script
- Example review and state files updated with trend output samples

### Technical Details
- Standalone Python script with no external dependencies (stdlib only)
- Uses difflib SequenceMatcher for fuzzy clustering of similar issues/lessons
- Configurable via CLI flags: `--days`, `--stale-days`, `--min-recurrence`

## [0.3.0] — 2026-03-21

### Added
- **Extended Auto-Apply categories** (5 new safe classes):
  - Infrastructure facts — cron IDs, script paths, service names, port assignments
  - Lessons Learned — purely factual technical lessons
  - Model Strategy — agent counts, new agent entries when fully documented
  - Closed Open Loops — remove resolved items with explicit closure signal on 2+ days
  - Stale project status — update planning/in-progress to live when URL + service confirmed
- **`config/auto-apply.md`** — configurable file to enable/disable auto-apply categories per project. Edit it to go conservative, aggressive, or anywhere in between.
- **Stricter confidence gate**: medium/low confidence items never auto-applied (only high)
- Prompt reads `config/auto-apply.md` at runtime if present (Step 4b)

## [0.2.0] — 2026-03-18

### Added
- **Auto-Apply** for high-confidence, low-risk suggestions:
  - Version numbers in skill/plugin tables
  - Stale Cron IDs where removal is documented
  - New project entries with complete details (2+ days mentioned)
- **Git integration**: auto-apply commits to local git with descriptive message (`dreamer: auto-apply — DESCRIPTION`)
- **Rollback**: `git revert <hash>` to undo any auto-applied change
- Review file now has `## ✅ Auto-Applied` section showing what was applied automatically

### Changed
- Review format updated: auto-applied changes shown separately from pending decisions
- State ledger: auto-applied suggestions tracked as `accepted` immediately

### Never Auto-Applied (by design)
- Belief Updates, Key Decisions, Family/personal facts
- Model Strategy preferences
- Anything with uncertainty

## [0.1.0] — 2026-03-16

### Added
- Initial release of Lucid V1
- Nightly review prompt with 6 analysis categories:
  - Candidate Updates, Open Loops, Blockers, Belief Updates, Stale Facts, Duplicate/Merge Suggestions
- Suggestion ledger (`state.json`) with status tracking (pending/accepted/rejected/deferred)
- Health sentinel (`.last-success` timestamp)
- Anti-circular reasoning rule (never reads own previous reviews)
- Decision policy with 2-day threshold, confidence labels, output cap
- Negative rules (no credentials, tokens, volatile URLs in memory)
- Memory class awareness (personal facts vs project state vs policies)
- Example review output and state ledger
- Full architecture documentation

### Design process
- Concept reviewed by 4 AI agents across 2 rounds:
  - Round 1: Codex (GPT-5.3) + Claude Code (Sonnet 4.6) — pragmatic + architectural feedback
  - Round 2: Codex (GPT-5.4) + Claude Code (Opus 4.6) — deeper failure mode analysis
- Key insights incorporated:
  - State ledger for idempotency (GPT-5.4)
  - Anti-circular reasoning (Opus)
  - Memory classes (GPT-5.4)
  - "Curator, not journalist" framing (GPT-5.4)
  - Drop morning send from V1 (both)
