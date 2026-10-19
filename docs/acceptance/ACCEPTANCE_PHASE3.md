# Phase 3 – Báo cáo nghiệm thu (từ brief đến video qua giao diện, bạn giữ vai trò duyệt)

Nền: Phase 2 đã nghiệm thu (+ phụ lục vòng sửa 3, 4). Hướng dẫn dùng: `HUONG_DAN_PHASE3.md`. Cấu hình AI: `config.example.json` mục `ai`. Hồ sơ kênh mẫu: `channels/default.json`.
Kiểm thử tự động: **phase 2: xem `evidence/tests_log.txt` (+ 8 test phase 1)** (`evidence/tests_log.txt`). Lần chạy thật: `evidence/phase3/real_runs.md`.

## 1. Đã xây (theo ba chặng)

**Chặng 1 – giao diện giao việc và duyệt** (`ui/server.py`, `ui/static/index.html`): 7 tab — Tổng quan (brief, việc chờ bạn duyệt, lỗi, nút "AI chuẩn bị"), Kịch bản (nguồn tra cứu, sửa lời, góp ý toàn bài/từng cảnh, "Nhờ AI sửa" có bảng thay đổi, duyệt lời đọc), Storyboard (form từng cảnh: lời, ảnh xem trước, nhân vật, hành động, hình/biểu đồ, nền, thời lượng ước tính — chỉ cho chọn những gì tool hỗ trợ, lấy từ `capabilities.py`), Asset (ảnh lớn, "Xem trong cảnh", duyệt/loại, tạo lại có góp ý, kế hoạch asset), Sản xuất (tiến độ từng bước, việc chờ bạn, lỗi theo bước, chi phí/hạn mức, job, chạy tiếp), Kết quả (video, góp ý, lịch sử duyệt, **gói bàn giao .zip**), Hồ sơ kênh. Dữ liệu và trạng thái nằm trong thư mục dự án; tải lại trang/khởi động lại server không mất gì (test `test_11`).
Sửa lời → `realign.py` tự dò lại mốc hành động/hiện hình theo cụm từ (thay cụm tương tự; không còn thì chuyển sang thời điểm gần đúng) + phụ đề tạo lại; danh sách thay đổi hiện ra để bạn kiểm tra.

**Chặng 2 – AI vào quy trình** (`llm.py`, `research.py`, `prepare.py`, `revise.py`, `capabilities.py`, `layout.py`, `budget.py`, `aiconfig.py`):
- Kết nối LLM: **Antigravity `agy` headless, đầu ra có cấu trúc (`--json-schema`)** — đã chạy thật. Provider/model trong cấu hình: `cheap` = Gemini 3.8 Flash (Low) cho phân loại/trích xuất/kế hoạch asset/sửa lỗi cấu trúc; `quality` = Claude Sonnet 4.6 cho kịch bản, storyboard, xử lý góp ý; `fallback` 1 lần.
- Nghiên cứu: phân loại có cần tra cứu không → tìm nguồn bằng công cụ web-search của agy → **tool tự mở từng URL, lưu URL cuối + thời điểm truy cập, đối chiếu trích dẫn/số liệu với nội dung trang**; không có căn cứ thì đánh dấu "thiếu căn cứ" (bạn chấp nhận/loại) và **không đưa vào lời kịch bản**.
- Kịch bản từ brief + hồ sơ kênh (+ dự toán thời lượng, một lần chỉnh độ dài nếu lệch mục tiêu); hoặc kịch bản bạn nhập sẵn (AI không viết lại).
- Storyboard: AI chỉ chọn từ danh mục của tool; kết quả phải qua `validate_storyboard`: sửa mốc tự động (không cần AI) → tối đa 2 vòng AI sửa lỗi → 1 vòng AI sửa chồng lấn bố cục (`layout.py`). Lời đọc của storyboard luôn đúng văn bản kịch bản.
- Kế hoạch asset: ưu tiên dùng lại asset đã duyệt của dự án khác (0 ảnh), chỉ đề xuất tạo mới khi cần; tạo qua **cùng lớp job `agy_jobs` mà MCP dùng** (UI và MCP thấy chung job/kết quả, test `test_ui_and_mcp_share_job_state`); ảnh mới là bản nháp; chỉ ảnh đã duyệt (theo mã băm) mới vào cảnh; đưa vào cảnh tự tránh chồng lấn.
- Sửa theo góp ý: đề xuất → bảng trước/sau → bạn bấm Áp dụng (phiên bản mới, bản cũ giữ); đề xuất cũ so với nội dung đã đổi bị từ chối; đề xuất không hợp lệ không áp dụng được.
- Chi phí: sổ cái `logs/ai_ledger.jsonl` (model thực tế đọc từ log agy, token, giây, trạng thái; dùng lại kết quả ghi `cache`), hạn mức lượt gọi / token / lượt ảnh / credit giọng đọc (mặc định + riêng từng dự án), kiểm tra **trước khi bắt đầu**; retry có giới hạn (1 thử lại + 1 model dự phòng); tiền hiển thị "chưa biết" vì agy chỉ báo token (đặt `price_per_1k_tokens` để ước tính).

