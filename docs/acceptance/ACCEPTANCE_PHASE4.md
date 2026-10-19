# Acceptance — Phase 4 (kế hoạch v2, 18/10/2026)

Test suite: 135 tests, all green (see evidence/tests_log.txt). Each section says what is REAL, MOCK or BLOCKED.

## Chặng 1 — asset policy + AI characters
- Asset policy (new / series / library / legacy), character_mode ai|bi: unit + project tests. MOCK LLM.
- AI character pipeline (parts sheet + faces sheet -> alpha slicing -> rig -> real EffectCraft/FilmCraft motion): REAL renderer with REAL Antigravity-made fixture sheets; motion QA, selective rebuild and Bi pixel-identity proven in tests/test_characters.py.
- Fresh image generation from Antigravity today: BLOCKED (agy "not logged in").

## Chặng 2 — multi-scene, cast, cues
- Cast (≤3 per scene), layout boxes, cue tolerance 0.7 s with criteria locked before build, cue review flow, draft voice stub: tests. MOCK LLM, REAL render.
- Gate 1 (gate1_hoc_bai) and Samples A/B/C with real LLM + real voice: BLOCKED (agy login; voice credits need owner approval). Not run, not claimed.

## Chặng 3 — research, providers, UI, Telegram
- Opportunity research: measured YouTube page data (views/length/date, access time) kept apart from AI judgement; null never 0; no search volume. Tested with fake pages (MOCK fetch/LLM); UI card "Chọn chủ đề" on Overview.
- OpenAI-compatible provider adapter + routing/fallback/budget: tested against a mock server. REAL FreeLLMAPI and the 20-task comparison: BLOCKED (needs endpoint + env key; harness ops/llm_compare.py ready).
- Telegram send/feedback/approve (allow-list, dedupe, expiry on hash change): mock Bot API. REAL Telegram: BLOCKED (needs token env + allowed ids).
- Actor identity: Telegram/test/AI approvals never unlock paid voice; only human approval does.

## Limits
Mouth is not lip-sync; single narrator voice; transitions cut/fade only; AI characters = front-facing cut-out humanoids only.
Test/AI approvals in demo projects are not owner approvals.

## Gate 1 — REAL run (gate1_hoc_bai, 2026-10-19)
REAL: storyboard from the agy LLM (3 scenes), two characters (chi_lan, minh) drawn by real Antigravity, rigged, draft video 35.3 s with silent stub voice (no paid voice), all build QA PASS.
Approvals: asset plan approved by label `claude-test` (not the owner); characters are `draft` (owner has not approved their pictures); no voice credits spent.
Two defects found only by the real run, fixed in shared components (thresholds unchanged): holds are shortened to fit the next cue (HOLDCLAMP); an entrance is shortened (WALKCLAMP, step every ~0.2 s, same speed) and no action may overlap the previous one (point_seq no longer exempt); `produce.py --draft` now validates with draft characters allowed. 135 tests green after the fixes.
Observed agy behaviour: each call ~2 min (first request stalls ~115 s then retries).

### Gate 1 — owner review round 1 (2026-10-19): fixes in shared components
Owner approved the character look and the idea; did NOT approve Gate 1 as complete. Findings and the reusable fix for each:
- Walk-in crossed the other character / phone: entrances now start from the screen edge nearest the final position (never across the stage), and layout.py checks the swept walk-in path against other characters and items (warning). Tests: test_phase4_feedback.
- Every list item used a coin icon: pills now have `marker` number (default 1-2-3) | dot | coin; coin on a non-money list is a validator warning; the storyboard prompt says so.
- Empty cream scenes although the text names a place/activity: the asset planner now reads where/what per scene first and proposes a background per named place + props for handled objects (ASSET_CAP 6, image budget still caps). NOT yet proven on real data: needs Sample A (or re-planning gate1) with real Antigravity.
- Voice edit left cast cues stale (found while applying the owner's wording change): realign.py now handles cast members' cues. s03 wording changed as the owner suggested (storyboard v5).
Rebuilt draft v5 (36.3 s): all QA PASS, walk-in no longer crosses, numbered list. Still pending owner: approval of Gate 1, characters, voice/pacing (needs paid voice, not run).

## Remotion renderer (2026-10-19) — chọn bằng `produce.py --renderer remotion`
REAL: bản thử 3 cảnh Sample A (≈30 s, rig Antigravity của Gate 1 làm placeholder, nền vẽ bằng code, giọng nháp im lặng) dựng ~31 s; sửa một ô bảng → chỉ dựng lại 1 cảnh trong 15 s, 0 lượt API (ledger không đổi). Tích hợp vào luồng sản xuất: `build_remotion.py`, `export_remotion.py`, qa.mjs; gate1_hoc_bai dựng bản nháp qua `produce.py --draft --renderer remotion` (36 s, toàn bộ QA đạt, 34 s so với ~90 s của Craft).
Sửa lỗi cache (do người review phát hiện): chữ ký chỉ gồm rig của nhân vật đầu → nay gồm rig + ảnh MỌI nhân vật, fps/kích thước/png scale/màu/font/audio/kích thước ảnh; 16 test node + 3 test Python (cache, từ chối thay thế âm thầm, dựng lại tăng dần).
Lỗi tìm thấy nhờ QA dùng chung: Remotion nội suy khóa không theo lưới khung hình như EffectCraft → nhảy 39°/khung ở s02; đã khóa key vào lưới khung hình.
Chưa chứng minh: asset/nhân vật mới của Sample A từ Antigravity (cần chủ dự án duyệt kế hoạch ảnh), giọng thật, nghe/xem bản nghiệm thu.

## Sample A — nghiệm thu bằng giọng thật (2026-10-20) — sample_a_thuc_don_tuan, storyboard v17, Remotion
REAL: kế hoạch 9 ảnh Antigravity do chủ dự án duyệt → 9 ảnh (12/14 lượt, 3 ảnh sinh lại) → duyệt ảnh (ghi theo xác nhận chat vì UI không chạy) → áp asset (nền dùng chung 7 cảnh, 2 tủ lạnh trước/sau, túi cầm tay) → lời v17 do chủ dự án duyệt + trần 1200 credit → giọng thật 8 cảnh, **858 credit** (ước tính 853; một lần lỗi 503 khi hỏi trạng thái, chạy lại nối tiếp không trả phí lại) → video 92,6 s có tiếng thật, QA: 1080p+audio, số cảnh, phụ đề, cue ≤0,7 s, chuyển động ĐẠT.
**Một tiêu chí KHÔNG đạt: thời lượng 60–90 s (thực tế 92,6 s).** Tiêu chí đã khóa từ brief 75±15 s; tôi không nới ngưỡng. Cần chủ dự án quyết: chấp nhận 92,6 s (ghi quyết định) hoặc rút lời rồi tạo lại giọng (tốn thêm credit).
Chạy lại không đổi: voice SKIP 8/8, video dùng lại 8/8, 15 s, credit giữ 858, 0 lượt API.
Cơ chế mới dùng chung: đối chiếu lời ↔ hành động (`action_match.py`), bố cục khung nội dung (`layout.compose`), bảng đủ ô theo lời, bỏ emoji, ảnh thiếu thì từ chối dựng, cheer một tay khi tay kia cầm đồ.
Hạn chế: chưa vẽ mở tủ/xếp đồ/ngồi (lời đã sửa để không nói đến), Linh viết bằng cách cầm sổ trước ngực; một số cảnh bút vung theo khi chỉ tay; ảnh nhân vật/asset chủ dự án duyệt qua chat.
