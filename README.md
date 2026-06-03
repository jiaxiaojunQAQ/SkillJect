# 🛡️ SkillJect

AI agent security evaluation framework for malicious-skill testing on top of OpenSandbox.

# 🎉  Our paper has been **Distinguished Paper Award of CVPR 6th AdvML@CV Workshop, 2026**!   


## 📖 Overview

SkillJect runs security evaluations through a single public execution flow:

- Entrypoint: `run.py`
- Main config: `config/main.yaml`
- Execution model: `execution_plan` steps select a `profile`
- Supported agents: `claude-code`, `openclaw`
- Supported generation methods: `direct_execution`, `skillject`, `template_injection`, `baseline`

The framework uses a streaming generate-execute-analyze loop and records sandbox traces plus attack outcomes.

## 🔗 Resources

- 📄 **Paper**: [arxiv.org/abs/2602.14211](https://arxiv.org/abs/2602.14211)
- 🐳 **Docker images & GLM-based generation results**: [Google Drive](https://drive.google.com/drive/folders/1CfJIJ8aJlVvB-AqpDeWXS6LIyRWGp_r6?usp=drive_link)

### 🤖 Agent Versions

| Agent | Version |
| --- | --- |
| Claude Code | `v2.1.34` |
| OpenClaw | `2026.3.31 (213a704)` |

## 🚀 Quick Start

### ✅ Prerequisites

- Python 3.10+
- Docker
- OpenSandbox server
- Required provider credentials in `.env`

### 📦 Install

```bash
pip install -e .
cp .env.example .env
```

### ▶️ Run

```bash
# 1. Start OpenSandbox
opensandbox-server

# 2. Build the sandbox image you need
docker build -f Dockerfile.claude -t claude_code:latest .

# 3. Execute the main plan
python run.py -c config/main.yaml
```

## 📝 Public Configuration Contract

`config/main.yaml` is the only supported top-level runtime entry.

It contains:

- optional global overrides, such as `generation.method`, `dataset`, `skill_names`
- `execution_plan`, a list of steps
- each step chooses a `profile` from `config/profiles/`

Example:

```yaml
generation:
  method: direct_execution

dataset:
  name: skill_inject
  base_dir: data/skill_inject
  instruction_base_dir: data/instruction/skill_inject

execution_plan:
  - profile: openclaw-minimax
  - profile: claude-gpt
    method: skillject
```

### Configuration Hierarchy

```text
config/
├── main.yaml           # User-facing entrypoint
├── agents/             # Agent runtime shape
├── base/               # Shared defaults
├── profiles/           # Runnable profile selections
├── providers/          # Flat {scenario}-{provider}.yaml defaults
└── strategies/         # Method-specific generation configs
```

Rules:

- `config/main.yaml` is the supported entrypoint
- `config/profiles/*.yaml` are internal composition files, not standalone entry configs
- `providers/` is the canonical provider layer; files are named by usage scenario, such as `strategy-llm.yaml` or `openclaw-minimax.yaml`
- strategy configs select only `llm.provider` and `llm.model`; strategy LLM connection/tuning lives in `config/providers/strategy-llm.yaml`
- agent runtime providers are separate from strategy LLM providers
- top-level overrides in `config/main.yaml` can override plan-step defaults

Strategy LLM environment variables are independent from agent runtime endpoints, for example:

```bash
STRATEGY_LLM_API_KEY=...
STRATEGY_LLM_BASE_URL=...
JUDGE_LLM_API_KEY=...
JUDGE_LLM_BASE_URL=...
OPENCLAW_MINIMAX_BASE_URL=...
CLAUDE_CODE_MINIMAX_BASE_URL=...
```

The exact names come from `config/providers/strategy-llm.yaml` and
`config/main.yaml`'s `llm_judge` block. See `.env.example` for the full list.

## ⚙️ Configuration Reference

All user-facing configuration is set in `config/main.yaml`. Internal files under `config/profiles/`, `config/base/`, `config/providers/`, and `config/strategies/` are composed by profiles and should not be edited directly.

### Top-Level Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `execution_plan` | list[Step] | yes | - | Sequential list of profile steps to run |
| `generation` | Generation | no | - | Global generation overrides |
| `dataset` | string or Dataset | no | from profile | Dataset name, path, or dict |
| `instruction` | string | no | `data/instruction/{dataset}` | Instruction directory path |
| `llm_judge` | LLM Judge | no | disabled | LLM-as-judge configuration |

### execution_plan Steps

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `profile` | string | yes | - | One of 10 supported profiles (see table below) |
| `model` | string | no | profile default | Override model for agent runtime |
| `method` | string | no | profile default | Override generation method |
| `dataset` | string or dict | no | global override | Override dataset for this step |
| `skills` | list[string] | no | all skills | Skill names to test |
| `attack_types` | list[string] | no | all types | Attack types to test |

### generation

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `method` | string | yes | - | `direct_execution`, `skillject`, `template_injection`, or `baseline` |
| `script_mapping_file` | string | no | - | Path to manifest JSON (`direct_execution` only) |
| `script_selection.mode` | string | no | `auto` | `auto`, `mapping`, or `random` |
| `script_selection.mapping_file` | string | no | - | Path to manifest JSON (when `mode=mapping`) |
| `attack_types` | list[string] | no | all | Attack types to generate (see AttackType enum) |
| `skills` | list[string] | no | all | Skill names to target |

### dataset (dict form)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | no* | derived from path | Dataset identifier |
| `base_dir` | string | no* | `data/{name}` | Path to skill dataset |
| `instruction_base_dir` | string | no | `data/instruction/{name}` | Path to instructions |

\* At least one of `name` or `base_dir` should be provided. String shorthand: `dataset: skills_sample` or `dataset: data/skills_sample`.

### llm_judge

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `attack_judgment` | bool | `false` | Use LLM for attack-success detection; `false` = rule-based detection |
| `model` | string | `gpt-4` | Judge model name (judge uses the OpenAI-compatible API) |
| `api_key_env` | string | `""` | Name of the env var holding the API key (e.g. `JUDGE_LLM_API_KEY`) |
| `base_url_env` | string | `""` | Name of the env var holding the base URL (e.g. `JUDGE_LLM_BASE_URL`) |
| `base_url` | string | `""` | Explicit base URL (overrides `base_url_env`) |
| `timeout` | int | `180` | Request timeout in seconds |
| `temperature` | float | `0.3` | Sampling temperature |
| `max_tokens` | int | `4096` | Max response tokens |

> The judge always uses the OpenAI-compatible interface; switch providers by
> pointing `base_url_env` at the right endpoint. There is no `provider` field.

### Inherited Config (from profiles)

These fields come from profile composition and have sensible defaults. Override only if needed.

**global** (from `config/base/common.yaml`):

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `verbose` | bool | `false` | Enable verbose output |
| `log_level` | string | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |

**adaptive_iteration** (from `config/base/common.yaml`):

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_attempts` | int | `5` | Max iterations per test (skillject only, min 1) |
| `stop_on_success` | bool | `true` | Stop iterating after attack success |

**execution** (from `config/base/execution.yaml`):

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `retry_failed` | bool | `true` | Retry infrastructure failures |
| `max_retries` | int | `3` | Max retries per test (min 0) |
| `save_detailed_logs` | bool | `true` | Write per-test log files |
| `test_timeout` | int | `2400` | Test execution timeout in seconds (min 1) |
| `command_timeout` | int | `2400` | Command timeout in seconds (min 1) |

**sandbox** (from `config/base/execution.yaml` + agents):

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `domain` | string | `localhost:18080` | OpenSandbox server address |
| `image` | string | `claude_code:latest` | Docker image for sandbox |

### CLI Arguments

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `-c, --config` | string | `config/main.yaml` | Config file path |
| `--max-attempts` | int | method-aware | Max iterations per test (skillject: from config; others: 1) |
| `--stop-on-success` | flag | from config | Stop on first attack success |
| `--skills` | list[string] | all | Skills to test |
| `--attack-types` | list[string] | all | Attack types to test (see AttackType enum) |
| `--no-retry` | flag | off | Disable infrastructure retries (`retry_failed=False, max_retries=0`) |
| `-v, --verbose` | flag | from config | Verbose output |

### Enum Values Reference

| Enum | Values |
|------|--------|
| AttackType | `information_disclosure`, `privilege_escalation`, `unauthorized_write`, `backdoor_injection` |
| InjectionLayer | `description`, `instruction`, `resource`, `description_resource`, `instruction_resource`, `all` |
| Severity | `low`, `medium`, `high`, `critical` |
| GenerationStrategy | `direct_execution`, `skillject`, `template_injection`, `baseline` |
| LogLevel | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |

## 🎯 Supported Profiles

| Profile | Agent | Model |
| --- | --- | --- |
| `claude-claude` | Claude Code | `claude-sonnet-4-6` |
| `claude-gpt` | Claude Code | `gpt-5-mini` |
| `claude-glm` | Claude Code | `glm-4.7` |
| `claude-minimax` | Claude Code | `MiniMax-M2.7` |
| `claude-mimo` | Claude Code | `claude-sonnet-4-6` |
| `openclaw-claude-openai` | OpenClaw | `claude-sonnet-4-6` |
| `openclaw-claude` | OpenClaw | `claude-sonnet-4-6` |
| `openclaw-gpt` | OpenClaw | `gpt-5-mini` |
| `openclaw-glm` | OpenClaw | `glm-4.7` |
| `openclaw-minimax` | OpenClaw | `MiniMax-M2.7` |

## 🧪 Generation Methods

| Method | Purpose |
| --- | --- |
| `direct_execution` | Execute pre-authored instructions with mapped scripts |
| `skillject` | Inject shell payloads into skill content with LLM-guided adaptation |
| `template_injection` | Template-based payload generation |

Adaptive loop controls (`adaptive_iteration`) apply only to `skillject`. Other methods are single-pass.

## ⚖️ LLM-as-Judge Evaluation

The framework supports an optional LLM-based judge that complements the built-in rule-based failure analysis. When enabled, the judge evaluates agent output after each test execution and can **upgrade** a verdict — detecting attack success that rule-based heuristics missed.

Configuration is added to `config/main.yaml` under the `llm_judge:` section:

```yaml
llm_judge:
  attack_judgment: false
  model: gpt-5-mini
  api_key_env: JUDGE_LLM_API_KEY
  base_url_env: JUDGE_LLM_BASE_URL
```

Judge is configured in `config/main.yaml`'s `llm_judge` section and uses independent environment variables, named by whatever `api_key_env` / `base_url_env` you set:

```bash
JUDGE_LLM_API_KEY=...
JUDGE_LLM_BASE_URL=...
```

The judge is fully optional — when not configured or disabled, the framework relies solely on rule-based analysis. When enabled, it runs after rule-based analysis and can override a "safe" verdict to "attack_success" with supporting evidence.

## 🔄 Infrastructure Retry

Transient infrastructure failures (rate limits, server errors, network timeouts, sandbox crashes) are automatically retried with exponential backoff and jitter across all three layers:

| Layer | Mechanism | Default |
| --- | --- | --- |
| **LLM API** (strategy + judge) | `LLMClient._call_with_retry()` | 3 attempts, 1s base delay |
| **Sandbox execution** | `retry_with_trace()` on `is_infrastructure_error` | `max_retries` from config |
| **Judge service** | `retry_with_trace()` wrapping `chat()` | 3 attempts, 2s base delay |

Non-retryable errors (authentication failures, invalid requests, bad parameters) fail immediately without retry.

Retry details are recorded per-iteration in both `result.json` (under `metadata.retry_trace`) and `raw_logs.txt` (under `=== Retry Details ===`). Retries are transparent — the iteration number does not increase.

Provider retry settings are configured in `config/providers/strategy-llm.yaml` and `config/main.yaml`'s `llm_judge` section:

```yaml
retry_max_attempts: 3
retry_base_delay: 1.0
retry_max_delay: 30.0
```

## 🏗️ Architecture

```text
src/
├── application/services/
│   ├── streaming_orchestrator.py
│   ├── result_analyzer.py
│   └── loop_result_analyzer.py
├── domain/
│   ├── analysis/
│   │   ├── interfaces/       # ILLMJudge abstract interface
│   │   ├── services/         # LLMJudgeService, RuleBasedFailureAnalyzer
│   │   └── value_objects/    # JudgeConfig, JudgeCriteria
│   ├── generation/
│   ├── testing/
│   └── reporting/
├── infrastructure/
│   ├── config/
│   ├── llm/
│   │   ├── base_llm_client.py # LLM client base class (with retry)
│   │   ├── judge_client.py    # LLM judge HTTP client (with retry)
│   │   └── judge_prompts.py   # Judge prompt templates
│   ├── loaders/
│   └── logging/
└── shared/
    └── exceptions.py          # RetryConfig, RetryTrace, retry_with_trace()
```

The main runtime path is:

1. Load `config/main.yaml`
2. Resolve each `execution_plan` step through a `profile`
3. Build `GenerationConfig` and execution settings
4. Run `StreamingOrchestrator`
5. Save results and summaries under the configured output directory

## 💡 Useful Commands

```bash
# Help
python run.py --help

# Run only selected skills
python run.py -c config/main.yaml --skills adaptyv hmdb-database

# Restrict attack types
python run.py -c config/main.yaml --attack-types information_disclosure privilege_escalation

# Override adaptive loop controls
python run.py -c config/main.yaml --max-attempts 10 --stop-on-success

# Analyze latest results
python run.py --analyze

# Rejudge existing results (one-time operation)
# Scans experiment_results_* directories and re-evaluates ignored/rejected tests
python -m src.application.scripts.rejudge_existing_results --base-dir . --judge-model gpt-5-mini
```

