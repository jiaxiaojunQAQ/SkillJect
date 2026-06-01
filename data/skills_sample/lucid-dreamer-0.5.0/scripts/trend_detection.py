#!/usr/bin/env python3
"""
Lucid Trend Detection — v0.4.0

Analyzes daily notes for recurring patterns, stale projects, and repeated mistakes.
Designed to be invoked by the nightly review prompt (or standalone).

Usage:
    python3 scripts/trend_detection.py --workspace /path/to/workspace [--memory MEMORY.md] [--days 14] [--state memory/review/state.json]

Output: Markdown trends section printed to stdout, state updates written to state.json.
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d")


def date_range(end: datetime, days: int):
    """Yield YYYY-MM-DD strings for the last *days* days ending at *end* (inclusive)."""
    for i in range(days):
        yield (end - timedelta(days=i)).strftime("%Y-%m-%d")


def read_file(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def normalise(text: str) -> str:
    """Lowercase, collapse whitespace."""
    return re.sub(r"\s+", " ", text.lower().strip())


# ---------------------------------------------------------------------------
# 1. Recurring Issues Detection
# ---------------------------------------------------------------------------

# Common issue-signal phrases (lowercase).  Extend as needed.
ISSUE_PATTERNS = [
    r"fail(?:ed|ure|s)?",
    r"error(?:s)?",
    r"broken",
    r"down",
    r"crash(?:ed|es)?",
    r"timeout(?:s)?",
    r"refused",
    r"stuck",
    r"bug(?:s)?",
    r"not working",
    r"issue(?:s)?",
    r"problem(?:s)?",
    r"missing",
    r"stale",
    r"disconnect(?:ed)?",
    r"unreachable",
    r"OOM|out of memory",
    r"permission denied",
    r"401|403|404|500|502|503",
]

# Compile a single big pattern.
_ISSUE_RE = re.compile(
    r"(?:^|\W)(" + "|".join(ISSUE_PATTERNS) + r")(?:\W|$)",
    re.IGNORECASE,
)


def _extract_issue_phrases(text: str, context_words: int = 4) -> list[str]:
    """Return short context snippets around issue-signal words.

    Works line-by-line to avoid cross-section contamination, and strips
    markdown headings / bullet markers for cleaner output.
    """
    phrases: list[str] = []
    for line in text.splitlines():
        # Skip headings and empty lines
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Remove bullet/list markers
        stripped = re.sub(r"^[-*•]\s+", "", stripped)
        words = stripped.split()
        for i, w in enumerate(words):
            if _ISSUE_RE.search(w) or _ISSUE_RE.search(" ".join(words[max(0, i - 1):i + 2])):
                start = max(0, i - context_words)
                end = min(len(words), i + context_words + 1)
                snippet = " ".join(words[start:end])
                phrases.append(normalise(snippet))
    return phrases


def _cluster_phrases(all_phrases: dict[str, list[str]], min_days: int = 3) -> list[dict]:
    """
    Cluster similar issue phrases across days.

    all_phrases: {date: [phrase, ...]}
    Returns list of {topic, days: [date, ...], count}.
    """
    # Simple approach: extract a 3-gram fingerprint from each phrase
    # and cluster by shared n-grams.
    from difflib import SequenceMatcher

    # Flatten into (date, phrase) pairs
    dated: list[tuple[str, str]] = []
    for d, phrases in all_phrases.items():
        for p in phrases:
            dated.append((d, p))

    if not dated:
        return []

    # Greedy clustering: for each phrase find existing cluster with similarity > 0.55
    clusters: list[dict] = []  # {rep: str, dates: set, phrases: list}
    for date, phrase in dated:
        best_idx = -1
        best_score = 0.0
        for idx, cl in enumerate(clusters):
            score = SequenceMatcher(None, phrase, cl["rep"]).ratio()
            if score > best_score:
                best_score = score
                best_idx = idx
        if best_score >= 0.55 and best_idx >= 0:
            clusters[best_idx]["dates"].add(date)
            clusters[best_idx]["phrases"].append(phrase)
        else:
            clusters.append({"rep": phrase, "dates": {date}, "phrases": [phrase]})

    # Filter to those appearing on min_days+ distinct days
    results = []
    for cl in clusters:
        if len(cl["dates"]) >= min_days:
            # Pick shortest phrase as representative topic label
            topic = min(cl["phrases"], key=len)
            # Trim to max 60 chars
            if len(topic) > 60:
                topic = topic[:57] + "..."
            results.append({
                "topic": topic,
                "days": sorted(cl["dates"]),
                "count": len(cl["dates"]),
            })
    # Sort by count desc
    results.sort(key=lambda r: r["count"], reverse=True)
    return results


def detect_recurring_issues(daily_notes: dict[str, str], min_days: int = 3) -> list[dict]:
    """
    Scan daily notes for recurring issue patterns.

    daily_notes: {date_str: file_content}
    Returns list of {topic, days, count}.
    """
    all_phrases: dict[str, list[str]] = {}
    for date, content in daily_notes.items():
        phrases = _extract_issue_phrases(content)
        if phrases:
            all_phrases[date] = phrases
    return _cluster_phrases(all_phrases, min_days=min_days)


# ---------------------------------------------------------------------------
# 2. Stale Project Detection
# ---------------------------------------------------------------------------

def _extract_projects_from_memory(memory_text: str) -> list[str]:
    """
    Extract project names from MEMORY.md.

    Heuristics:
    - Lines under ## Projects / ## Active Projects / ## Projekte headings
    - Table rows with project-like names
    - Bold items in list entries (- **ProjectName** ...)
    """
    projects: list[str] = []

    # Strategy 1: Bold list items under project-ish headings
    in_project_section = False
    for line in memory_text.splitlines():
        stripped = line.strip()
        if re.match(r"^#{1,3}\s.*(project|projekt|active|repo)", stripped, re.IGNORECASE):
            in_project_section = True
            continue
        if re.match(r"^#{1,3}\s", stripped) and in_project_section:
            in_project_section = False
            continue
        if in_project_section:
            # Bold items: - **name** or | name |
            m = re.match(r"[-*]\s+\*\*(.+?)\*\*", stripped)
            if m:
                projects.append(m.group(1).strip())
                continue
            # Table rows (skip header separators)
            if stripped.startswith("|") and "---" not in stripped:
                cells = [c.strip().strip("*").strip() for c in stripped.split("|") if c.strip()]
                if cells:
                    projects.append(cells[0])

    # Deduplicate, preserve order
    seen: set[str] = set()
    unique: list[str] = []
    for p in projects:
        key = p.lower()
        if key not in seen and len(p) > 1:
            seen.add(key)
            unique.append(p)
    return unique


def detect_stale_projects(
    memory_text: str,
    daily_notes: dict[str, str],
    stale_days: int = 30,
    today: datetime | None = None,
) -> list[dict]:
    """
    Find projects in MEMORY.md not mentioned in recent daily notes.

    Returns list of {project, last_mention, days_since}.
    """
    if today is None:
        today = datetime.now()

    projects = _extract_projects_from_memory(memory_text)
    if not projects:
        return []

    results: list[dict] = []
    for project in projects:
        pattern = re.compile(re.escape(project), re.IGNORECASE)
        last_mention: str | None = None
        for date in sorted(daily_notes.keys(), reverse=True):
            if pattern.search(daily_notes[date]):
                last_mention = date
                break

        if last_mention is None:
            # Never mentioned in scanned window — flag with unknown last mention
            results.append({
                "project": project,
                "last_mention": "unknown (not in scanned window)",
                "days_since": stale_days + 1,
            })
        else:
            days_since = (today - parse_date(last_mention)).days
            if days_since >= stale_days:
                results.append({
                    "project": project,
                    "last_mention": last_mention,
                    "days_since": days_since,
                })

    results.sort(key=lambda r: r["days_since"], reverse=True)
    return results


# ---------------------------------------------------------------------------
# 3. Repeated Mistakes / Escalated Patterns
# ---------------------------------------------------------------------------

def _extract_lessons(text: str) -> list[str]:
    """
    Extract lesson-learned entries from a daily note.

    Looks for:
    - Sections named "Lessons", "Lesson Learned", "Takeaway", "Gelernt"
    - Bullet items under those sections
    - Lines containing "lesson:", "takeaway:", "note to self"
    """
    lessons: list[str] = []
    in_lesson_section = False

    for line in text.splitlines():
        stripped = line.strip()

        # Check for lesson section headers
        if re.match(
            r"^#{1,4}\s.*(lesson|takeaway|gelernt|erkenntn|mistake|learning)",
            stripped,
            re.IGNORECASE,
        ):
            in_lesson_section = True
            continue
        if re.match(r"^#{1,4}\s", stripped) and in_lesson_section:
            in_lesson_section = False
            continue

        # Bullet items in lesson section
        if in_lesson_section and re.match(r"^[-*]\s", stripped):
            lessons.append(normalise(stripped.lstrip("-* ")))
            continue

        # Inline lesson markers anywhere
        m = re.match(
            r"^[-*]?\s*(?:lesson|takeaway|note to self|gelernt)\s*:\s*(.+)",
            stripped,
            re.IGNORECASE,
        )
        if m:
            lessons.append(normalise(m.group(1)))

    return lessons


def detect_repeated_mistakes(daily_notes: dict[str, str], min_days: int = 3) -> list[dict]:
    """
    Find the same lesson/mistake appearing across 3+ daily notes.

    Returns list of {pattern, days, count}.
    """
    from difflib import SequenceMatcher

    # Collect all (date, lesson) pairs
    dated_lessons: list[tuple[str, str]] = []
    for date, content in daily_notes.items():
        for lesson in _extract_lessons(content):
            dated_lessons.append((date, lesson))

    if not dated_lessons:
        return []

    # Cluster similar lessons
    clusters: list[dict] = []
    for date, lesson in dated_lessons:
        best_idx = -1
        best_score = 0.0
        for idx, cl in enumerate(clusters):
            score = SequenceMatcher(None, lesson, cl["rep"]).ratio()
            if score > best_score:
                best_score = score
                best_idx = idx
        if best_score >= 0.6 and best_idx >= 0:
            clusters[best_idx]["dates"].add(date)
            clusters[best_idx]["lessons"].append(lesson)
        else:
            clusters.append({"rep": lesson, "dates": {date}, "lessons": [lesson]})

    results = []
    for cl in clusters:
        if len(cl["dates"]) >= min_days:
            pattern = min(cl["lessons"], key=len)
            if len(pattern) > 80:
                pattern = pattern[:77] + "..."
            results.append({
                "pattern": pattern,
                "days": sorted(cl["dates"]),
                "count": len(cl["dates"]),
            })
    results.sort(key=lambda r: r["count"], reverse=True)
    return results


# ---------------------------------------------------------------------------
# Output Formatting
# ---------------------------------------------------------------------------

def format_trends_section(
    recurring: list[dict],
    stale: list[dict],
    escalated: list[dict],
) -> str:
    """Format all trend results as a Markdown section."""
    lines: list[str] = ["## Trends\n"]

    # Recurring Issues
    lines.append("### 🔁 Recurring Issues")
    if recurring:
        lines.append("_Same issue/topic flagged on 3+ separate days in the last 14 days._\n")
        for i, r in enumerate(recurring, 1):
            days_str = ", ".join(r["days"])
            lines.append(f"{i}. **{r['topic']}** — appeared on {r['count']} days ({days_str})")
    else:
        lines.append("_No recurring issues detected._")
    lines.append("")

    # Stale Projects
    lines.append("### 🕸️ Possibly Stale Projects")
    if stale:
        lines.append("_Projects in MEMORY.md not mentioned in any daily note for 30+ days._\n")
        for i, s in enumerate(stale, 1):
            lines.append(f"{i}. **{s['project']}** — last mentioned: {s['last_mention']} ({s['days_since']} days ago)")
    else:
        lines.append("_All tracked projects appear active._")
    lines.append("")

    # Escalated Patterns
    lines.append("### ⚠️ Escalated Patterns (Repeated Mistakes)")
    if escalated:
        lines.append("_Same lesson/mistake appearing in 3+ daily notes — pattern not yet broken._\n")
        for i, e in enumerate(escalated, 1):
            days_str = ", ".join(e["days"])
            lines.append(f"{i}. **{e['pattern']}** — repeated on {e['count']} days ({days_str})")
    else:
        lines.append("_No escalated patterns detected._")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# State Management
# ---------------------------------------------------------------------------

def update_state_trends(state_path: str, recurring: list, stale: list, escalated: list, today_str: str):
    """Merge trend data into state.json under a 'trends' key."""
    state: dict = {}
    if os.path.exists(state_path):
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)

    trends = state.get("trends", {
        "recurringIssues": [],
        "staleProjects": [],
        "escalatedPatterns": [],
        "history": [],
    })

    # Update current snapshot
    trends["recurringIssues"] = recurring
    trends["staleProjects"] = stale
    trends["escalatedPatterns"] = escalated

    # Append to history (keep last 30 entries)
    history = trends.get("history", [])
    history.append({
        "date": today_str,
        "recurringCount": len(recurring),
        "staleCount": len(stale),
        "escalatedCount": len(escalated),
    })
    trends["history"] = history[-30:]

    state["trends"] = trends
    state["lastTrendRun"] = today_str

    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_config(workspace: Path) -> dict:
    """Load lucid.config.json if it exists, return defaults otherwise."""
    script_dir = Path(__file__).resolve().parent.parent
    config_path = script_dir / "config" / "lucid.config.json"
    if not config_path.exists():
        config_path = workspace / "config" / "lucid.config.json"
    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def get_cfg(config: dict, *keys, default=None):
    """Safe nested config access."""
    val = config
    for k in keys:
        if not isinstance(val, dict):
            return default
        val = val.get(k, default)
    return val if val is not None else default


def main():
    parser = argparse.ArgumentParser(description="Lucid Trend Detection")
    parser.add_argument("--workspace", required=True, help="Path to agent workspace root")
    parser.add_argument("--memory", default="MEMORY.md", help="Relative path to MEMORY.md (from workspace)")
    parser.add_argument("--days", type=int, default=None, help="Number of days to scan (default: from config or 14)")
    parser.add_argument("--stale-days", type=int, default=None, help="Days before a project is flagged stale (default: from config or 30)")
    parser.add_argument("--min-recurrence", type=int, default=None, help="Min days for recurring issue (default: from config or 3)")
    parser.add_argument("--state", default="memory/review/state.json", help="Relative path to state.json")
    parser.add_argument("--date", default=None, help="Override today's date (YYYY-MM-DD)")
    parser.add_argument("--config", default=None, help="Path to lucid.config.json (default: auto-detect)")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    config = load_config(workspace)

    # Check if trends are enabled at all
    if not get_cfg(config, "trends", "enabled", default=True):
        print("## Trends\n\n_Trend detection disabled via config._")
        return

    # Apply config defaults (CLI args override config which overrides hardcoded defaults)
    days = args.days or get_cfg(config, "trends", "recurringIssues", "lookbackDays", default=14)
    stale_days = args.stale_days or get_cfg(config, "trends", "staleProjects", "staleAfterDays", default=30)
    min_recurrence = args.min_recurrence or get_cfg(config, "trends", "recurringIssues", "minOccurrences", default=3)

    # Per-detector enable flags
    recurring_enabled = get_cfg(config, "trends", "recurringIssues", "enabled", default=True)
    stale_enabled = get_cfg(config, "trends", "staleProjects", "enabled", default=True)
    escalated_enabled = get_cfg(config, "trends", "escalatedPatterns", "enabled", default=True)

    today = parse_date(args.date) if args.date else datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    # Read daily notes
    daily_notes: dict[str, str] = {}
    for date_str in date_range(today, days):
        content = read_file(workspace / "memory" / f"{date_str}.md")
        if content:
            daily_notes[date_str] = content

    if not daily_notes:
        print("## Trends\n\n_No daily notes found for the last {} days. Skipping trend analysis._".format(days))
        return

    # Read MEMORY.md
    memory_text = read_file(workspace / args.memory) or ""

    # Run detections (respects per-detector config)
    recurring = detect_recurring_issues(daily_notes, min_days=min_recurrence) if recurring_enabled else []
    stale = detect_stale_projects(memory_text, daily_notes, stale_days=stale_days, today=today) if stale_enabled else []
    escalated = detect_repeated_mistakes(daily_notes, min_days=min_recurrence) if escalated_enabled else []

    # Output markdown
    print(format_trends_section(recurring, stale, escalated))

    # Update state
    state_path = str(workspace / args.state)
    try:
        update_state_trends(state_path, recurring, stale, escalated, today_str)
        print(f"<!-- trend data written to {args.state} -->", file=sys.stderr)
    except Exception as e:
        print(f"<!-- warning: could not update state.json: {e} -->", file=sys.stderr)


if __name__ == "__main__":
    main()
