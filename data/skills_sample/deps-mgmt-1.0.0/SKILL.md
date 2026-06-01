---
name: deps-mgmt
description: Deep dependency management workflow—inventory, upgrade policy, security patches, licensing, lockfiles, and supply-chain hygiene. Use when upgrading frameworks, resolving CVEs, or standardizing how teams pin dependencies.
---

# Dependencies

Dependencies are **supply-chain** surface area: versions affect security, reproducibility, and upgrade cost.

## When to Offer This Workflow

**Trigger conditions:**

- Dependabot noise; major version upgrades
- CVE response or license audit
- “Works on my machine” due to unpinned dependencies

**Initial offer:**

Use **six stages**: (1) inventory & risk, (2) policy & cadence, (3) lockfiles & reproducibility, (4) upgrades & testing, (5) security & licensing, (6) governance & tooling). Confirm ecosystem (npm, pip, Maven, Go modules, etc.).

---

## Stage 1: Inventory & Risk

**Goal:** Direct vs transitive dependencies; flag critical packages (crypto, auth, parsing, serialization).

**Exit condition:** SBOM or export for top applications; list of critical deps.

---

## Stage 2: Policy & Cadence

**Goal:** When to upgrade (time-based vs on-demand); SemVer rules for libraries vs applications.

---

## Stage 3: Lockfiles & Reproducibility

**Goal:** Committed lockfiles for deployable apps; libraries test against a compatibility matrix instead of one frozen lock.

---

## Stage 4: Upgrades & Testing

**Goal:** Prefer one major bump per PR when feasible; CI matrix on supported language/runtime versions.

---

## Stage 5: Security & Licensing

**Goal:** SCA scanning; patch SLA by severity; license allowlist for compliance.

---

## Stage 6: Governance & Tooling

**Goal:** Renovate/Bot policies; pin internal packages; document exceptions and overrides.

---

## Final Review Checklist

- [ ] Inventory and risk hotspots known
- [ ] Upgrade cadence and semver policy documented
- [ ] Lockfiles or matrix strategy per repo type
- [ ] CI validates upgrades
- [ ] SCA and license policy enforced

## Tips for Effective Guidance

- Transitive CVEs may need overrides—trace the dependency graph.
- Pin CI images and toolchains, not only application dependencies.

## Handling Deviations

- Monorepos: shared versions with Nx/Bazel/etc.—coordinate breaking upgrades.
