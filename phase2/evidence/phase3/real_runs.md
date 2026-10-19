# Phase 3 – các lần chạy THẬT (agy: Gemini + Claude qua Antigravity; tạo ảnh thật qua Antigravity)

Số liệu đọc từ thư mục dự án (`logs/ai_ledger.jsonl`, `prepare/*.json`, `ai_assets/manifest.json`). Dự án `co_nen_tra_no...` chưa gọi API giọng nói; dự án `lap_ngan_sach...` đã gọi API giọng nói thật sau khi chủ dự án (Khoa) duyệt.

## co_nen_tra_no_som_hay_dau_tu_t
- Brief: “Có nên trả nợ sớm hay đầu tư thêm?” · mục tiêu: Người xem biết cách so sánh lãi vay với lợi nhuận kỳ vọng trước khi quyết định · thời lượng mong muốn 75 s · nghiên cứu: yes
- Kịch bản: {'scenes': 8, 'chars': 1102, 'est_seconds': 78.2} · nguồn: ai · model: Claude Sonnet 4.6 (Thinking)
- Storyboard: v2, 8 cảnh, kiểm tra hợp lệ: 0 lỗi, 8 cảnh báo
- Lượt gọi AI (đã tính, không kể dùng lại): 6 · token 142,149 · lượt ảnh 0 · credit giọng 0
- Model thực tế: Gemini 3.8 Flash (Low) (4 lượt, 90,496 token, 0 lỗi); Claude Sonnet 4.6 (Thinking) (2 lượt, 51,653 token, 0 lỗi)
- Tiền: chưa biết: nhà cung cấp chỉ trả số token (agy không báo tiền); đặt price_per_1k_tokens trong config để ước tính

| Việc | Tầng | Model thực tế | Token | Giây | Kết quả |
|---|---|---|---|---|---|
| research_classify | cheap | Gemini 3.8 Flash (Low) | 24856 | 13.0 | ok |
| research_facts | cheap | Gemini 3.8 Flash (Low) | 38374 | 44.9 | ok |
| script | quality | Claude Sonnet 4.6 (Thinking) | 16841 | 40.8 | ok |
| storyboard | quality | Claude Sonnet 4.6 (Thinking) | 34812 | 76.4 | ok |
| asset_plan | cheap | Gemini 3.8 Flash (Low) | 13535 | 8.3 | ok |
| asset_plan | cheap | Gemini 3.8 Flash (Low) | 13731 | 10.4 | ok |

Kế hoạch asset (AI lập, bạn duyệt):

- `calm_room_bg` (background) cảnh s01: dùng lại từ lap_ngan_sach_chi_tieu_hang_th/calm_room_ai
- `umbrella_prop` (prop) cảnh s05: dùng lại từ video2_quy_khan_cap/umbrella_ai
- `piggy_prop` (prop) cảnh s07: dùng lại từ lap_ngan_sach_chi_tieu_hang_th/piggy_ai

Việc đang chờ chủ dự án:

- 6 thông tin chưa có căn cứ — chấp nhận hoặc loại bỏ
- 2 điểm AI đánh dấu cần kiểm chứng
- Duyệt lại hình/hành động: s01, s02, s03, s04, s05, s06, s07, s08
- Duyệt kế hoạch tạo 0 asset mới

Ảnh tổng quan các cảnh (khung đầu mỗi cảnh, dựng thật bằng EffectCraft): `evidence/phase3/co_nen_tra_no_som_hay_dau_tu_t_contact_sheet.png`

## lap_ngan_sach_chi_tieu_hang_th
- Brief: “Lập ngân sách chi tiêu hàng tháng cho người mới đi làm” · mục tiêu: Người xem biết chia thu nhập thành các nhóm chi tiêu và theo dõi hằng tháng · thời lượng mong muốn 70 s · nghiên cứu: no
- Kịch bản: {'scenes': 7, 'chars': 1034, 'est_seconds': 73.1} · nguồn: ai · model: Claude Sonnet 4.6 (Thinking)
- Storyboard: v5, 7 cảnh, kiểm tra hợp lệ: 0 lỗi, 3 cảnh báo
- Lượt gọi AI (đã tính, không kể dùng lại): 8 · token 205,089 · lượt ảnh 1 · credit giọng 743
- Model thực tế: Claude Sonnet 4.6 (Thinking) (4 lượt, 88,472 token, 0 lỗi); Gemini 3.8 Flash (Low) (4 lượt, 116,617 token, 0 lỗi)
- Tiền: chưa biết: nhà cung cấp chỉ trả số token (agy không báo tiền); đặt price_per_1k_tokens trong config để ước tính

