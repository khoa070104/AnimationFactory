# Chặng 1 — sửa theo review (commit 677a84b)

Mỗi mục: lỗi reviewer nêu → cách sửa → test tái hiện (`phase2/tests/test_review1.py`, trừ khi ghi khác). Tất cả chạy từ **bản clone sạch** (183 test Python + 22 test node đều đạt; cần `npm ci` trong `phase2/remotion`).

| # | Lỗi | Sửa | Test |
|---|---|---|---|
| 1 | Clone sạch không chạy `af.py capabilities` (`.gitignore` nuốt `style/tokens.json`) | thu hẹp quy tắc credential; đưa `tokens.json`, PNG rig đã duyệt, ảnh/dữ liệu của 3 project mẫu vào Git; `.gitattributes` giữ nguyên byte của baseline | `test_repo_hygiene.test_files_the_code_needs_to_start_are_tracked`; chạy lại toàn bộ test trong clone mới |
| 2 | Hai CLI lưu/dựng cùng lúc: cả hai báo ok, mất một thay đổi; job trùng/ID trùng | `tools/projlock.py` (khóa liên tiến trình + luồng, dùng chung CLI/MCP/UI); `sbstore.save` kiểm tra hash và ghi nguyên tử **trong khóa**; đăng ký job nguyên tử, ID có hậu tố ngẫu nhiên; preview giữ khóa `build` | `test_two_processes_saving_at_once…` (3 vòng, 2 tiến trình đồng bộ giờ), `test_two_concurrent_job_starts…` |
| 3 | Validator shot bỏ lọt lỗi thời gian | kiểm tra cấu trúc (kiểu dữ liệu, `end` không có trong lời, `end<=start`, thứ tự cụm, `focus` phải là vùng 4 số) + kiểm tra lại **sau khi đổi cue thành giây** (`timing_problems`: tăng chặt, trong cảnh, `start<end`, ease vừa khoảng tới shot sau); `resolve` từ chối bằng `ShotError` có mã/scene/shot/field; khoảng trống chỉ quay về toàn cảnh trong phần thời gian còn lại | `test_timing_holes…`, `test_structural_shot_errors…`, `test_preview_reports_a_shot_timing_error…` |
| 4 | QA hỏng vẫn `status: ok` | `QA_FAILED` → `needs_changes`, mã thoát 2, kèm `failed_checks`; vẫn trả clip nháp; job nền có trạng thái `needs_changes`; `paid_calls_this_run` luôn là số | `test_failed_qa_is_needs_changes…`, `test_paid_calls_is_always_a_number` |
| 5 | “Cô lập tiêu điểm” ẩn cả nhãn screen, và ẩn đến hết khoảng tới shot sau | bỏ qua lớp `screen`; cửa sổ ẩn = đúng thời lượng shot (`end` nếu sớm hơn); dữ liệu điều khiển: `item.keep`, `item.hide_in:[shot]`, `nhân vật.keep` | `test_isolation_respects…` |
| 6 | Lỗi JSON ở cửa vào | `INVALID_JSON`, `BAD_FILE`, `BAD_PROJECT_NAME` (cùng quy tắc với hàm tạo), `PROJECT_EXISTS`, `INTERNAL_ERROR`; scene id bất kỳ (không cần bắt đầu bằng `s`) được định vị; lỗi `TypeError` trong tool không bị che thành lỗi đối số | `test_bad_input_returns_json_errors`, `test_scene_ids_need_not_start_with_s` |

## Góp ý về hình (clip v7)
| Mốc | Sửa trong thành phần dùng chung |
|---|---|
| Thẻ tick xanh cho tình huống giao nhầm | `notice.icon`: `check` (mặc định) / `warn` / `info` / `none` — chọn theo ý nghĩa; thẻ tự rộng ra khi chữ dài (không tràn) |
| Camera lướt qua kệ, tường trước khi tới Linh | cách vào shot: `cut`/`ease` của dữ liệu luôn thắng; mặc định đoạn ngắn lướt 0,5 s, đoạn dài (chủ thể xa, đổi cỡ lớn, shot không phải wide) là **cắt** |
| Shot phản ứng thừa khoảng trống phía trên | nhân vật ở cận/trung được đặt với headroom 14 % và chừa chỗ về phía nhìn (`gaze`) |
| Phụ đề tách riêng “xóm.” | chia phụ đề: đoạn cuối ngắn do dòng trước bị cắt vì dài được gộp và chia lại cân bằng |
| Tuấn/Linh đổi chỗ | `compose` giữ nguyên bên đứng theo dữ liệu (đổi x để đổi chỗ); `ops/chang1_demos.py story --variant` = cùng sample, đổi chỗ + nhãn khác dài hơn + lời dài hơn, **không sửa mã** |

Không đổi (Chặng 2): quay đầu/hướng mắt thật, nhãn bám theo vật, tiếp xúc/che khuất. Chưa làm: ảnh trước–lúc–sau sự kiện trong preview, thành phần vẽ dần thanh/đường, CLI thứ hai và MCP qua phiên Claude thật (vẫn chờ chủ dự án duyệt MCP).