**Chặng 3 – điều phối** (`approve.py`, `agy_slots.py`, `overview.py`, `export_project.py`, `produce.py`): duyệt theo loại (lời đọc / storyboard / kế hoạch asset / từng asset) gắn mã băm, lịch sử duyệt `approvals_history.jsonl`; giọng chỉ tạo khi lời đọc đã duyệt và vừa credit, video chỉ dựng khi storyboard đã duyệt; **giới hạn số lượt agy chạy đồng thời trên cả máy (mặc định 1, dùng chung UI/MCP/CLI, chủ chết thì nhường)**; tiến trình AI bị ngắt hiện là `interrupted`, chạy tiếp không lặp bước đã xong; xuất gói bàn giao.

## 2. Bài nghiệm thu

| Bài | Trạng thái | Bằng chứng |
|---|---|---|
| Một dự án mới: brief → video 60–90 s, có giọng, ≥1 asset Antigravity mới, thao tác trên giao diện | **Đạt**: dự án `lap_ngan_sach_chi_tieu_hang_th` — brief nhập trên giao diện → AI chuẩn bị (kịch bản 7 cảnh, storyboard, kế hoạch asset) → **asset mới `notebook_ai` tạo thật qua Antigravity** (+ 2 asset dùng lại) → **chủ dự án (Khoa) duyệt lời đọc + storyboard trên giao diện** → "Chạy sản xuất" → **giọng thật 7 lượt / 743 credit** → video **80,2 s, 1920×1080, có âm thanh, 11/11 kiểm tra tự động đạt**. Lưu ý: tạo dự án, bấm "AI chuẩn bị", tạo/đưa asset do tôi thao tác trên giao diện (thử); phần duyệt nội dung là của chủ dự án; asset đang ghi "đã duyệt" do tôi (thử) — chủ dự án nên duyệt lại | `evidence/phase3/real_runs.md`, `projects/lap_ngan_sach_chi_tieu_hang_th/output/*.mp4`, `evidence/phase3/lap_ngan_sach_chi_tieu_hang_th_contact_sheet.png` |
| Brief thứ hai | **Đạt** (thật): 2 brief khác chủ đề → kịch bản + storyboard hợp lệ, cùng bộ tool, không sửa code theo dự án | `real_runs.md` (2 dự án); `test_two_different_briefs_...` |
| Sửa một lời thoại | **Đạt (thật, trừ bước trả phí cuối)**: trên bản sao có giọng thật, sửa lời cảnh s05 → chỉ s05 cần duyệt lại lời và storyboard; tạo giọng trước khi duyệt bị từ chối; sau duyệt, kế hoạch = **1 cảnh (~146 credit), 6 cảnh giữ nguyên, 0 lượt API cho phần còn lại**. Lần tạo giọng thật cho cảnh đó chưa chạy (chờ lệnh của bạn). Cộng test tự động với giọng giả lập | `evidence/phase3/selective_rebuild.md`, `test_edit_one_line_shows_impact_and_regenerates_only_that_voice` |
| Thay một asset | **Đạt (thật)**: trên bản sao, góp ý ảnh → AI đề xuất prompt → tạo lại ảnh thật qua Antigravity → duyệt → dựng lại: **chỉ s03 dựng lại, 6 cảnh còn lại dùng lại, giọng 0 lượt API thêm** | `evidence/phase3/selective_rebuild.md` |
| Chạy lại không đổi | **Đạt** (thật + test): chạy lại AI chuẩn bị → mọi bước "đã có", 0 lượt gọi AI; giọng 0 lần; job ảnh dùng lại | `test_unchanged_rerun_calls_nothing_at_all`, `test_rerun_after_assets_and_edits_...`, `test_07` |
| Lỗi và phục hồi | **Đạt** (tiến trình thật bị kill giữa lúc gọi AI): hiện `interrupted`, không ghi nửa chừng, chạy tiếp không lặp bước đã xong, không job trùng (Phase 2 vòng 4) | `test_preparation_process_crash_...`, `test_job_processes` |
| Giới hạn chi phí | **Đạt**: vượt hạn mức bị từ chối trước khi bắt đầu, giải thích trên giao diện (lượt gọi AI, ảnh, credit giọng); sửa hạn mức rồi chạy tiếp chỉ làm phần còn thiếu | `test_budget_*`, `test_limits_refuse_to_start_and_say_why`, `test_08` |

