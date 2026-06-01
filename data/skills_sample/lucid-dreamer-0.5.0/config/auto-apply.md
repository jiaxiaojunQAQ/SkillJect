# Auto-Apply Configuration

This file defines which categories Lucid is allowed to auto-apply without human review.

Only changes with **HIGH confidence** are ever auto-applied — regardless of category.
Medium and low confidence always require human approval.

## ✅ Enabled Categories

Edit this list to match your project's needs.

### Safe (factual, no opinions)
- **Version numbers** — skill/plugin tables clearly outdated
- **Stale Cron IDs** — cron was explicitly removed/replaced in notes
- **Service/port deletions** — clearly documented as removed
- **New project entries** — complete details (URL, repo, path, service) mentioned on 2+ days
- **Infrastructure facts** — new cron IDs, script paths, service names, port assignments
- **Lessons Learned** — purely factual technical lessons (not preferences or opinions)
- **Model Strategy** — agent counts, new agent entries when clearly documented with model + alias
- **Closed Open Loops** — remove resolved items when explicit closure signal exists on 2+ days
- **Stale project status** — update "planning"/"in progress" to "live" when URL + service confirmed on 2+ days

## ❌ Never Auto-Apply (hardcoded)

These are always manual regardless of confidence:

- Belief Updates (opinions, model preferences, strategy changes)
- Key Decisions
- Family/personal facts
- User preferences or communication style
- Anything you are uncertain about
- Anything with medium or low confidence

## Customization Examples

**Minimal setup** (only version numbers + new projects):
Remove all categories except "Version numbers" and "New project entries".

**Aggressive setup** (trust the AI more):
Add "Open Loops closure" and "Stale project status" — but watch for false positives.

**Conservative setup** (human reviews everything):
Remove all categories. Lucid will still generate suggestions but never apply them.
