---
name: eeat-content-quality-audit
description: Systematic content quality audit based on 80 CORE-EEAT standards, evaluating content's GEO (Generative Engine Optimization) and SEO (Search Engine Optimization) potential. Features 8-dimension scoring, weighted total calculation, veto item detection, and priority improvement recommendations. Applicable for pre-publication checks, competitive analysis, and AI citation potential assessment.
---

# EEAT Content Quality Audit

> This skill is developed based on the CORE-EEAT Content Benchmark, providing 80 standardized content quality audit criteria.

## Skill Overview

This skill evaluates content quality through 80 standardized criteria across 8 core dimensions. It generates comprehensive audit reports including item-level scores, dimension scores, system scores (GEO/SEO), content-type weighted total scores, veto item detection, and priority action plans.

## Applicable Scenarios

Use this skill when users request the following:

- Content quality check or audit
- EEAT scoring or E-E-A-T audit
- Content quality assessment
- CORE-EEAT audit
- GEO quality scoring
- Content improvement recommendations
- AI citation potential assessment
- Content optimization plan
- "How good is my content"
- "Can my content be cited by AI"

## Core Capabilities

This skill can:

1. **Complete 80-Item Audit**: Score each CORE-EEAT item as Pass/Partial/Fail
2. **Dimension Scoring**: Calculate scores for all 8 dimensions (0-100 points each)
3. **System Scoring**: Calculate GEO score (CORE) and SEO score (EEAT)
4. **Weighted Total Score**: Calculate final score based on content-type specific weights
5. **Veto Item Detection**: Flag critical credibility violations (T04, C01, R10)
6. **Priority Ranking**: Identify top 5 improvement recommendations by impact
7. **Action Plan**: Generate specific, actionable improvement steps

## Content Types

This skill supports the following content types, each with different dimension weights:

- Product Review
- How-To Guide
- Comparison Review
- Landing Page
- Blog Post
- FAQ
- Alternative Recommendation
- Best Recommendation
- User Review

## Usage

### Basic Audit

```
Please audit the quality of the following content: [Content text or URL]
```

```
Perform content quality audit on [URL]
```

### Specify Content Type

```
Audit this content as a product review: [Content]
```

```
Score this tutorial based on 80 criteria: [Content]
```

### Comparison Audit

```
Audit the differences between my content and competitor's: [Your content] vs [Competitor content]
```

## Data Input Requirements

**Manual Data Input** (Currently recommended):

Request users to provide:
1. Content text, URL, or file path
2. Content type (if cannot auto-detect): Product Review, How-To Guide, Comparison Review, Landing Page, Blog Post, FAQ, Alternative Recommendation, Best Recommendation, User Review
3. Optional: Competitor content for comparative assessment

**Note**: Explicitly mark in the output which items cannot be fully evaluated due to lack of access (e.g., backlink data, Schema markup, site-level signals).

## Execution Steps

When users request content quality audit, follow these steps:

### Step 1: Audit Preparation

```markdown
### Audit Preparation

**Content**: [Title or URL]
**Content Type**: [Auto-detected or user-specified]
**Dimension Weights**: [Load from content type weight table]

#### Veto Item Check (Emergency Brake)

| Veto Item | Status | Action |
|-----------|--------|--------|
| T04: Disclosure Statement | ✅ Pass / ⚠️ Triggered | [If triggered: "Immediately add disclosure banner at top of page"] |
| C01: Intent Alignment | ✅ Pass / ⚠️ Triggered | [If triggered: "Rewrite title and first paragraph"] |
| R10: Content Consistency | ✅ Pass / ⚠️ Triggered | [If triggered: "Verify all data before publication"] |
```

If any veto item is triggered, prominently mark it at the top of the report and recommend immediate action before continuing with the full audit.

### Step 2: CORE Audit (40 Items)

Evaluate each item according to standards in references/core-eeat-benchmark.md.

Score each item:
- **Pass** = 10 points (Fully meets standard)
- **Partial** = 5 points (Partially meets standard)
- **Fail** = 0 points (Does not meet standard)

