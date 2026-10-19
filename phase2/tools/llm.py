"""LLM calls with structured (JSON-schema) output, through the configured provider (aiconfig; default: Antigravity `agy` headless).

  r = llm.call(proj, task="script", tier="quality", prompt=..., schema={...}, search=False)
  r["data"]  the parsed, schema-checked object      r["meta"]  model asked/actual, tokens, seconds, cache, conversation id, search used

Rules (shared by every AI step of the tool)
  * cache: the same (provider, model, prompt, schema, search) answers from PROJECT/llm_cache/ - no new call, no cost (rerun unchanged = 0 calls);
  * budget: a call that would exceed the project's llm_calls / llm_tokens limit is refused BEFORE it starts (budget.BudgetError);
  * bounded: per call at most 1 + max_retries invalid-output tries on the primary model, then ONE configured fallback model (if allowed and
    the limits still allow it); a timeout or crash goes to the fallback directly (no loops);
  * concurrency: runs inside an agy slot shared by all processes (agy_slots), default 1 at a time;
  * every real attempt is written to PROJECT/logs/ai_ledger.jsonl with the REAL model label (read from agy's log), tokens and seconds;
  * the agent is told not to use tools except web search when `search` is requested; the run happens in an empty temp directory.
agy does not report money, only tokens; money stays 'unknown' unless a price table is configured."""
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import agy_image as G
import agy_slots
import aiconfig
import budget


class LLMError(RuntimeError):
    pass


def check_schema(data, schema, path="$"):
    """Small JSON-schema subset check (type, required, properties, items, enum, minItems/maxItems). -> list of problems."""
    errs = []
    t = schema.get("type")
    py = {"object": dict, "array": list, "string": str, "integer": int, "number": (int, float), "boolean": bool}
    if isinstance(t, list):                                              # union, e.g. ["string", "number"]
        if any(not check_schema(data, {**schema, "type": x}, path) for x in t):
            return []
        return [f"{path}: expected one of {t}"]
    if t and (not isinstance(data, py[t]) or (t in ("integer", "number") and isinstance(data, bool))):
        return [f"{path}: expected {t}"]
    if "enum" in schema and data not in schema["enum"]:
        errs.append(f"{path}: {data!r} not in {schema['enum']}")
    if t == "object":
        for k in schema.get("required", []):
            if k not in data:
                errs.append(f"{path}: missing {k!r}")
        for k, sub in (schema.get("properties") or {}).items():
            if k in data:
                errs += check_schema(data[k], sub, f"{path}.{k}")
    if t == "array":
        if "minItems" in schema and len(data) < schema["minItems"]:
            errs.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(data) > schema["maxItems"]:
            errs.append(f"{path}: more than {schema['maxItems']} items")
        for i, x in enumerate(data):
            errs += check_schema(x, schema.get("items") or {}, f"{path}[{i}]")
    return errs


