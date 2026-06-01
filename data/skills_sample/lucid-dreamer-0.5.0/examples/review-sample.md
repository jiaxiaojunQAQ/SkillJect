# Memory Review — 2026-03-16

## Candidate Updates

### 1. Hermes Agent — New Infrastructure (high confidence)
- **Add to Projects section:** `hermes-node` container (Tailscale `100.119.98.35`) running Hermes agent with GPT-5.4 via Codex OAuth, systemd service `hermes-gateway.service`, Telegram bot `8112006356:...`, mem0 Vector-DB memory
- **Source:** `memory/2026-03-15.md` (Hermes Agent Setup) + `memory/2026-03-13.md` (initial install)
- **Context:** Replaces rustyHermes (deleted 2026-03-13), NanoCami vs Hermes decision pending as of 2026-03-15

### 2. hermes-webchat Project (medium confidence)
- **Add to Projects section:** `hermes-webchat` — Next.js 15 + FastAPI mock backend, repo `robbyczgw-cla/hermes-webchat`, deployed on hermes-node ports 8444/8445 (currently disabled), **no real Hermes agent connected yet**
- **Source:** `memory/2026-03-16.md` (hermes-webchat Projekt section)

### 3. Morning Briefing Model — Pending Change (medium confidence)
- **Update Model Strategy table:** `Morning Briefing` row — currently shows Kimi, but 2026-03-14 benchmarks found Sonnet wins. Pending Robby decision.
- **Source:** `memory/2026-03-14.md` (~"Morning Briefing Modell" section)

### 4. Backup System Overhaul (high confidence)
- **Update MEMORY.md:** Add note that `/root/scripts/backup-storagebox.sh` was rewritten 2026-03-15 to use native `openclaw backup create`. Old clawd-workspace + openclaw-config separate approach replaced.
- **Source:** `memory/2026-03-15.md` (Backup System section)

### 5. web-search-plus Skills Version Mismatch (medium confidence)
- **MEMORY.md Published Skills table** shows `web-search-plus 2.7.2` but notes show it was bumped to 2.9.0 (2026-03-12) and the plugin to 1.2.2 (2026-03-11). Table is stale.
- **Source:** `memory/2026-03-12.md` (web-search-plus v2.9.0) + `memory/2026-03-11.md` (plugin v1.2.2)

### 6. QUERIT_API_KEY TODO (low confidence)
- **Lessons Learned / Operational:** `QUERIT_API_KEY` still missing from `/root/clawd/skills/web-search-plus/config.json` — noted as TODO since 2026-03-12. Worth adding as a formal TODO or note.
- **Source:** `memory/2026-03-12.md` (web-search-plus v2.9.0 section, end)

---

## Open Loops

### 1. NanoCami vs Hermes Decision
- **Started:** 2026-03-15 — Plan was "test Hermes this week → if stable, shut down NanoCami"
- **Missing:** No closure signal. NanoCami still running (6€/mo). Hermes tested on 2026-03-15/16 but decision not final.
- **Source:** `memory/2026-03-15.md` ("Entscheidung: NanoCami vs Hermes")

### 2. hermes-webchat — Real Agent Integration
- **Started:** 2026-03-16 — Mock backend only, no real Hermes agent connected
- **Missing:** Actual integration + UI polish ("sloppy" per Robby)
- **Source:** `memory/2026-03-16.md` ("Nächste Schritte")

### 3. Skill Selection — Life OS / GitClaw / others
- **Started:** 2026-03-12 brainstorm → carried through 2026-03-15/16
- **Missing:** No decision made after 4+ days of discussion
- **Source:** `memory/2026-03-16.md` (Skill-Ideen section) + `memory/2026-03-15.md` (Opus top 3)

### 4. X/Twitter Login on browser-node
- **Started:** 2026-03-14 — Manual login via noVNC needed, bot-detection blocks automated
- **Missing:** Still not logged in as of 2026-03-15
- **Source:** `memory/2026-03-15.md` + `memory/2026-03-14.md`

### 5. awesome-mcp-servers PR #3156
- **Started:** 2026-03-13 — Submitted, waiting on merge after AAA score (2026-03-14)
- **Missing:** No confirmation of merge
- **Source:** `memory/2026-03-14.md` (web-search-plus-mcp section)

### 6. Morning Briefing Model Switch (Kimi → Sonnet)
- **Started:** 2026-03-14 — Sonnet identified as winner but not yet changed
- **Missing:** Config update never happened; explicit decision pending
- **Source:** `memory/2026-03-14.md` (Morning Briefing Modell section)

### 7. agent-chronicle 0.6.2 → ClawHub publish
- **Started:** 2026-03-10 (Open TODOs) — local ahead of ClawHub 0.6.0
- **Missing:** Still listed as TODO across 6+ days with no resolution
- **Source:** `memory/2026-03-10.md` + `memory/2026-03-12.md`

### 8. personas --force update to 2.2.6
- **Started:** 2026-03-10 — local 2.2.4, ClawHub 2.2.6
- **Missing:** Never resolved despite appearing in every TODO list
- **Source:** `memory/2026-03-10.md` through `memory/2026-03-12.md`

