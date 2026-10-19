"""Extra LLM provider (OpenAI-compatible gateway such as FreeLLMAPI) against a local mock server: routing per task, key from the environment only, usage and actual
model in the ledger, bounded retries, fallback to agy, every attempt counted by the budget, search tasks always on agy. No network, no key."""
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
sys.path.insert(0, str(P2 / "tests"))
import budget  # noqa: E402
import fake_llm_responder as F  # noqa: E402
import llm  # noqa: E402


class Mock(BaseHTTPRequestHandler):
    mode = "ok"
    calls = []
    auth = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n))
        Mock.calls.append(body)
        Mock.auth.append(self.headers.get("Authorization"))
        if Mock.mode == "500":
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'{"error":"boom"}')
            return
        user = body["messages"][-1]["content"]
        task = F.task_of(user)
        if Mock.mode == "garbage":
            content = "I am sorry, here is some prose and no JSON at all"
        elif Mock.mode == "fenced":
            content = "```json\n" + json.dumps(F.respond(task, user, None)) + "\n```"
        else:
            content = json.dumps(F.respond(task, user, None))
        out = json.dumps({"id": "chatcmpl-1", "model": "gateway-model-x", "choices": [{"message": {"role": "assistant", "content": content}}],
                          "usage": {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), Mock)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}/v1"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        Mock.mode, Mock.calls, Mock.auth = "ok", [], []
        self.proj = Path(tempfile.mkdtemp())
        cfgf = Path(tempfile.mkdtemp()) / "ai.json"
        cfgf.write_text(json.dumps({"ai": {"providers": {"freellmapi": {"type": "openai_compat", "base_url": self.url, "api_key_env": "AF_TEST_LLM_KEY",
                                                                       "models": {"cheap": "free-small", "quality": "free-big"}}},
                                           "routing": {"asset_prompt": "freellmapi", "research_facts": "freellmapi", "asset_plan": "freellmapi"}}}), encoding="utf-8")
        os.environ["AF_AI_CONFIG"] = str(cfgf)
        os.environ["AF_TEST_LLM_KEY"] = "test-key-not-real"
        self.agy_calls = []
        self._orig = llm._run_agy

        def fake_agy(model, prompt, schema, timeout, search):
            self.agy_calls.append((model, search))
            data = F.respond(F.task_of(prompt), prompt, schema)
            return data, {"seconds": 0.1, "model_actual": "agy " + model, "searches": 1 if search else 0, "tokens": {"in": 1, "out": 1, "total": 2}}
        llm._run_agy = fake_agy
        self.schema = {"type": "object", "required": ["prompt", "explanation"], "properties": {"prompt": {"type": "string"}, "explanation": {"type": "string"}}}
        self.prompt = "Improve the prompt\nTASK: asset_prompt"

    def tearDown(self):
        llm._run_agy = self._orig
        os.environ.pop("AF_AI_CONFIG", None)
        os.environ.pop("AF_TEST_LLM_KEY", None)

    def ledger(self):
        return [r for r in budget.rows(self.proj) if r["kind"] == "llm"]

    def test_routed_task_uses_the_gateway_and_the_ledger_shows_provider_model_tokens(self):
        r = llm.call(self.proj, "asset_prompt", "cheap", self.prompt, self.schema)
        self.assertEqual(r["meta"]["provider"], "freellmapi")
        self.assertEqual(self.agy_calls, [])
        self.assertEqual(Mock.calls[0]["model"], "free-small")
        self.assertEqual(Mock.auth[0], "Bearer test-key-not-real")
        row = self.ledger()[0]
        self.assertEqual((row["provider"], row["model"], row["model_actual"], row["tokens"]["total"], row["status"]), ("freellmapi", "free-small", "gateway-model-x", 150, "ok"))
        again = llm.call(self.proj, "asset_prompt", "cheap", self.prompt, self.schema)           # same request: answered from the project cache, no second HTTP call
        self.assertTrue(again["meta"]["cache"])
        self.assertEqual(len(Mock.calls), 1)

    def test_code_fences_are_tolerated_but_prose_is_a_failure_that_falls_back_after_bounded_retries(self):
        Mock.mode = "fenced"
        self.assertEqual(llm.call(self.proj, "asset_prompt", "cheap", self.prompt, self.schema)["meta"]["provider"], "freellmapi")
        Mock.mode, Mock.calls = "garbage", []
        p2 = self.prompt + " again"
        r = llm.call(self.proj, "asset_prompt", "cheap", p2, self.schema)
        self.assertEqual(len(Mock.calls), 2, "1 try + 1 retry on the gateway, never more")
        self.assertEqual(r["meta"]["provider"], "agy")
        self.assertTrue(self.agy_calls)
        st = [(x["provider"], x["status"]) for x in self.ledger()][-3:]
        self.assertEqual(st, [("freellmapi", "invalid"), ("freellmapi", "invalid"), ("agy", "ok")])

    def test_http_error_and_missing_key_fall_back_to_agy_and_are_never_hidden(self):
        Mock.mode = "500"
        r = llm.call(self.proj, "asset_prompt", "cheap", self.prompt, self.schema)
        self.assertEqual(r["meta"]["provider"], "agy")
        errs = [x for x in self.ledger() if x["status"] == "error"]
        self.assertTrue(errs and "HTTP 500" in errs[0]["error"])
        os.environ.pop("AF_TEST_LLM_KEY")
        r = llm.call(self.proj, "asset_prompt", "cheap", self.prompt + " no key", self.schema)
        self.assertEqual(r["meta"]["provider"], "agy")
        self.assertTrue(any("environment variable" in x.get("error", "") for x in self.ledger()))

    def test_every_attempt_counts_against_the_budget_and_refuses_before_starting(self):
        (self.proj / "brief.json").write_text(json.dumps({"budget": {"llm_calls": 2}}), encoding="utf-8")
        Mock.mode = "500"
        llm.call(self.proj, "asset_prompt", "cheap", self.prompt, self.schema)                   # 1 failed gateway call + 1 agy call = 2
        self.assertEqual(budget.usage(self.proj)["llm_calls"], 2)
        with self.assertRaises(budget.BudgetError):
            llm.call(self.proj, "asset_prompt", "cheap", self.prompt + " third", self.schema)
        self.assertEqual(len(Mock.calls), 1, "nothing was sent after the limit")

    def test_search_tasks_stay_on_agy_even_when_routed_elsewhere(self):
        schema = {"type": "object", "required": ["facts"], "properties": {"facts": {"type": "array"}}}
        r = llm.call(self.proj, "research_facts", "cheap", "find facts\nTASK: research_facts", schema, search=True)
        self.assertEqual(r["meta"]["provider"], "agy")
        self.assertEqual(Mock.calls, [])
        self.assertEqual(self.agy_calls[0][1], True)

    def test_unconfigured_provider_is_an_error_not_a_silent_default(self):
        cfgf = Path(tempfile.mkdtemp()) / "ai2.json"
        cfgf.write_text(json.dumps({"ai": {"routing": {"asset_prompt": "nope"}}}), encoding="utf-8")
        os.environ["AF_AI_CONFIG"] = str(cfgf)
        with self.assertRaises(llm.LLMError) as e:
            llm.call(self.proj, "asset_prompt", "cheap", self.prompt, self.schema)
        self.assertIn("not configured", str(e.exception))


if __name__ == "__main__":
    unittest.main()