```markdown
### C — Contextual Clarity

| ID | Check Item | Score | Notes |
|----|------------|-------|-------|
| C01 | Intent Alignment | Pass/Partial/Fail | [Specific observation] |
| C02 | Direct Answer | Pass/Partial/Fail | [Specific observation] |
| ... | ... | ... | ... |
| C10 | Semantic Closure | Pass/Partial/Fail | [Specific observation] |

**C Dimension Score**: [X]/100
```

Evaluate **O** (Organization), **R** (Referenceability), and **E** (Exclusivity) in the same table format, 10 items per dimension.

### Step 3: EEAT Audit (40 Items)

```markdown
### Exp — Experience

| ID | Check Item | Score | Notes |
|----|------------|-------|-------|
| Exp01 | First-Person Narrative | Pass/Partial/Fail | [Specific observation] |
| ... | ... | ... | ... |

**Exp Dimension Score**: [X]/100
```

Evaluate **Ept** (Expertise), **A** (Authority), and **T** (Trust) in the same table format, 10 items per dimension.

For detailed 80-item ID lookup table and site-level item handling instructions, see references/item-reference.md.

### Step 4: Scoring and Reporting

Calculate scores and generate final report:

```markdown
## CORE-EEAT Audit Report

### Overview

- **Content**: [Title]
- **Content Type**: [Type]
- **Audit Date**: [Date]
- **Total Score**: [Score]/100 ([Rating])
- **GEO Score**: [Score]/100 | **SEO Score**: [Score]/100
- **Veto Item Status**: ✅ No triggers / ⚠️ [Item] triggered

### Dimension Scores

| Dimension | Score | Rating | Weight | Weighted Score |
|-----------|-------|--------|--------|----------------|
| C — Contextual Clarity | [X]/100 | [Rating] | [X]% | [X] |
| O — Organization | [X]/100 | [Rating] | [X]% | [X] |
| R — Referenceability | [X]/100 | [Rating] | [X]% | [X] |
| E — Exclusivity | [X]/100 | [Rating] | [X]% | [X] |
| Exp — Experience | [X]/100 | [Rating] | [X]% | [X] |
| Ept — Expertise | [X]/100 | [Rating] | [X]% | [X] |
| A — Authority | [X]/100 | [Rating] | [X]% | [X] |
| T — Trust | [X]/100 | [Rating] | [X]% | [X] |
| **Weighted Total Score** | | | | **[X]/100** |

**Score Calculation Formulas**:
- GEO Score = (C + O + R + E) / 4
- SEO Score = (Exp + Ept + A + T) / 4
- Weighted Score = Σ (Dimension Score × Content Type Weight)

**Rating Standards**: 90-100 Excellent | 75-89 Good | 60-74 Fair | 40-59 Poor | 0-39 Very Poor

### Unavailable Item Handling

When an item cannot be evaluated (e.g., A01 backlink profile requires site-level data, inaccessible):

1. Mark the item as "N/A" and note the reason
2. Exclude N/A items from dimension score calculation
3. Dimension Score = (Sum of scored items) / (Number of scored items × 10) × 100
4. If a dimension has >50% items as N/A, mark that dimension as "Insufficient Data" and exclude from weighted total score
5. Recalculate weighted total score using only dimensions with sufficient data, renormalizing weights to total 100%

**Example**: Authority dimension has 8 N/A items and 2 scored items (A05=8, A07=5):
- Dimension Score = (8+5) / (2 × 10) × 100 = 65
- But 8/10 items are N/A (>50%), so mark as "Insufficient Data -- Authority"
- Exclude A dimension from weighted total; redistribute its weight proportionally to remaining dimensions

### Item-Level Scores

#### CORE — Content Body (40 Items)

| ID | Check Item | Score | Notes |
|----|------------|-------|-------|
| C01 | Intent Alignment | [Pass/Partial/Fail] | [Observation] |
| C02 | Direct Answer | [Pass/Partial/Fail] | [Observation] |
| ... | ... | ... | ... |

#### EEAT — Source Credibility (40 Items)

| ID | Check Item | Score | Notes |
|----|------------|-------|-------|
| Exp01 | First-Person Narrative | [Pass/Partial/Fail] | [Observation] |
| ... | ... | ... | ... |

### Top 5 Priority Improvements

Sorted by: Weight × Points Lost (by impact from high to low)

1. **[ID] [Name]** — [Specific improvement suggestion]
   - Current Status: [Fail/Partial] | Potential Gain: [X] weighted points
   - Action: [Specific steps]

2. **[ID] [Name]** — [Specific improvement suggestion]
   - Current Status: [Fail/Partial] | Potential Gain: [X] weighted points
   - Action: [Specific steps]

3–5. [Same format]

### Action Plan

#### Quick Wins (Less than 30 minutes each)
- [ ] [Action 1]
- [ ] [Action 2]

#### Medium Investment (1-2 hours)
- [ ] [Action 3]
- [ ] [Action 4]

#### Strategic (Requires Planning)
- [ ] [Action 5]
- [ ] [Action 6]

### Recommended Next Steps

- Complete content rewrite: Rewrite with CORE-EEAT constraints
- GEO optimization: Optimize for failed GEO-First items
- Content refresh: Focus on weak dimensions
- Technical fixes: Check site-level issues
```

