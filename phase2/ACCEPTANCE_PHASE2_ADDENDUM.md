# Phase 2 – Phụ lục nghiệm thu (ba việc chốt)

Ngày 2026-10-18. Mã công cụ hiện tại: `evidence/code_manifest.json` (overall 25408ed5a6e684e4). Mẫu (video 1, video 2, ui_demo) chỉ dùng để chứng minh chức năng.

## 1. Claude Code gọi MCP thật (Claude → MCP → bộ tạo asset)

- Cách làm: mở **một phiên Claude Code mới** trong `D:\AnimationFactory`, nạp `.mcp.json` đã đăng ký. Phiên được dặn *không* chạy server bằng tay, *không* đọc file, *không* chạy shell, chỉ dùng hai tool MCP, và chỉ dùng yêu cầu đã có.
- Bản ghi nguyên văn của phiên: `evidence/claude_mcp_session/session_transcript.jsonl`.
- Kết quả (từ bản ghi):
  1. Phiên tìm thấy `mcp__animation-factory-assets__submit_asset_job` và `...__check_asset_job` (qua ToolSearch).
  2. `submit_asset_job(project=video2_quy_khan_cap, asset_id=umbrella_ai, kind=prop, prompt=…, reference_images=[frame01.png], display_width=300)` → `job_id umbrella_ai-90c3537188`, `state succeeded`, ghi chú *"same request: stored result is used, no image was generated"*.
  3. `check_asset_job(umbrella_ai-90c3537188)` → `ai_assets/umbrella_ai.png`, sha256 `a64120f4…04ae`, status `approved`, `tool_evidence true`.
  4. `check_asset_job(calm_room_ai-deed835bee)` → `ai_assets/calm_room_ai.png`, sha256 `62b1f914…ec9c`, status `approved`.
- Chứng minh **không có ảnh mới**: sha256 của hai PNG trùng bản trước; thời gian sửa file/log/job đều 17:56–17:57 (trước phiên thử lúc 18:58); thư mục `jobs/` và `logs/` không có mục mới.
- Điểm mơ hồ phiên thử nêu ra và đã sửa: bản ghi job giữ `reused:false` của **lần chạy gốc**, nên khi gửi lại người đọc không biết lần gửi này có chạy lại không. Nay phản hồi `submit_asset_job` khi dùng kết quả đã lưu có thêm `reused_now:true` và `new_generation:false` (có test). Lời gọi bằng phiên thật ở trên được thực hiện *trước* khi thêm hai trường này.
- Chưa chứng minh trong phiên thật: đường tạo ảnh **mới** từ Claude Code (Claude → MCP → agy). Đường này đã chạy thật qua stdio (`evidence/mcp_scene_video2.md`, `ops/mcp_real_e2e.py`) và qua giao diện (`coin_ui`), nhưng không phát sinh thêm ảnh trong đợt này theo yêu cầu.
- Lần thử đầu bằng `claude -p` ngoài phiên bị "Not logged in" (CLI đóng gói riêng chưa đăng nhập); máy chủ MCP kết nối bình thường. Không dùng kết quả đó làm bằng chứng.

## 2. Khả năng sản xuất dùng lại – đối chiếu từng trường hợp

Nguồn: `evidence/dependency_cache_video2.md` (chạy trên **bản sao** của video 2, không đụng dự án thật) + log dựng trong `projects/*/logs/`. Chạy bổ sung hôm nay sau các sửa lỗi nhỏ (cùng mã công cụ mới) – dựng lại cả ba dự án: **không cảnh nào dựng lại, 0 lần gọi API** (video1 9/9, video2 9/9, ui_demo 3/3 dùng lại).

| Trường hợp yêu cầu | Bằng chứng | Kết quả |
|---|---|---|
| Dựng video 2 không sửa code riêng | cùng `frozen_code_hash 11701db21ad47fec` ở video 1, video 2, ui_demo khi dựng; test `test_no_project_content_in_shared_code` cấm nội dung video trong mã dùng chung; video 2 chỉ khác nhau ở dữ liệu `storyboard.json` | đạt |
| Chạy lại không đổi | dòng 1 của bảng phụ thuộc: dùng lại 9/9, 0 API; chạy bổ sung hôm nay cho 3 dự án | đạt |
| Đổi hình một cảnh | dòng 4 (đổi bố cục s03 → chỉ dựng lại s03, 0 API); dòng 3 (sửa asset AI piggy_ai → chỉ s06); thật: video 2 cảnh 6 đổi sang `ai:piggy_ai` chỉ dựng lại cảnh 6 | đạt |
| Đổi lời, chạy thử khô | dòng 5: trước khi duyệt lại → bị **từ chối**; sau duyệt lại: 1 cảnh cần sinh (123 ký tự, ~89 credit), 8 cảnh giữ nguyên, 0 API | đạt |
| Thêm asset không dùng | dòng 2: không cảnh nào dựng lại | đạt |
| Sửa asset đang dùng | dòng 3: chỉ cảnh dùng asset đó dựng lại | đạt |
| (thêm) sửa hành động dùng chung / sửa khung xương | dòng 6 (chỉ cảnh dùng hành động), dòng 7 (dựng lại tất cả) | đạt |

