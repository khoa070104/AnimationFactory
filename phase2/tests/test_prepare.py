"""AI preparation pipeline (brief -> research -> script -> storyboard -> asset plan -> assets) with a deterministic LLM stand-in:
valid output for two different briefs, caching/resume, user-supplied script, research evidence, budget refusal, bounded failures, overwrite protection."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P2 / "tools"))
sys.path.insert(0, str(P2 / "tests"))
import agy_image as G  # noqa: E402
import budget  # noqa: E402
import channel as CH  # noqa: E402
import fake_llm_responder as F  # noqa: E402
import llm  # noqa: E402
import new_project  # noqa: E402
import prepare as PR  # noqa: E402
from imgdouble import ColorAgy, Dispatch, RUNNER as IMG_RUNNER  # noqa: E402


class FakeLLM:
    def __init__(self, mode="ok"):
        self.calls, self.prompts, self.mode = [], [], mode

    def __call__(self, model, prompt, schema, timeout, search):
        task = F.task_of(prompt)
        self.calls.append((task, model))
        self.prompts.append((task, prompt))
        if self.mode == "down":
            raise llm.LLMError("agy produced no output")
        data = F.respond(task, prompt, schema, self.mode)
        return data, {"seconds": 0.1, "model_actual": f"Fake {model}", "searches": 1 if (task == "research_facts" or (search and task.startswith("opportunity"))) else 0, "tokens": {"in": 50, "out": 50, "total": 100},
                      "conversation_id": "c", "denied": []}


class T(unittest.TestCase):
    def setUp(self):
        self.names, self.chans = [], []
        self.fake = FakeLLM()
        PR.RUNNER = self.fake
        PR.FETCHER = None
        PR.IMAGE_RUNNER = None

    def tearDown(self):
        PR.RUNNER = PR.FETCHER = PR.IMAGE_RUNNER = None
        for n in self.names:
            shutil.rmtree(PR.P2 / "projects" / n, ignore_errors=True)
        for c in self.chans:
            (CH.CH / f"{c}.json").unlink(missing_ok=True)

    def project(self, brief, tag="a"):
        name = f"_t_prep_{tag}_{os.getpid()}_{len(self.names)}"
        d = new_project.create(name, brief.get("title", "T"), brief={"character_mode": "bi", **brief})
        self.names.append(name)
        return d

    def calls(self, task=None):
        return [c for c in self.fake.calls if task is None or c[0] == task]

    # ------------------------------------------------------------------------------------------------------------------
    def test_two_different_briefs_give_valid_scripts_and_storyboards(self):
        outs = []
        for title in ("Vay tiền mua xe có nên không", "Lập kế hoạch tiết kiệm cho kỳ nghỉ"):
            d = self.project({"title": title, "goal": "người xem hiểu các bước cơ bản", "message": "bắt đầu nhỏ", "research": "no"}, tag=str(len(outs)))
            res = PR.run_steps(d, PR.PLAN_STEPS)
            self.assertTrue(all(v == "ok" for v in res.values()), res)
            sb = json.loads((d / "storyboard.json").read_text(encoding="utf-8"))
            errs, _ = PR.validate_obj(d, sb)
            self.assertEqual(errs, [])
            self.assertTrue(6 <= len(sb["scenes"]) <= 10)
            sc = json.loads((d / "prepare/script.json").read_text(encoding="utf-8"))
            self.assertTrue(50 <= sc["stats"]["est_seconds"] <= 100, sc["stats"])
            self.assertEqual([s["voice"] for s in sb["scenes"]], [s["voice"] for s in sc["scenes"]], "the storyboard speaks exactly the script text")
            self.assertEqual(sb["voice"]["voice_id"], CH.get("default")["voice"]["voice_id"])
            outs.append((sb["title"], sb["scenes"][0]["voice"]))
        self.assertNotEqual(outs[0], outs[1])

    def test_rerun_unchanged_makes_no_ai_call_and_resumes_after_a_change(self):
        d = self.project({"title": "Chủ đề cố định", "research": "no"})
        PR.run_steps(d, PR.PLAN_STEPS)
        n = len(self.fake.calls)
        res = PR.run_steps(d, PR.PLAN_STEPS)
        self.assertEqual(set(res.values()), {"skipped"})
        self.assertEqual(len(self.fake.calls), n, "unchanged inputs: zero LLM calls")
        b = json.loads((d / "brief.json").read_text(encoding="utf-8"))
        b["notes"] = "ghi chú mới cho người viết kịch bản"
        (d / "brief.json").write_text(json.dumps(b, ensure_ascii=False), encoding="utf-8")
        res = PR.run_steps(d, PR.STEPS[:4], force=())
        self.assertEqual(res["research"], "skipped")                                   # research inputs did not change
        self.assertEqual(res["script"], "ok")                                          # notes changed -> script is rewritten
        self.assertEqual(len(self.calls("script")), 2)

    def test_owner_supplied_script_is_not_rewritten_by_ai(self):
        text = "\n\n".join(f"Đoạn {i} nói về một ý của kịch bản tự viết, câu này đủ dài để làm một cảnh riêng. Câu thứ hai bổ sung thêm." for i in range(1, 8))
        d = self.project({"title": "Kịch bản có sẵn", "script_text": text, "research": "no"})
        PR.run_steps(d, ["script"])
        self.assertEqual(self.calls("script"), [])
        sc = json.loads((d / "prepare/script.json").read_text(encoding="utf-8"))
        self.assertEqual((sc["source"], len(sc["scenes"])), ("user", 7))
        self.assertTrue(sc["scenes"][3]["voice"].startswith("Đoạn 4"))

    def test_research_keeps_sources_and_marks_unsupported_facts(self):
        pages = {"https://example.test/rates": "Bảng lãi suất. Hiện lãi suất 12 tháng 5,9% một năm tại nhóm ngân hàng lớn. Cập nhật hôm nay."}
        PR.FETCHER = lambda u: (u + "?final", 200, pages[u]) if u in pages else (u, 0, "")
        d = self.project({"title": "Lãi suất tiết kiệm hiện nay", "research": "auto", "references": "xem https://example.test/rates"})
        res = PR.run_steps(d, PR.STEPS[:2])
        self.assertTrue(all(v == "ok" for v in res.values()), res)
        r = json.loads((d / "prepare/research.json").read_text(encoding="utf-8"))
        self.assertTrue(r["searched"] and r["decision"]["needs_research"])
        f1, f2 = r["facts"]
        self.assertTrue(f1["verified"] and f1["accessed_at"] and f1["final_url"].endswith("?final"))
        self.assertTrue(f2["needs_check"] and not f2["verified"] and any("not found" in x for x in f2["reasons"]))
        self.assertTrue(r["references"][0]["reachable"])
        script_prompt = dict(self.fake.prompts)["script"]
        self.assertIn(f1["claim"], script_prompt)
        self.assertNotIn(f2["claim"], script_prompt, "unsupported facts must not reach the script writer")
        PR.set_fact_decision(d, "f2", "accept")                                        # the owner can take responsibility for it
        self.assertEqual(len(PR.research_facts(d)), 2)

    def test_research_without_search_evidence_is_not_trusted(self):
        class NoSearch(FakeLLM):
            def __call__(self, *a):
                data, meta = super().__call__(*a)
                meta["searches"] = 0
                return data, meta
        PR.RUNNER = NoSearch()
        PR.FETCHER = lambda u: (u, 200, "lãi suất 12 tháng 5,9% một năm")
        d = self.project({"title": "Lãi suất tiết kiệm", "research": "yes"})
        PR.run_steps(d, ["research"])
        r = json.loads((d / "prepare/research.json").read_text(encoding="utf-8"))
        self.assertTrue(all(f["needs_check"] and any("search tool" in x for x in f["reasons"]) for f in r["facts"]))

    def test_budget_refuses_to_start_and_resume_does_not_repeat_finished_steps(self):
        d = self.project({"title": "Có giới hạn lượt gọi", "research": "no", "budget": {"llm_calls": 1}})
        res = PR.run_steps(d, PR.PLAN_STEPS)
        self.assertEqual(res["research"], "ok")
        self.assertIn("script", res)                                                   # script used the single allowed call (script writing)
        self.assertTrue(res["script"].startswith("ok") or "failed" in res["script"])
        self.assertTrue(any(str(v).startswith("failed") and "Vượt hạn mức" in str(v) for v in res.values()), res)
        before = len(self.fake.calls)
        self.assertEqual(before, 1)
        st = PR.status(d)["steps"]
        self.assertEqual(st["storyboard"]["state"], "failed")
        self.assertIn("Vượt hạn mức", st["storyboard"]["error"])
        self.assertTrue((d / "prepare/script.json").exists(), "finished work is kept")
        b = json.loads((d / "brief.json").read_text(encoding="utf-8"))
        b["budget"] = {"llm_calls": 10}
        (d / "brief.json").write_text(json.dumps(b), encoding="utf-8")
        res = PR.run_steps(d, PR.PLAN_STEPS)
        self.assertEqual(res["script"], "skipped")
        self.assertEqual(len(self.calls("script")), 1, "the finished script call is not repeated")
        self.assertEqual(res["storyboard"], "ok")

    def test_bad_ai_output_is_bounded_then_fails_clearly_without_touching_the_project(self):
        PR.RUNNER = self.fake = FakeLLM("invalid")
        d = self.project({"title": "AI trả lỗi", "research": "no"})
        res = PR.run_steps(d, ["script"])
        self.assertTrue(res["script"].startswith("failed"))
        self.assertEqual(len(self.fake.calls), 3, "1 try + 1 retry on the primary model + 1 fallback model, never more")
        self.assertEqual([m for _, m in self.fake.calls][-1], "gemini-3.8-flash-high")
        self.assertFalse((d / "prepare/script.json").exists())
        self.assertEqual(json.loads((d / "storyboard.json").read_text(encoding="utf-8"))["scenes"], [])
        led = budget.rows(d)
        self.assertEqual(sum(1 for r in led if r["kind"] == "llm" and r["status"] == "invalid"), 3)

    def test_provider_down_goes_to_fallback_once(self):
        PR.RUNNER = self.fake = FakeLLM("down")
        d = self.project({"title": "AI sập", "research": "no"})
        res = PR.run_steps(d, ["script"])
        self.assertTrue(res["script"].startswith("failed"))
        self.assertEqual(len(self.fake.calls), 2, "primary once, fallback once")

    def test_cues_not_in_the_text_are_repaired_without_another_ai_call(self):
        PR.RUNNER = self.fake = FakeLLM("badcue")
        d = self.project({"title": "Mốc sai", "research": "no"})
        PR.run_steps(d, ["script"])
        self.fake.mode = "badcue"
        res = PR.run_steps(d, ["storyboard"])
        self.assertEqual(res["storyboard"], "ok", res)
        self.assertEqual(self.calls("storyboard_repair"), [])
        sb = json.loads((d / "storyboard.json").read_text(encoding="utf-8"))
        self.assertEqual(PR.validate_obj(d, sb)[0], [])

    def test_ai_never_overwrites_approved_or_edited_work_without_force(self):
        d = self.project({"title": "Đã duyệt", "research": "no"})
        PR.run_steps(d, PR.STEPS[:4])
        import approve
        approve.record(d, "chủ dự án", "all")
        b = json.loads((d / "brief.json").read_text(encoding="utf-8"))
        b["message"] = "đổi thông điệp"
        (d / "brief.json").write_text(json.dumps(b, ensure_ascii=False), encoding="utf-8")
        res = PR.run_steps(d, ["script"])
        self.assertTrue(res["script"].startswith("failed") and "already approved" in res["script"])
        n = len(self.fake.calls)
        res = PR.run_steps(d, ["script", "storyboard"], force=("script", "storyboard"))
        self.assertEqual((res["script"], res["storyboard"]), ("ok", "ok"))
        sb = json.loads((d / "storyboard.json").read_text(encoding="utf-8"))
        self.assertEqual(sb["version"], 2)
        self.assertTrue(list((d / "versions").glob("storyboard_v1_before_ai_*.json")), "the replaced storyboard is kept")
        import approve as A
        self.assertTrue(A.changes_since_approval(d)[0], "the rewritten text invalidates the script approval")

    def test_asset_plan_needs_approval_then_runs_through_the_job_manager_and_applies_after_asset_approval(self):
        d = self.project({"title": "Có asset AI", "research": "no"})
        PR.run_steps(d, PR.PLAN_STEPS)
        plan = json.loads((d / "prepare/asset_plan.json").read_text(encoding="utf-8"))
        self.assertEqual(len(plan["assets"]), 1)
        a = plan["assets"][0]
        self.assertEqual(a["refs"], [], "no picture of another project or a sample is ever a reference"); self.assertTrue(a["placement"]["scene"] in [s["id"] for s in json.loads((d / "storyboard.json").read_text(encoding="utf-8"))["scenes"]])
        with self.assertRaises(PR.PrepareError) as e:
            PR.do_assets(d)
        self.assertIn("not been approved", str(e.exception))
        self.assertEqual(budget.usage(d)["images"], 0, "no image before the plan is approved")
        PR.approve_plan(d, "chủ dự án")
        PR.update_plan_asset(d, a["id"], prompt="a small plant growing on a pile of coins, flat style")
        self.assertFalse(PR.plan_approved(d), "editing the plan withdraws its approval")
        PR.approve_plan(d, "chủ dự án")
        home = Path(tempfile.mkdtemp())
        os.environ["AGY_HOME"] = str(home)
        (home / "brain").mkdir()
        Dispatch.impl = img = ColorAgy(home / "brain")
        PR.IMAGE_RUNNER = IMG_RUNNER
        self.assertEqual(PR.do_assets(d, poll=0.05), "ok")
        self.assertEqual(len(img.calls), 1)
        self.assertEqual(G.approval_state(d, a["id"])[0], "draft")
        self.assertEqual(PR.apply_assets(d), [], "a draft asset is never put in a scene")
        PR.do_assets(d, poll=0.05)                                                     # run again: nothing is generated twice
        self.assertEqual(len(img.calls), 1)
        G.set_status(d, a["id"], "approved", approved_by="chủ dự án")
        self.assertEqual(PR.apply_assets(d), [a["id"]])
        sb = json.loads((d / "storyboard.json").read_text(encoding="utf-8"))
        self.assertTrue(any(i.get("img") == f"ai:{a['id']}" for s in sb["scenes"] for i in s["items"]))
        self.assertEqual(PR.validate_obj(d, sb)[0], [])
        self.assertEqual(PR.apply_assets(d), [], "applied once")

    def _approved_asset(self, title, mutate):
        d = self.project({"title": title, "research": "no"})
        PR.run_steps(d, PR.PLAN_STEPS)
        pf = d / "prepare/asset_plan.json"
        plan = json.loads(pf.read_text(encoding="utf-8"))
        mutate(plan["assets"][0], [s["id"] for s in json.loads((d / "storyboard.json").read_text(encoding="utf-8"))["scenes"]])
        pf.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        PR.approve_plan(d, "chủ dự án")
        home = Path(tempfile.mkdtemp())
        os.environ["AGY_HOME"] = str(home)
        (home / "brain").mkdir()
        Dispatch.impl = ColorAgy(home / "brain")
        PR.IMAGE_RUNNER = IMG_RUNNER
        PR.do_assets(d, poll=0.05)
        aid = plan["assets"][0]["id"]
        G.set_status(d, aid, "approved", approved_by="chủ dự án")
        return d, aid

    def test_one_background_is_shared_by_every_scene_in_its_list(self):
        def bg(a, ids):
            a["kind"], a["placement"]["mode"], a["scenes"] = "background", "bg", ids[:3]
        d, aid = self._approved_asset("Nền dùng chung", bg)
        self.assertEqual(PR.apply_assets(d), [aid])
        sb = json.loads((d / "storyboard.json").read_text(encoding="utf-8"))
        self.assertEqual([s["bg"] for s in sb["scenes"][:3]], [f"ai:{aid}"] * 3)

    def test_hold_mode_puts_the_asset_in_a_characters_hand_with_a_size_that_fits(self):
        def hold(a, ids):
            a["placement"].update({"mode": "hold", "who": "main", "side": "L"})
            a["scenes"] = ids[:2]
        d, aid = self._approved_asset("Cầm sổ", hold)
        PR.apply_assets(d)
        sb = json.loads((d / "storyboard.json").read_text(encoding="utf-8"))
        h = sb["scenes"][0]["holds"][0]
        self.assertEqual((h["prop"], h["side"], h["who"]), (f"ai:{aid}", "L", "main"))
        self.assertTrue(0 < h["scale"] <= 1.0)
        self.assertTrue(sb["scenes"][1]["holds"])
        self.assertEqual(PR.validate_obj(d, sb)[0], [])

    def test_rerun_after_assets_and_edits_changes_nothing_and_never_overwrites_edits(self):
        d = self.project({"title": "Chạy lại sau chỉnh sửa", "research": "no"})
        PR.run_steps(d, PR.PLAN_STEPS)
        PR.approve_plan(d, "chủ dự án")
        home = Path(tempfile.mkdtemp())
        os.environ["AGY_HOME"] = str(home)
        (home / "brain").mkdir()
        Dispatch.impl = ColorAgy(home / "brain")
        PR.IMAGE_RUNNER = IMG_RUNNER
        PR.do_assets(d, poll=0.05)
        aid = json.loads((d / "prepare/asset_plan.json").read_text(encoding="utf-8"))["assets"][0]["id"]
        G.set_status(d, aid, "approved", approved_by="chủ dự án")
        PR.apply_assets(d)
        import sbstore
        sbstore.edit_voice(d, "s03", json.loads((d / "storyboard.json").read_text(encoding="utf-8"))["scenes"][2]["voice"] + " Thêm một câu của chủ dự án.")
        text = (d / "storyboard.json").read_text(encoding="utf-8")
        plan = (d / "prepare/asset_plan.json").read_text(encoding="utf-8")
        n = len(self.fake.calls)
        res = PR.run_steps(d, PR.PLAN_STEPS)
        self.assertEqual(set(res.values()), {"skipped"}, res)
        self.assertEqual((d / "storyboard.json").read_text(encoding="utf-8"), text)
        self.assertEqual((d / "prepare/asset_plan.json").read_text(encoding="utf-8"), plan)
        self.assertEqual(len(self.fake.calls), n, "a library that grew since planning does not make the plan 'new'")
        b = json.loads((d / "brief.json").read_text(encoding="utf-8"))
        b["notes"] = "ghi chú mới"
        (d / "brief.json").write_text(json.dumps(b, ensure_ascii=False), encoding="utf-8")
        res = PR.run_steps(d, PR.PLAN_STEPS)
        self.assertEqual(res["script"], "ok")
        self.assertTrue(res["storyboard"].startswith("failed") and "edited or approved" in res["storyboard"], res)
        self.assertEqual((d / "storyboard.json").read_text(encoding="utf-8"), text, "the owner's edits and the applied asset are untouched")

    def test_image_limit_refuses_before_any_image_job(self):
        d = self.project({"title": "Hạn mức ảnh", "research": "no", "budget": {"images": 0}})
        PR.run_steps(d, PR.PLAN_STEPS)
        plan = json.loads((d / "prepare/asset_plan.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["assets"], [], "with no image budget the plan proposes nothing new")

    def test_channel_profile_is_reused_and_changes_invalidate_the_script(self):
        cid = f"t_chan_{os.getpid()}"
        self.chans.append(cid)
        prof = dict(CH.DEFAULT, name="Kênh thử", tone="vui vẻ, hài hước")
        CH.save(cid, prof)
        d = self.project({"title": "Theo kênh", "research": "no", "channel": cid})
        PR.run_steps(d, ["script"])
        self.assertIn("vui vẻ, hài hước", dict(self.fake.prompts)["script"])
        CH.save(cid, dict(prof, tone="nghiêm túc"))
        res = PR.run_steps(d, ["script"])
        self.assertEqual(res["script"], "ok")
        self.assertEqual(len(self.calls("script")), 2)

    def test_examples_and_capabilities_are_valid(self):
        import capabilities
        ex = json.loads((P2 / "style/storyboard_examples.json").read_text(encoding="utf-8"))["scenes"]
        d = self.project({"title": "Ví dụ"})
        sb = PR.template_storyboard(d, {"title": "x"}, CH.get("default"), {"title": "x"}, {"duration": [60, 90], "scenes": [6, 10]})
        sb["scenes"] = [dict(s, subtitles="auto", transition="cut") for s in ex]
        self.assertEqual(PR.validate_obj(d, sb)[0], [])
        cat = capabilities.capabilities(d)
        self.assertEqual({a["name"] for a in cat["actions"]}, set(capabilities.V.ACTIONS))
        self.assertEqual(set(cat["item_types"]), capabilities.V.ITEM_TYPES)


if __name__ == "__main__":
    unittest.main()