## Validation Checkpoints

### Input Validation
- [ ] Content source identified (text, URL, or file path)
- [ ] Content type confirmed (auto-detected or user-specified)
- [ ] Content sufficient for meaningful audit (≥300 words)
- [ ] If comparative audit, competitor content also provided

### Output Validation
- [ ] All 80 items scored (or marked N/A with reason)
- [ ] All 8 dimension scores calculated correctly
- [ ] Weighted total score matches content type weight configuration
- [ ] Veto items checked and marked if triggered
- [ ] Top 5 improvements sorted by weighted impact, not arbitrary order
- [ ] Each recommendation specific and actionable (not generic)
- [ ] Action plan includes specific steps and investment estimates

## Success Points

1. **Start with Veto Items** — T04, C01, R10 are one-vote veto items; they affect overall evaluation regardless of total score

2. **Focus on High-Weight Dimensions** — Different content types prioritize different dimensions

3. **GEO-First Items are Critical for AI Visibility** — If goal is AI citation, prioritize items marked with GEO 🎯

4. **Some EEAT Items Require Site-Level Data** — Don't penalize content for things only observable at site level (backlinks, brand recognition)

5. **Use Weighted Scores, Not Just Raw Averages** — Product reviews with strong exclusivity are more important than strong authority

6. **Re-Audit After Improvements** — Run again to verify score improvements and catch regressions

## Terminology

### CORE (Content Quality)
- **C (Contextual Clarity)**: Contextual Clarity — Whether content is clear, accurate, and directly answers user questions
- **O (Organization)**: Organization — Whether content has good structure, hierarchy, and navigation
- **R (Referenceability)**: Referenceability — Whether content has sufficient data, evidence, and citations
- **E (Exclusivity)**: Exclusivity — Whether content offers unique insights, data, and perspectives

### EEAT (Source Credibility)
- **Exp (Experience)**: Experience — Whether author demonstrates actual usage experience
- **Ept (Expertise)**: Expertise — Whether author demonstrates professional knowledge and skills
- **A (Authority)**: Authority — Whether content source possesses authority and industry status
- **T (Trust)**: Trust — Whether content is trustworthy

### GEO (Generative Engine Optimization)
- Content optimization for AI search engines (e.g., Google SGE, Bing Chat)
- Emphasizes direct answer capability, referenceability, and exclusivity

## Reference Documents

- references/core-eeat-benchmark.md — Complete 80-item benchmark with dimension definitions, scoring standards, and GEO-First item markers
- references/item-reference.md — Compact lookup table for all 80 item IDs + site-level item handling instructions + sample scored report

## Notes

- Read reference documents only when needed to maintain context conciseness
- When operations are fragile or require strong consistency, prioritize script execution with result validation
- Fully leverage the agent's language understanding and generation capabilities; avoid writing scripts for simple tasks
- This skill primarily serves Chinese users but retains industry terminology (CORE, EEAT, GEO) for alignment with international standards