### 9. TextCortex Follow-up (Jay / Ceyhun)
- **Started:** 2026-03-09 email sent, reminder cron set for 2026-03-16 09:00
- **Missing:** As of 2026-03-15, no reply yet. Today (2026-03-16) is the follow-up date — status unknown.
- **Source:** `memory/2026-03-14.md` + `memory/2026-03-15.md` (MEMORY.md TextCortex section)

### 10. Gigabrain Fork Decision
- **Started:** 2026-03-12 — "Tomorrow decide if we start"
- **Missing:** No decision noted in 2026-03-13/14/15/16 notes
- **Source:** `memory/2026-03-12.md` (Memory System Research section)

---

## Blockers

### 1. hermes-webchat UI quality ("sloppy")
- Robby explicitly noted the UI is still "sloppy" after two code passes (Opus + Codex)
- Mentioned on 2026-03-16 with no resolution in same session
- **Source:** `memory/2026-03-16.md`

### 2. Persistent low-priority TODOs (personas, agent-chronicle)
- `personas --force update to 2.2.6` and `publish agent-chronicle 0.6.2` appear in every single daily note from 2026-03-10 through 2026-03-16 (7 days) — never acted on
- Both are trivial 5-minute tasks that keep getting deprioritized
- **Source:** `memory/2026-03-10.md`, `2026-03-12.md`, `2026-03-14.md`, `2026-03-15.md`

---

## Belief Updates

### 1. Browser Tool Default Changed
- **Previously (2026-03-11):** `browser` tool used `profile: "browserless"` as explicit default
- **Now (2026-03-14+):** `browser-node` (ThinkCentre LXC container) is the new default — no profile parameter needed
- AGENTS.md was updated; MEMORY.md references are consistent with this
- **Source:** `memory/2026-03-14.md` (Infrastructure Notes) + `memory/2026-03-11.md`

### 2. OpenFang / rustyHermes Server — Deleted
- **Previously:** Multiple references to `100.114.73.25` / `openfang.tail8a9ea9.ts.net` / `rustyhermes.tail8a9ea9.ts.net` as experimental servers
- **Now:** Deleted by Robby 2026-03-13 — no active server at that IP
- MEMORY.md appears clean of these references already
- **Source:** `memory/2026-03-13.md` (end: "Rusty/Hermes/rustyHermes — GELÖSCHT")

### 3. Anna.partners — Evaluierung abgebrochen
- **Previously (2026-03-10/15):** Anna agent being tested, credits received
- **Now (2026-03-15):** Deinstalled, NATS Disconnect problem, decided not for us
- MEMORY.md doesn't mention Anna at all — no update needed
- **Source:** `memory/2026-03-15.md` (Anna.partners section)

---

## Stale Facts

### 1. MEMORY.md Model Strategy Table — Morning Briefing
- Table shows `Morning Briefing → Kimi`
- 2026-03-14 benchmarks clearly show Sonnet wins Morning Briefing
- However: decision to switch is explicitly "TODO/pending" → confidence medium (don't change until Robby decides)
- **Source:** MEMORY.md "Model Strategy" section vs `memory/2026-03-14.md`

### 2. MEMORY.md Published Skills Table — Versions
- `web-search-plus 2.7.2` is stale → actually 2.9.0 (since 2026-03-12)
- `web-search-plus-plugin 1.0.1` stale → actually 1.2.2 (since 2026-03-11)
- These are high-confidence staleness findings
- **Source:** `memory/2026-03-12.md` + `memory/2026-03-11.md`

### 3. TextCortex Reminder Cron — One-shot, likely fired
- MEMORY.md still shows: "Reminder Cron: gesetzt für 2026-03-16 09:00 Wien (ID: `b40d8516`)"
- Today is 2026-03-16 — this cron has already fired (or was due to). Should be removed from MEMORY.md once TextCortex loop closes.
- **Source:** MEMORY.md TextCortex section + `memory/2026-03-14.md`

---

## Trends

### 🔁 Recurring Issues
_Same issue/topic flagged on 3+ separate days in the last 14 days._

1. **tailscale down / disconnect** — appeared on 4 days (2026-03-10, 2026-03-12, 2026-03-14, 2026-03-15)
2. **personas --force update pending** — appeared on 7 days (2026-03-10, 2026-03-11, 2026-03-12, 2026-03-13, 2026-03-14, 2026-03-15, 2026-03-16)

### 🕸️ Possibly Stale Projects
_Projects in MEMORY.md not mentioned in any daily note for 30+ days._

_All tracked projects appear active._

### ⚠️ Escalated Patterns (Repeated Mistakes)
_Same lesson/mistake appearing in 3+ daily notes — pattern not yet broken._

_No escalated patterns detected._

---

## Duplicate/Merge Suggestions

### 1. Hermes Agent — Scattered Across Notes
- Hermes setup info appears across 2026-03-13, 2026-03-15 daily notes
- No single coherent MEMORY.md entry exists yet for `hermes-node` container
- Suggest adding a consolidated "NanoCami / Hermes" section to MEMORY.md (similar to existing NanoCami section)
- **Source:** `memory/2026-03-13.md` + `memory/2026-03-15.md`

### 2. NanoCami section in MEMORY.md — Merge with Hermes when decided
- Current NanoCami section is standalone; once NanoCami vs Hermes decision is made, these should be consolidated
- Low urgency until decision is final
- **Source:** MEMORY.md "NanoCami (NanoBot)" section