Chuẩn hóa số `speed` (1 ↔ 1.0): lỗi thật phát hiện khi lưu từ trình duyệt; đã sửa trong `approve.py`. Test `test_speed_1_vs_1_0_is_not_a_change` chứng minh cả hai chiều: đổi `1.0→1` **không** bị coi là đổi, nhưng sửa lời một cảnh sau đó **vẫn bị chốt duyệt chặn** (`V.run` từ chối, `changes_since_approval` trả đúng cảnh). Giới hạn: `scene_hash` (phần hình) vẫn so chuỗi số nguyên bản, nên lưu lại qua trình duyệt một cảnh có số kiểu `1.0` sẽ bị đánh dấu "đổi hình" (báo dư, an toàn; không bao giờ bỏ sót).

## 3. Trạng thái duyệt

### 3a. Năm cảnh video 1 bị đánh dấu "đổi sau duyệt" (bản duyệt: storyboard v2)

So sánh `storyboard.json` hiện tại với `versions/storyboard_v2_approved.json`: **chỉ một trường khác** ở mỗi cảnh, `hold_after` (thời gian giữ hình thêm sau khi hết lời; được thêm sau bản duyệt, chưa có xác nhận của chủ dự án). Lời đọc, giọng, tốc độ, số liệu, hình, hành động: không đổi.

| Cảnh | Tên | Đổi gì | Ảnh hưởng | Cần duyệt lại |
|---|---|---|---|---|
| s03 | Xem lại chi tiêu | thêm `hold_after: 0.9` | nhịp hình: cảnh dài thêm 0,9 s | duyệt nhịp (hình) |
| s05 | Xe hỏng | thêm `hold_after: 0.7` | nhịp hình +0,7 s | duyệt nhịp |
| s06 | Thử chia lương | thêm `hold_after: 0.9` | nhịp hình +0,9 s | duyệt nhịp |
| s07 | Áp dụng với 15 triệu | thêm `hold_after: 0.9` | nhịp hình +0,9 s | duyệt nhịp |
| s09 | Kết | thêm `hold_after: 1.4` | nhịp hình +1,4 s | duyệt nhịp |

Cổng duyệt cho thấy: `voice changed = []` (lời **không** đổi, không gọi API giọng, không cần duyệt lại lời); `visual changed = [s03, s05, s06, s07, s09]`. Muốn xóa cờ: chủ dự án chạy `python phase2/tools/approve.py phase2/projects/video1_luong --by "tên"` (duyệt cả bản), hoặc yêu cầu bỏ `hold_after`.

### 3b. Ai đã duyệt gì – phân biệt kiểm thử và duyệt thật

| Mục | Trạng thái | Nguồn xác nhận |
|---|---|---|
| video1 nội dung v2 | duyệt | chủ dự án xác nhận trong chat (Claude ghi lại, `recorded_by` trong `approval.json`); cờ hình ở 3a |
| video2 nội dung v3 (gồm s04b, `ai:piggy_ai` ở cảnh 6) | duyệt | chủ dự án xác nhận trong chat; ghi lại bởi Claude |
| asset `piggy_ai` | approved | chủ dự án nói duyệt trong chat |
| asset `umbrella_ai`, `calm_room_ai` | approved | chủ dự án nói "Duyệt umbrella_ai và calm_room_ai" trong chat; Claude bấm nút Duyệt trên giao diện thay (tên ghi "Chủ dự án (qua chat 2026-10-18)") |
| ui_demo nội dung v2, phiên bản lời v3→v4 | **dữ liệu thử** của Claude khi bấm thử giao diện ("Chủ dự án (thử qua giao diện)" **không phải duyệt thật**) | không có xác nhận của chủ dự án; cảnh a3 hiện bị đánh dấu đổi hình do thêm `subtitles:"auto"` trong lần sửa thử |
| asset `coin_ui` (ui_demo) | **draft** | tạo để thử gửi job; chưa ai duyệt |
| Giọng đọc của mọi video | chưa ai nghe | kiểm tra chỉ là tự động (thời lượng, khoảng lặng, cắt cụt) |

