---
name: api-compat
description: "Change public APIs without breaking clients—versioning schemes, additive vs breaking changes, deprecation windows, and comms. Use when shipping breaking changes, sunsetting fields, or coordinating mobile/web SDK consumers."
---

# API Compatibility

Own the **lifecycle** of a public API: who breaks when you ship, how long old behavior lives, and how clients discover what’s next. Pair with **http-api** for how requests look **today**; this skill is about **time and promises**.

## When to use

- Adding/removing fields, routes, or semantics that **existing** clients rely on.
- Choosing **URL vs header vs package** versioning—or when **no** formal version and only additive JSON.
- **Deprecation**: timelines, metrics (who still calls old paths?), and removal gates.

## Core ideas

- **Additive first** — nullable new fields beat silent behavior changes.
- **Explicit contracts** — integration tests or consumer-driven checks for critical partners.
- **Communicate** — changelog, developer email, in-response **Sunset** / warnings where standards allow.

## Avoid

- “We’ll just bump the version” without a **migration** story for slow-moving apps.
- Breaking auth or pagination with no **coordination** window.
- Deprecating without **usage data**—you’ll cut traffic you didn’t know existed.

## Checklist before breaking

- [ ] Who is affected (internal only vs third parties)?
- [ ] Minimum notice period and **rollback** if telemetry spikes errors?
- [ ] Docs + examples updated **before** the flag day?

## Done when

- Old and new behaviors are **measurable**; removal is gated on **evidence**, not hope.
