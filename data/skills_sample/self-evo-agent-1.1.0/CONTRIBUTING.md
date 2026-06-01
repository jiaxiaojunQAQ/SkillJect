# Contributing

Thanks for contributing to `self-evolving-agent`.

## Principles

- Keep the skill clearly stronger than passive self-improvement systems.
- Prefer concrete workflow improvements over abstract theory.
- Preserve the memory layer while strengthening capability evolution.
- Treat benchmark quality as part of the product, not as an afterthought.

## Branch Convention

The default branch is `main`. Please branch from `main` and target `main` in pull requests.

## Development Setup

```bash
git clone https://github.com/RangeKing/self-evolving-agent.git
cd self-evolving-agent
python3 scripts/run-evals.py .
./scripts/bootstrap-workspace.sh /tmp/self-evolving-agent-dev --force
```

Optional model-in-the-loop smoke test:

```bash
python3 scripts/run-benchmark.py \
  --skill-dir . \
  --candidate-model gpt-5.4-mini \
  --judge-model gpt-5.4-mini \
  --max-scenarios 1 \
  --timeout-seconds 90
```

## What Good Changes Look Like

- New modules or assets improve diagnosis, training, evaluation, transfer, or promotion quality.
- README and docs stay aligned with the actual repository behavior.
- Benchmarks become more discriminating, not more vague.
- Long-term memory stays strict: recording is not treated as mastery.

## Pull Request Checklist

- Update docs when behavior or structure changes.
- Run `python3 scripts/run-evals.py .`
- Run a benchmark smoke test when the change affects benchmarked behavior or evaluation logic.
- Keep generated benchmark outputs out of Git.
- Add or update changelog notes in [CHANGELOG.md](./CHANGELOG.md).

## Scope Guidance

### Great contributions

- Better benchmark scenarios
- Better curriculum or evaluator rubrics
- Clearer capability taxonomy
- More reusable demos
- Better installation and workflow ergonomics

### Usually not a fit

- Purely cosmetic changes with no usability benefit
- Weaker promotion rules
- Benchmark shortcuts that reduce evaluation integrity
- Large unrelated refactors without a clear repository payoff

## Commit and PR Style

- Use clear, descriptive titles.
- Explain the user-facing outcome, not only the file diff.
- Call out risks, follow-ups, and assumptions explicitly.

## Questions

Open an issue for product or design discussion. For security-sensitive concerns, follow [SECURITY.md](./SECURITY.md).