Mọi "duyệt" trong `approval.json`/manifest do Claude ghi lại theo lời chủ dự án trong chat; công cụ chưa có xác thực người duyệt độc lập (ghi tên tự khai). Đó là giới hạn đã biết.

## 4. Kết luận riêng

**Chức năng tool đạt:** tạo dự án/nhập storyboard/kiểm tra/lưu/duyệt/dựng qua giao diện; cổng duyệt gắn bản đúng và chặn lời đã đổi; giọng chỉ gọi API khi có duyệt và chỉ cho cảnh đổi (dùng chung cache giọng); dựng lại có chọn lọc theo phụ thuộc (7 tình huống + 3 dự án chạy lại 0 API); asset AI qua agy có bằng chứng gọi công cụ ảnh, tách nền, manifest, duyệt/loại, dùng trong cảnh bằng `ai:<id>` chỉ khi đã duyệt; MCP: Claude Code phiên thật gọi được cả hai tool và dùng lại kết quả đã có; 54 test phase 2 + 8 test phase 1 đạt.

**Giới hạn đang có (công bố):** nhập storyboard bằng ô JSON (chưa có form); chuyển cảnh chỉ cắt thẳng và fade-out; hành động chỉ tay chỉ tay phải; asset AI chỉ là ảnh tĩnh, chưa gắn khớp, chưa thay được nhân vật Bi có khớp; agy không công bố model ảnh và không báo credit/tiền (chỉ token); tên người duyệt tự khai; số kiểu `1.0` trong phần hình có thể gây báo "đổi hình" dư; không dùng Git (định danh phiên bản bằng manifest mã băm); đường tạo ảnh mới từ Claude Code chưa chạy lại trong phiên thật đợt này.

**Chờ chủ dự án duyệt/hành động:** (1) nhịp `hold_after` năm cảnh video 1 (bảng 3a); (2) asset `coin_ui` (draft; có thể loại) và việc có giữ dữ liệu thử `ui_demo` hay không; (3) nghe/xem thử video và xác nhận giọng; (4) thu hồi API key cũ đã dán trong chat; (5) chuẩn bị chấp nhận hoặc bỏ yêu cầu giới hạn ở trên.

## 5. Vòng sửa lỗi 3 – năm lỗi dùng chung do rà soát mã (agy_jobs / build_storyboard)

Mã sửa: `tools/agy_image.py`, `tools/agy_jobs.py`, `tools/build_storyboard.py`, `ui/server.py`. Test mới: `tests/test_asset_integrity.py` (8 test, bộ giả lập agy, không gọi API trả phí). Mô tả quy tắc: `assets_mcp/README.md` mục "Toàn vẹn job / asset".

| # | Lỗi | Sửa | Test |
|---|---|---|---|
| 1 | `_inflight` chỉ theo `job_id`: dự án thứ hai gửi cùng yêu cầu bị đụng, `TypeError` | khóa theo (đường dẫn dự án, job_id) | `test_same_request_in_two_projects_while_running` |
| 2 | `check()` trả ảnh của yêu cầu mới cho job cũ | `snapshot` theo job + bản đóng băng `versions/`; job cũ báo `superseded` | `test_old_job_never_returns_the_newer_request_result` |
| 3 | cache báo thành công dù file mất | kiểm tra tồn tại + sha256; mất/hỏng → lỗi rõ, không tự tạo lại, không phát sinh phí | `test_cache_does_not_claim_success_for_a_missing_or_changed_file` |
| 4 | ảnh bị thay nội dung vẫn mang duyệt cũ | duyệt ghi `approved_sha256`; bộ dựng/validator chặn `changed_after_approval`; ảnh tạo lại là draft | `test_approval_is_bound_to_the_image_hash`, `..._without_approved_hash_...` |
| 5 | đọc trạng thái lúc đang ghi → lỗi JSON | ghi nguyên tử (`os.replace`), đọc có thử lại, khóa liên tiến trình cho manifest | `test_state_files_are_written_atomically`, `test_checking_while_a_job_changes_state_never_fails`, `test_manifest_updates_from_two_workers_do_not_lose_each_other` |

