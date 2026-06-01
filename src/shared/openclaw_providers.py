"""OpenClaw provider ids and alias normalization."""

OPENCLAW_PROVIDER_ALIASES: dict[str, str] = {
    "anthropic": "anthropic",
    "anthropic-vertex": "anthropic-vertex",
    "openai": "openai",
    "openai-codex": "openai",
    "google": "google",
    "google-gemini-cli": "google",
    "deepseek": "deepseek",
    "zai": "zai",
    "zhipu": "zai",
    "qianfan": "qianfan",
    "moonshot": "moonshot",
    "kimi": "kimi",
    "kimi-coding": "kimi",
    "minimax": "minimax",
    "minimax-portal": "minimax",
    "volcengine": "volcengine",
    "volcengine-plan": "volcengine",
    "byteplus": "byteplus",
    "byteplus-plan": "byteplus",
    "xiaomi": "xiaomi",
    "modelstudio": "modelstudio",
    "xai": "xai",
    "mistral": "mistral",
    "amazon-bedrock": "amazon-bedrock",
    "microsoft-foundry": "microsoft-foundry",
    "github-copilot": "github-copilot",
    "copilot-proxy": "copilot-proxy",
    "openrouter": "openrouter",
    "together": "together",
    "huggingface": "huggingface",
    "nvidia": "nvidia",
    "ollama": "ollama",
    "vllm": "vllm",
    "sglang": "sglang",
    "litellm": "litellm",
    "chutes": "chutes",
    "fal": "fal",
    "cloudflare-ai-gateway": "cloudflare-ai-gateway",
    "vercel-ai-gateway": "vercel-ai-gateway",
    "venice": "venice",
    "kilocode": "kilocode",
    "opencode": "opencode",
    "opencode-go": "opencode-go",
    "synthetic": "synthetic",
}


def normalize_openclaw_provider(provider: str) -> str:
    """Map config/provider aliases to the OpenClaw runtime provider id."""
    normalized = provider.strip().lower()
    return OPENCLAW_PROVIDER_ALIASES.get(normalized, normalized)
