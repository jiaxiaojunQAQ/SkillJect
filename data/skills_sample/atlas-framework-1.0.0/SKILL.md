---
name: atlas-framework
description: "ATLAS Framework - Structured AI-assisted development methodology with GOTCHA 6-layer architecture and 5-step app building workflow. Use when building applications, creating workflows, or setting up agentic systems."
---

# ATLAS Framework

A structured methodology for AI-assisted development built on the GOTCHA 6-layer architecture.

## When to Use This Skill

Use this skill when:
- Building full-stack applications
- Creating agentic workflows
- Setting up AI assistant frameworks
- Designing data systems or databases
- Planning integrations with external services

## The GOTCHA Framework (6 Layers)

**GOT (The Engine):**
- **Goals** (`goals/`) — What needs to happen (process definitions)
- **Orchestration** — The AI manager that coordinates execution
- **Tools** (`tools/`) — Deterministic scripts that do the actual work

**CHA (The Context):**
- **Context** (`context/`) — Reference material and domain knowledge
- **Hard prompts** (`hardprompts/`) — Reusable instruction templates
- **Args** (`args/`) — Behavior settings that shape how the system acts

### Why GOTCHA?

LLMs are probabilistic (educated guesses). Business logic is deterministic (must work the same way every time). This structure bridges that gap through **separation of concerns**:
- Push **reliability** into deterministic code (tools)
- Push **flexibility and reasoning** into the LLM (orchestration)
- Push **process clarity** into goals
- Push **behavior settings** into args files
- Push **domain knowledge** into context layer

---

## ATLAS Workflow (5 Steps)

Use this when building applications:

| Step | Phase | What You Do |
|------|-------|-------------|
| **A** | Architect | Define problem, users, success metrics |
| **T** | Trace | Data schema, integrations map, stack proposal |
| **L** | Link | Validate ALL connections before building |
| **A** | Assemble | Build with layered architecture |
| **S** | Stress-test | Test functionality, error handling |

For production builds, also add:
- **V** — Validate (security, input sanitization, edge cases, unit tests)
- **M** — Monitor (logging, observability, alerts)

### A — Architect

**Purpose:** Know exactly what you're building before touching code.

Answer these questions:
1. **What problem does this solve?** (One sentence)
2. **Who is this for?** (Specific user, not "everyone")
3. **What does success look like?** (Measurable outcome)
4. **What are the constraints?** (Budget, time, technical requirements)

### T — Trace

**Purpose:** Design before building.

1. **Data Schema** — Define source of truth BEFORE building
2. **Integrations Map** — List every external connection (service, purpose, auth type, MCP available?)
3. **Technology Stack** — Propose database, backend, frontend
4. **Edge Cases** — Document what could break (rate limits, token expiry, timeouts)

### L — Link

**Purpose:** Validate ALL connections BEFORE building.

```
[ ] Database connection tested
[ ] All API keys verified
[ ] MCP servers responding
[ ] OAuth flows working
[ ] Environment variables set
[ ] Rate limits understood
```

### A — Assemble

**Purpose:** Build with proper architecture.

Build order:
1. Database schema first
2. Backend API routes second
3. Frontend UI last

Follow GOTCHA separation:
- **Frontend** — UI components, user interactions
- **Backend** — API routes, business logic, validation
- **Database** — Schema, migrations, indexes

### S — Stress-test

**Purpose:** Test before shipping.

- **Functional Testing** — All buttons work, data saves/retrieves, navigation works
- **Integration Testing** — API calls succeed, MCP operations work, auth persists
- **Edge Case Testing** — Invalid input handled, empty states display, network errors show feedback

---

## File Structure

```
project/
├── goals/          — Process definitions (what to achieve)
├── tools/          — Execution scripts (organized by workflow)
├── args/           — Behavior settings (YAML/JSON)
├── context/        — Domain knowledge and references
├── hardprompts/    — Reusable instruction templates
├── memory/         — Persistent memory system
├── .tmp/           — Temporary work (disposable)
├── .env            — API keys + environment variables
└── CLAUDE.md       — System instruction file
```

---

## Memory System

The framework includes a persistent memory system for cross-session continuity.

### Loading Memory

At session start, load memory context:
- Read `memory/MEMORY.md` for curated long-term facts
- Read today's log: `memory/logs/YYYY-MM-DD.md`
- Read yesterday's log for continuity

### Memory Types
- `fact` — Objective information
- `preference` — User preferences  
- `event` — Something that happened
- `insight` — Learned pattern
- `task` — Something to do
- `relationship` — Connection between entities

### Search Capabilities
- Keyword search
- Semantic search
- Hybrid search (best results)

---

## Anti-Patterns (What NOT To Do)

1. **Building before designing** — End up rewriting everything
2. **Skipping connection validation** — Hours wasted on broken integrations
3. **No data modeling** — Schema changes cascade into UI rewrites
4. **No testing** — Ship broken code, lose trust
5. **Hardcoding everything** — No flexibility for changes

---

## Guardrails

- Always check `tools/manifest.md` before writing new scripts
- Verify tool output format before chaining into another tool
- Don't assume APIs support batch operations — check first
- When a workflow fails mid-execution, preserve intermediate outputs before retrying
- Read the full goal before starting a task — don't skim

---

## First Run Initialization

On first session in a new environment:

1. Check if `memory/MEMORY.md` exists
2. If missing, create the folder structure:
   - `memory/logs/`
   - `data/`
3. Create `MEMORY.md` with template
4. Initialize SQLite databases for memory and activity tracking

---

## Continuous Improvement Loop

Every failure strengthens the system:

1. Identify what broke and why
2. Fix the tool script
3. Test until it works reliably
4. Update the goal with new knowledge
5. Next time → automatic success