- Chạy 4 test đầu với bản `agy_jobs.py`/`build_storyboard.py` cũ của người rà soát: `evidence/fixes_round3/tests_against_reviewed_code.txt` – ba test đầu thất bại đúng lỗi mô tả (TypeError; `succeeded != superseded`; không báo lỗi khi mất file). Test số 4 trên mã cũ thất bại do lỗi đọc JSON (không phải đúng lỗi duyệt-theo-hash), nên **không** có bằng chứng "đỏ trước" riêng cho lỗi 4; nó được kiểm bằng test mới sau sửa (thay PNG đã duyệt → `changed_after_approval`, không duyệt được file lạ).
- Tương thích: các job/asset đã có (video 2: `umbrella_ai`, `calm_room_ai`, ảnh heo đất) vẫn `succeeded/approved` (kiểm bằng `check` thật, không gọi agy); bản duyệt cũ không có `approved_sha256` dùng hash manifest. Hồ sơ duyệt asset không có hash nào cả (không có `sha256`) bị coi là không hợp lệ (an toàn).
- Nghiệm thu bằng `ui_demo` (không gọi API: `api_calls 0`, `credits_spent 0`): `produce.py` chạy hết (validate → storyboard → giọng: không cần sinh → video) dùng lại 3/3 cảnh; dựng cưỡng bức `--force` dựng lại 3/3 cảnh; chạy lại không đổi dùng lại 3/3 cảnh. Log: `projects/ui_demo/logs/build_20261018_192947.log`, `..._193004.log` (force), `..._193043.log` (rerun).
- Kiểm thử: 62 test phase 2 + 8 test phase 1 đạt.
- Giới hạn còn lại: gửi lại đúng yêu cầu của job đã `superseded` sẽ gọi agy lại (chưa khôi phục từ `versions/`); khóa manifest chỉ có hiệu lực giữa các tiến trình dùng mã này; chưa chạy lại đường tạo ảnh mới thật bằng agy sau các sửa (chỉ bằng bộ giả lập, theo yêu cầu).

## 6. Vòng sửa lỗi 4 – quản lý job giữa các tiến trình

Mã sửa: `tools/agy_jobs.py` (+ khóa có tên trong `tools/agy_image.py`). Quy tắc: `assets_mcp/README.md` mục "Nhiều tiến trình dùng chung dự án".

- Mỗi job `queued/running` ghi `owner` = pid + dấu thời điểm tạo tiến trình (Windows: `GetProcessTimes`; Linux: `/proc/<pid>/stat`), nên pid tái sử dụng không bị nhầm là chủ. Quyết định gửi/ngắt chạy dưới khóa tệp `ai_assets/.jobs.lock`.
- `check` từ tiến trình khác không đổi job đang chạy thành `interrupted`; chỉ job mồ côi (chủ đã mất) mới `interrupted`.
- `submit` lại khi job còn chạy trả đúng job đó, `run` không tăng, agy không bị gọi lần nữa.
- Test bằng **tiến trình thật** (`tests/test_job_processes.py` + `tests/job_proc_a.py`, bộ giả lập agy, không tạo ảnh/video thật):
  1. A chạy; B (tiến trình kiểm thử) `check` 3 lần = `running`, chủ = pid của A; B gửi lại → cùng job, `run 1`; bộ giả lập được gọi **đúng 1 lần** (do A), 0 lần từ B; thả A → `succeeded`; gửi lại → dùng kết quả đã lưu, vẫn 1 lần gọi.
  2. Hai tiến trình gửi cùng lúc → chỉ một chạy (1 lần gọi), tiến trình kia nhận job hiện có.
  3. A bị kill giữa lúc chạy → B `check` = `interrupted` (có thông báo); B gửi lại → `run 2`, chủ = B, chạy xong `succeeded`; tổng gọi: 1 (A, chết) + 1 (B).
  4. Cùng pid nhưng dấu tiến trình khác (pid tái sử dụng) → coi là mồ côi, `interrupted`.
- Trên mã `agy_jobs.py` cũ, test 1 và 2 thất bại đúng lỗi (`'interrupted' != 'running'`; hai tiến trình đều chạy: 2 lần gọi thay vì 1): `evidence/fixes_round3/process_tests_against_previous_agy_jobs.txt`.
- Job/asset sẵn có (video 2, ui_demo) vẫn đọc đúng (bản ghi cũ không có `owner` vẫn dùng được).
- Kiểm thử: 66 test phase 2 + 8 test phase 1 đạt.
- Giới hạn: agy có thể chạy song song giữa các tiến trình khác nhau với các yêu cầu khác nhau (chưa có khóa chạy agy toàn máy); khóa tệp coi khóa quá 60 giây là của tiến trình đã chết; bản ghi job không có `owner` chỉ tiến trình đang chạy nó mới xác nhận được.
