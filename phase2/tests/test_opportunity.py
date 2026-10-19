"""Topic opportunity research: measured YouTube evidence (read by the tool) vs the AI's judgement, nothing invented, duplicates of earlier topics dropped,
unreadable/unsearched evidence left empty (null, never 0). Fake LLM + fake pages."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
sys.path.insert(0, str(P2 / "tests"))
import channel as CH  # noqa: E402
import new_project  # noqa: E402
import opportunity as O  # noqa: E402
import prepare as PR  # noqa: E402
import shutil  # noqa: E402
import topics  # noqa: E402
from test_prepare import FakeLLM  # noqa: E402

PAGE = '<html><meta itemprop="datePublished" content="2025-03-04T10:00:00-07:00"><script>var ytInitialPlayerResponse = {"videoDetails":{"videoId":"abc","title":"Quỹ khẩn cấp \u0111\u1ea7y \u0111\u1ee7","lengthSeconds":"612","author":"Kênh A","viewCount":"123456","isOwnerViewing":false},"microformat":{"playerMicroformatRenderer":{"publishDate":"2025-03-04T10:00:00-07:00"}}};</script></html>'
PAGE2 = PAGE.replace("123456", "2000").replace("2025-03-04", "2024-11-20")


class T(unittest.TestCase):
    def setUp(self):
        self.hist = Path(tempfile.mkdtemp()) / "history.jsonl"
        os.environ["AF_TOPIC_HISTORY"] = str(self.hist)
        self.fake = FakeLLM()
        PR.RUNNER = self.fake
        self.name = f"_t_opp_{os.getpid()}"
        self.d = new_project.create(self.name, "Tài chính cá nhân", brief={"title": "Tài chính cá nhân cho người mới đi làm", "research": "no", "character_mode": "bi"})
        pages = {}

        def fetch(url):
            if "aaa" in url:
                return url + "&x=1", 200, PAGE
            if "bbb" in url:
                return url, 200, PAGE2
            return url, 200, "<html>nothing here</html>"
        PR.FETCHER_RAW = fetch

    def tearDown(self):
        PR.RUNNER = PR.FETCHER_RAW = None
        os.environ.pop("AF_TOPIC_HISTORY", None)
        shutil.rmtree(self.d, ignore_errors=True)

    def test_page_parser_reads_only_what_the_page_states(self):
        m = O.parse_video_page(PAGE)
        self.assertEqual((m["views"], m["length_s"], m["channel"], m["published"]), (123456, 612, "Kênh A", "2025-03-04"))
        self.assertEqual(m["title"], "Quỹ khẩn cấp đầy đủ")
        self.assertEqual(O.parse_video_page("<html>no video data</html>"), {})

    def test_candidates_carry_measured_evidence_separate_from_the_ai_judgement(self):
        self.assertEqual(PR.run_steps(self.d, ["opportunity"]), {"opportunity": "ok"})
        res = json.loads((self.d / "prepare/opportunities.json").read_text(encoding="utf-8"))
        self.assertEqual(res["platform"], "youtube")
        self.assertIn("search volume", res["not_available"])
        c = res["candidates"][0]
        reads = [v for v in c["videos"] if v["measured"]]
        self.assertEqual(len(reads), 2)
        self.assertTrue(all(v["accessed_at"] and v["final_url"] for v in c["videos"]))
        unread = [v for v in c["videos"] if not v["measured"]]
        self.assertEqual(len(unread), 1, "the page that is not a video stays unmeasured")
        self.assertEqual((c["summary"]["videos_read"], c["summary"]["max_views"], c["summary"]["median_views"]), (2, 123456, 62728))
        self.assertEqual((c["summary"]["newest"], c["summary"]["oldest"]), ("2025-03-04", "2024-11-20"))
        self.assertEqual(c["evidence_state"], "measured")
        self.assertEqual(c["judgement"]["source"], "AI")
        self.assertNotIn("volume", json.dumps(c["summary"]).replace("search volume", ""))

    def test_no_search_or_unreadable_pages_give_nulls_not_zeros(self):
        class NoSearch(FakeLLM):
            def __call__(self, *a):
                data, meta = super().__call__(*a)
                meta["searches"] = 0
                return data, meta
        PR.RUNNER = NoSearch()
        PR.run_steps(self.d, ["opportunity"])
        c = json.loads((self.d / "prepare/opportunities.json").read_text(encoding="utf-8"))["candidates"][0]
        self.assertEqual(c["videos"], [], "videos from an answer that did not use web search are not accepted")
        self.assertIsNone(c["summary"]["median_views"])
        self.assertIsNone(c["summary"]["max_views"])
        self.assertEqual(c["evidence_state"], "none")
        self.assertIn("không suy ra bằng 0", c["summary"]["note"])

    def test_topics_already_made_are_not_proposed_again_and_history_is_kept(self):
        topics.add("default", "Quỹ khẩn cấp là gì và nên có bao nhiêu", "video2")
        self.assertTrue(topics.is_duplicate("Quỹ khẩn cấp là gì, nên có bao nhiêu?", topics.titles("default")))
        self.assertFalse(topics.is_duplicate("Cách chọn bảo hiểm", topics.titles("default")))
        PR.run_steps(self.d, ["opportunity"])
        res = json.loads((self.d / "prepare/opportunities.json").read_text(encoding="utf-8"))
        self.assertNotIn("Quỹ khẩn cấp là gì và nên có bao nhiêu", [c["topic"] for c in res["candidates"]])
        self.assertEqual(len(res["candidates"]), 2)
        prompt = dict(self.fake.prompts)["opportunity_topics"]
        self.assertIn("Quỹ khẩn cấp là gì và nên có bao nhiêu", prompt, "the AI is told what the channel already covered")
        n = len(self.fake.calls)
        self.assertEqual(PR.run_steps(self.d, ["opportunity"]), {"opportunity": "skipped"})
        self.assertEqual(len(self.fake.calls), n, "unchanged inputs: no second research")


if __name__ == "__main__":
    unittest.main()