## 3. Lỗi tìm thấy khi chạy thật và đã sửa (đều ở mã dùng chung, có test)
- **Chạy lại "AI chuẩn bị" trên dự án đã có asset/đã chỉnh sửa làm AI viết đè storyboard và kế hoạch asset** (do đầu vào bước phụ thuộc danh sách asset/thư viện thay đổi sau mỗi lần duyệt). Sửa: đầu vào chỉ còn kịch bản + hồ sơ kênh; storyboard đã bị sửa/duyệt sau khi AI viết thì **không bị ghi đè nếu không `force`**; kế hoạch asset đã duyệt cũng vậy; kế hoạch cũ được lưu trong `prepare/history/`. Dữ liệu thử của tôi bị ảnh hưởng đã được khôi phục (ghi rõ trong `real_runs.md`: sổ cái có thêm lượt gọi do lỗi này).
- Brief có trường `null` (từ form) làm bước kịch bản lỗi → chuẩn hóa brief.
- Chồng lấn bố cục trong storyboard AI (chữ đè hóa đơn…) → `layout.py` + một vòng AI sửa + đưa asset vào cảnh tự tránh chồng lấn.
- Test cũ của UI giả định dự án mới có cảnh mẫu → viết lại cho luồng brief.

## 4. Giới hạn đang có (công bố)
- Dự án “Có nên trả nợ sớm…” chưa tạo giọng (≈ 800 credit, hạn mức mặc định 900); dự án “Lập ngân sách…” đã tạo giọng thật (743 credit).
- agy không báo tiền, không công bố model ảnh; chi phí tiền "chưa biết". Gemini 3.8 Flash (Low) có độ trễ cao (suy luận) — cấu hình đổi được.
- Tra cứu: URL nguồn do công cụ tìm kiếm trả về thường là trang gốc của site (không phải bài cụ thể); tool đối chiếu được nội dung trang nên phần lớn thông tin bị đánh dấu "thiếu căn cứ" và chờ bạn quyết — an toàn nhưng cần thao tác tay.
- AI sinh storyboard vẫn có thể xếp hình chưa đẹp (chỉ bắt được chồng lấn một phần, không đánh giá thẩm mỹ); nền AI (ảnh) có thể trùng với hình tool đặt lên — chưa kiểm được va chạm giữa hình và nền AI.
- Sửa lời bằng form chỉ tự dò lại mốc theo cụm từ; thay đổi lớn về ý có thể cho mốc "gần đúng" cần bạn xem lại.
- Chưa có rigging nhân vật AI, chuyển cảnh chỉ cắt thẳng/mờ dần, chỉ tay phải; tên người duyệt tự khai; hai tiến trình khác nhau vẫn dùng khóa tệp (không xác thực người dùng).
- agy chạy tuần tự (1 slot): một dự án mất ~5–6 phút cho phần AI (7–8 lượt) và ~1,5 phút mỗi ảnh.

## 5. Chờ bạn quyết định
1. Xem video `projects/lap_ngan_sach_chi_tieu_hang_th/output/lap_ngan_sach_chi_tieu_hang_th_v5_preview.mp4` (80,2 s), nghe giọng; duyệt lại 3 asset (hiện ghi "đã duyệt" do thao tác thử của tôi).
2. Có muốn chạy **lần tạo giọng thật cho cảnh s05 của bản sao** (~146 credit) để hoàn tất bằng chứng "sửa lời" không (không bắt buộc).
3. Duyệt/loại các thông tin “thiếu căn cứ” và 2 điểm AI đánh dấu của dự án “Có nên trả nợ sớm…”.
4. Thu hồi API key cũ (đã dán trong chat).

## 6. Lỗi tìm thấy trong lúc chạy sản xuất thật (đã sửa ở mã dùng chung)
- Dựng video đầu tiên báo 2 kiểm tra FAIL: khớp khuỷu "giật" 126°/khung ở cảnh mở đầu vì hai hành động (`enter` và một hành động theo cụm từ) chồng thời gian → `lib/scene_anim.jsx` xếp các hành động nối tiếp, không chồng nhau; thời lượng 80,2 s nằm ngoài cửa sổ brief 70 s ±10 → cửa sổ = brief ±15 s và hiệu chỉnh lại tốc độ đọc từ 25 job thật. Sau sửa: 11/11 đạt, không tạo lại giọng.
- Tạo lại ảnh thất bại không còn phá asset đã duyệt (xem `selective_rebuild.md`); đề xuất prompt ảnh được kiểm tra (không nhại hướng dẫn, tách JSON lồng).
