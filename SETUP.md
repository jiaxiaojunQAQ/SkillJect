# Setup Guide

## Overview

This guide covers the complete setup process for the Security Evaluation Framework, including OpenSandbox server installation and Docker image preparation.

## Prerequisites

- Docker installed and running
- Python 3.10+
- (Optional) `uv` for faster package installation

## Step 1: OpenSandbox Server Setup

OpenSandbox is a required dependency for running security tests in isolated sandboxes.

### Option A: Quick Install (Recommended)

```bash
# Install OpenSandbox server
pip install opensandbox-server

# Initialize configuration
opensandbox-server init-config ~/.sandbox.toml --example docker
```

### Option B: Install from Source

```bash
# Clone the repository
git clone https://github.com/alibaba/OpenSandbox.git
cd OpenSandbox/server

# Install dependencies
pip install -e .

# Copy configuration file
cp example.config.toml ~/.sandbox.toml
```

### Start the Server

```bash
# Start OpenSandbox server
opensandbox-server

# Or from source:
cd OpenSandbox/server
python -m src.main
```

**Verify the server is running:**
```bash
curl http://localhost:8080/health
```

## Step 2: Build Docker Image

The framework requires a Docker image with Claude Code CLI installed.

```bash
# Build the image from Dockerfile
docker build -f Dockerfile.claude -t claude_code:latest .

# Verify the image
docker images | grep claude_code
```

## Step 3: Configure Environment

Create or edit `.env` file:

```bash
# Judge LLM (required when llm_judge is configured in config/main.yaml)
JUDGE_LLM_API_KEY=sk-xxx
# JUDGE_LLM_BASE_URL=https://api.openai.com/v1

# Strategy LLM (only for skillject / template_injection generation methods)
STRATEGY_LLM_API_KEY=sk-xxx
# STRATEGY_LLM_BASE_URL=https://api.openai.com/v1

# Agent runtime credentials — fill only the providers your profiles use
ANTHROPIC_API_KEY=sk-ant-xxx           # claude-claude
OPENAI_API_KEY=sk-xxx                  # claude-gpt / openclaw-gpt
ZHIPU_API_KEY=xxx.xxx                  # claude-glm / openclaw-glm
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/anthropic
# MINIMAX_API_KEY=sk-xxx               # claude-minimax / openclaw-minimax
# CLAUDE_CODE_MINIMAX_BASE_URL=https://api.minimax.chat/anthropic
# OPENCLAW_MINIMAX_BASE_URL=https://api.minimax.chat/v1
# OPENCLAW_GATEWAY_TOKEN=xxx           # required by any openclaw-* profile

# OpenSandbox Configuration
SANDBOX_DOMAIN=localhost:8080
SANDBOX_IMAGE=claude_code:latest
```

> The env var **names** are defined in `config/providers/*.yaml` (`auth_token_env` /
> `base_url_env`) and `config/main.yaml` (`llm_judge.api_key_env` / `base_url_env`).
> See [`.env.example`](.env.example) for the complete, grouped reference.

## Step 4: Run Evaluation

```bash
# Example: Run the main plan
python run.py -c config/main.yaml

# Example: Run with specific skills
python run.py -c config/main.yaml --skills adaptyv hmdb-database

# Example: Run with verbose output
python run.py -c config/main.yaml --verbose
```

## Troubleshooting

### OpenSandbox Server Issues

**Server won't start:**
- Check if port 8080 is available: `lsof -i :8080`
- Verify Docker is running: `docker ps`
- Check `~/.sandbox.toml` configuration

**Connection refused:**
- Ensure OpenSandbox server is running: `curl http://localhost:8080/health`
- Check `SANDBOX_DOMAIN` in your .env file

### Docker Image Issues

**Build fails:**
- Check Docker daemon is running
- Ensure you have sufficient disk space
- Try building with no-cache: `docker build --no-cache -f Dockerfile.claude -t claude_code:latest .`

### Configuration Issues

**Authentication errors:**
- Verify API keys in `.env` file
- Check the key matches the profile's provider (e.g. `claude-claude` needs `ANTHROPIC_API_KEY`)
- For GLM models, verify `ZHIPU_API_KEY` format and `ZHIPU_BASE_URL`

## Additional Resources

- [OpenSandbox Documentation](https://github.com/alibaba/OpenSandbox) - Official OpenSandbox repository and docs
- [README.md](README.md) - Main project documentation
- [RUNBOOK.md](docs/RUNBOOK.md) - Operations manual