| Việc | Tầng | Model thực tế | Token | Giây | Kết quả |
|---|---|---|---|---|---|
| script | quality | Claude Sonnet 4.6 (Thinking) | 16283 | 35.7 | ok |
| script_fit | quality | Claude Sonnet 4.6 (Thinking) | 6785 | 23.4 | ok |
| storyboard | quality | Claude Sonnet 4.6 (Thinking) | 32549 | 64.7 | ok |
| storyboard_repair | cheap | Gemini 3.8 Flash (Low) | 27761 | 9.4 | ok |
| asset_plan | cheap | Gemini 3.8 Flash (Low) | 13473 | 7.8 | ok |
| asset notebook_ai | image | Gemini 3.8 Flash (High) | 57268 | 86.2 | ok |
| storyboard | quality | Claude Sonnet 4.6 (Thinking) | 32855 | 66.4 | ok |
| storyboard_repair | cheap | Gemini 3.8 Flash (Low) | 45550 | 67.9 | ok |
| asset_plan | cheap | Gemini 3.8 Flash (Low) | 29833 | 12.2 | ok |

Kế hoạch asset (AI lập, bạn duyệt):

- `piggy_ai` (prop) cảnh s04: dùng lại từ video2_quy_khan_cap/piggy_ai
- `calm_room_ai` (background) cảnh s07: dùng lại từ video2_quy_khan_cap/calm_room_ai
- `notebook_ai` (prop) cảnh s03: TẠO MỚI qua Antigravity — “a small open notebook or blank notepad with a pencil resting beside it, simple lined paper”
- Asset tạo thật: `notebook_ai` · Gemini 3.8 Flash (High) · PNG [600, 437] · trong suốt: {'ok': True, 'corner_alpha': [0, 0, 0, 0], 'opaque_fraction': 0.745, 'edge_transparent_fraction': 1.0} · conversation `ef770bf1-e9a0-4cc8-81bd-3349bba8beec` · trạng thái approved

Video: lap_ngan_sach_chi_tieu_hang_th_v5_preview.mp4 · kiểm tra tự động: 11/11 đạt
  - PASS video 1920x1080 with audio 
  - PASS duration within 55-85 s 80.2s
  - PASS scene count within 6-10 7 scenes
  - PASS timeline has exactly one video and one audio clip per scene (no duplicates) video 7, audio 7
  - PASS video clips are contiguous (no gaps/overlaps) max |gap| 0.000s
  - PASS each voice clip starts `lead` s into its scene and ends inside it 
  - PASS silence between scenes <= 0.85 s (<= 1.5 s after scenes that hold a chart/summary) gaps [0.66, 0.7, 0.69, 0.67, 0.68, 0.67]
  - PASS no speech trimmed: every voice clip keeps >= 0.1 s after the last word []
  - PASS subtitles: inside scene, in order, no overlap, <= 56 chars 
  - PASS all cue-driven actions/appear times fall inside their scene 
  - PASS motion QA on all scenes (joint limits, no snaps/flips, arms never through torso) 

Giọng đọc THẬT: 7 lượt gọi API, 743 credit thực tế (dự toán ~740).


Việc đang chờ chủ dự án:


Ảnh tổng quan các cảnh (khung đầu mỗi cảnh, dựng thật bằng EffectCraft): `evidence/phase3/lap_ngan_sach_chi_tieu_hang_th_contact_sheet.png`

## Ghi chú trung thực
- Các dòng `asset_plan` thứ hai (cả hai dự án) và `storyboard` + `storyboard_repair` thứ hai (dự án `lap_ngan_sach...`) trong sổ cái đến từ MỘT LỖI tìm thấy khi chạy thật: chạy lại 'AI chuẩn bị' sau khi asset đã được duyệt/đưa vào cảnh làm AI lập lại kế hoạch và viết đè storyboard. Lỗi đã sửa (đầu vào các bước chỉ còn kịch bản + hồ sơ kênh; storyboard/kế hoạch đã sửa hoặc duyệt không bị ghi đè nếu không `force`; kế hoạch cũ lưu ở `prepare/history/`) và có test hồi quy. Storyboard của dự án `lap_ngan_sach...` đã được khôi phục từ bản lưu trong `versions/` (v2 → v4); kế hoạch asset dựng lại từ manifest.
- Dự án `co_nen_tra_no...`: bảng kế hoạch asset hiện tại là bản lập lại do lỗi trên (3 asset dùng lại, 0 asset mới); chưa có ảnh nào được tạo cho dự án này.
- Lần dựng video đầu của `lap_ngan_sach...` (80,2 s) báo 2 kiểm tra FAIL: (1) kiểm tra chuyển động — khớp khuỷu phải xoay 126°/khung ở cảnh s01 vì hai hành động (`enter` và `cheek` theo cụm từ) chồng lên nhau; (2) thời lượng 80,2 s ngoài cửa sổ 60–80 s suy ra từ brief 70 s. Đã sửa ở mã dùng chung: hành động không còn chồng nhau (`lib/scene_anim.jsx`: hành động sau bắt đầu ngay khi hành động trước kết thúc), cửa sổ thời lượng = brief ±15 s, hiệu chỉnh lại tốc độ đọc từ 25 job thật (`tools/calibrate.py`: 15,28 ký tự/giây). Sau đó 11/11 kiểm tra đạt mà không tạo lại giọng (0 lượt gọi API thêm).
- Người duyệt 'Claude (kiểm thử, không phải chủ dự án)' là thao tác thử của tôi, không phải duyệt của chủ dự án.