def _run_agy(model, prompt, schema, timeout, search):
    """One agy headless run. -> (structured data or None, meta). Raises LLMError on infrastructure failure."""
    with tempfile.TemporaryDirectory(prefix="af_llm_", ignore_cleanup_errors=True) as d:     # a killed agy child may still hold a file for a moment (Windows)
        d = Path(d)
        sf = d / "schema.json"
        sf.write_text(json.dumps(schema), encoding="utf-8")
        log = d / "agy.log"
        guard = ("You are a text/JSON generator inside a tool. Never run shell commands, never read or write files. "
                 + ("You MAY use web search; use it for facts you must verify. " if search else "Do not use any tools. ")
                 + "Answer only with the JSON object required by the schema.\n\n")
        cmd = G.agy_cmd() + ["--print", guard + prompt, "--json-schema", str(sf), "--model", model, "--output-format", "stream-json",
                             "--print-timeout", f"{max(10, timeout - 15)}s", "--log-file", str(log)]
        t0 = time.time()
        try:
            with agy_slots.AgySlot("llm"):
                r = subprocess.run(cmd, cwd=d, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        except subprocess.TimeoutExpired as e:
            raise LLMError(f"timeout: agy did not answer within {timeout}s") from e
        except OSError as e:
            raise LLMError(f"cannot start agy: {e}") from e
        events = []
        for line in r.stdout.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    events.append(json.loads(line))
                except ValueError:
                    pass
        meta = {"seconds": round(time.time() - t0, 1), "model_actual": G.agent_model(log), "searches": 0, "tokens": {}, "denied": [], "conversation_id": None}
        data, resp = None, ""
        for e in events:
            su = e.get("step_update") or {}
            if su.get("tool_name") == "search_web" and su.get("state") == "DONE":
                meta["searches"] += 1
            if e.get("event") == "result":
                res = e["result"]
                meta["conversation_id"] = res.get("conversation_id")
                u = res.get("usage") or {}
                meta["tokens"] = {"in": u.get("input_tokens", 0), "out": u.get("output_tokens", 0), "thinking": u.get("thinking_tokens", 0), "total": u.get("total_tokens", 0)}
                meta["denied"] = [x.get("action") for x in res.get("denied_actions") or []]
                data, resp = res.get("structured_output"), res.get("response") or ""
        if data is None and resp:
            m = re.search(r"\{.*\}", resp, re.S)
            if m:
                try:
                    data = json.loads(m.group(0))
                except ValueError:
                    data = None
        if not events:
            raise LLMError("agy produced no output: " + (r.stderr or "").strip()[-200:])
        return data, meta


def _key(provider, model, prompt, schema, search):
    return hashlib.sha256(json.dumps([provider, model, prompt, schema, bool(search)], ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:24]


def _run_http(pcfg, model, prompt, schema, timeout, search):
    """OpenAI-compatible chat/completions provider (FreeLLMAPI and similar gateways). The key comes from the environment variable pcfg["api_key_env"]."""
    key = os.environ.get(pcfg.get("api_key_env") or "")
    if not key:
        raise LLMError(f"provider key missing: set the environment variable {pcfg.get('api_key_env')!r}")
    system = ("You are a text/JSON generator inside a tool. Answer with ONE JSON object only (no markdown, no commentary) that matches this JSON schema:\n" + json.dumps(schema, ensure_ascii=False))
    body = json.dumps({"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}], "temperature": 0.2,
                       "response_format": {"type": "json_object"}}).encode("utf-8")
    req = urllib.request.Request(pcfg["base_url"].rstrip("/") + "/chat/completions", data=body, method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=int(pcfg.get("timeout_seconds") or timeout)) as r:
            resp = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise LLMError(f"provider HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:200]}") from e
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise LLMError(f"provider unreachable or not JSON: {e}") from e
    try:
        text = resp["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError("provider answer has no choices[0].message.content") from e
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    data = None
    try:
        data = json.loads(text)
    except ValueError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                data = json.loads(m.group(0))
            except ValueError:
                data = None
    u = resp.get("usage") or {}
    meta = {"seconds": round(time.time() - t0, 1), "model_actual": resp.get("model") or model, "searches": 0, "denied": [], "conversation_id": resp.get("id"),
            "tokens": {"in": u.get("prompt_tokens", 0), "out": u.get("completion_tokens", 0), "thinking": 0, "total": u.get("total_tokens", (u.get("prompt_tokens", 0) + u.get("completion_tokens", 0)))}}
    return data, meta


def _provider_chain(cfg, task, tier, search, runner):
    """-> [(provider, model, call)]: the routed provider first, then agy as the configured fallback. Search tasks and test runners always use agy."""
    agy_fn = runner or _run_agy
    agy_models = [aiconfig.model_for(tier, cfg)] + ([aiconfig.fallback_for(tier, cfg)] if aiconfig.fallback_for(tier, cfg) else [])
    prov = (cfg.get("routing") or {}).get(task) or cfg["provider"]
    if search or runner is not None or prov == "agy":
        if prov not in ("agy",) and not search and runner is None:
            pass
        return [("agy", m, agy_fn) for m in agy_models]
    pcfg = (cfg.get("providers") or {}).get(prov)
    if not pcfg:
        raise LLMError(f"provider {prov!r} is not configured (config.json ai.providers)")
    http = lambda model, prompt, schema, timeout, srch, _p=pcfg: _run_http(_p, model, prompt, schema, timeout, srch)
    chain = [(prov, aiconfig.model_for(tier, cfg, prov), http)]
    if cfg.get("allow_fallback", True):
        chain += [("agy", m, agy_fn) for m in agy_models]
    return chain


def call(proj, task, tier, prompt, schema, search=False, fresh=False, runner=None, validate=None):
    """See module doc. `runner(model, prompt, schema, timeout, search)` replaces the agy call (tests). Provider per task: config ai.routing, else ai.provider."""
    proj = Path(proj)
    cfg = aiconfig.get()
    chain = _provider_chain(cfg, task, tier, search, runner)
    prov0, primary = chain[0][0], chain[0][1]
    key = _key(prov0, primary, prompt, schema, search)
    cdir = proj / "llm_cache"
    cf = cdir / f"{key}.json"
    if cf.exists() and not fresh:
        hit = json.loads(cf.read_text(encoding="utf-8"))
        budget.append(proj, {"kind": "llm", "task": task, "tier": tier, "provider": prov0, "model": primary, "cache": True, "key": key})
        return {"data": hit["data"], "meta": {**hit["meta"], "cache": True}}
    last = "no attempt"
    for mi, (prov, model, fn) in enumerate(chain):
        tries = 1 + (int(cfg["max_retries"]) if mi == 0 else 0)
        for k in range(tries):
            budget.check(proj, "llm_calls", 1)                        # raises BudgetError: nothing is started over the limit - every try, retry and fallback counts
            budget.check(proj, "llm_tokens", 1)
            row = {"kind": "llm", "task": task, "tier": tier, "provider": prov, "model": model, "key": key, "attempt": k + 1, "fallback": mi > 0}
            try:
                data, meta = fn(model, prompt, schema, int(cfg["timeout_seconds"]), search)
            except LLMError as e:
                last = str(e)
                budget.append(proj, {**row, "status": "error", "error": last})
                break                                                   # infrastructure failure: no retry on this model, go to the fallback
            problems = ["no structured answer"] if data is None else check_schema(data, schema)
            if not problems and validate:
                problems = list(validate(data) or [])                    # task-specific sanity check (e.g. an image prompt that is not an instruction echo)
            budget.append(proj, {**row, "status": "ok" if not problems else "invalid", "model_actual": meta.get("model_actual"), "tokens": meta.get("tokens"),
                                 "seconds": meta.get("seconds"), "conversation_id": meta.get("conversation_id"), "searches": meta.get("searches"),
                                 **({"error": "; ".join(problems[:3])} if problems else {})})
            if not problems:
                out = {"data": data, "meta": {**meta, "model": model, "provider": prov, "cache": False, "tier": tier, "task": task}}
                cdir.mkdir(exist_ok=True)
                G.write_json_atomic(cf, out)
                return out
            last = "invalid structured output: " + "; ".join(problems[:3])
            prompt += f"\n\nYour previous answer was rejected: {'; '.join(problems[:3])}. Return exactly the required JSON."
    raise LLMError(f"AI call '{task}' failed after the allowed attempts ({last}). Nothing was changed; fix the cause and run the step again (finished steps are not repeated).")
