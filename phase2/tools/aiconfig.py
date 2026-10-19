"""AI connection settings (provider, models, retries, limits). Defaults here; phase2/config.json {"ai": {...}} overrides them key by key;
environment AF_AGY_CONCURRENCY overrides the concurrency. Nothing about a provider or model is hard-coded elsewhere.

  provider            "agy" (Antigravity CLI headless, structured output via --json-schema) - the verified path on this machine
  models.cheap        classification / extraction / checking / asset planning
  models.quality      script writing, storyboard, applying feedback
  fallback            model used when the primary one fails (only if allow_fallback and the call limits still allow it)
  limits              per-project defaults; brief.json "budget" overrides them for one project
  price_per_1k_tokens optional {"<model id>": {"in": x, "out": y}} - only then an estimated money cost is shown (otherwise 'unknown')"""
import copy
import json
import os
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
DEFAULTS = {
    "provider": "agy",
    "models": {"cheap": "gemini-3.8-flash-low", "quality": "claude-sonnet-4-6"},
    "fallback": {"quality": "gemini-3.8-flash-high", "cheap": "gemini-3.8-flash-medium"},
    "allow_fallback": True,
    "timeout_seconds": 420,
    "max_retries": 1,
    "agy_concurrency": 1,
    "limits": {"llm_calls": 40, "llm_tokens": 1500000, "images": 14, "voice_credits": 900},
    "price_per_1k_tokens": None,
    # extra providers: name -> {"type": "openai_compat", "base_url": "...", "api_key_env": "ENV_NAME", "models": {"cheap": "...", "quality": "..."}, "timeout_seconds": 120}
    # the key itself is NEVER stored in config: it is read from the environment variable named by api_key_env.
    "providers": {},
    # task -> provider name (anything not listed uses "provider"); tasks that need web search always use agy
    "routing": {},
}


def _merge(a, b):
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            _merge(a[k], v)
        else:
            a[k] = v
    return a


def get():
    cfg = copy.deepcopy(DEFAULTS)
    f = P2 / "config.json"
    if f.exists():
        _merge(cfg, json.loads(f.read_text(encoding="utf-8")).get("ai"))
    extra = os.environ.get("AF_AI_CONFIG")                         # a JSON file merged last (tests, one-off experiments); never holds secrets
    if extra and Path(extra).exists():
        d = json.loads(Path(extra).read_text(encoding="utf-8"))
        _merge(cfg, d.get("ai", d))
    return cfg


def model_for(tier, cfg=None, provider=None):
    cfg = cfg or get()
    if provider and provider != "agy":
        return cfg["providers"][provider]["models"][tier]
    return cfg["models"][tier]


def fallback_for(tier, cfg=None):
    cfg = cfg or get()
    m = (cfg.get("fallback") or {}).get(tier)
    return m if cfg.get("allow_fallback") and m and m != cfg["models"][tier] else None
