# Video 2 – bằng chứng nghiệm thu quy trình sản xuất (2026-10-18)

| Tình huống | Kết quả | Bằng chứng |
|---|---|---|
| 1. Hai video khác kịch bản, chung bộ công cụ, không sửa code | **Đạt.** Video 2 tạo bằng dữ liệu mới (8 cảnh, bố cục khác: Bi đứng bên phải, nhãn tự giãn, biểu đồ 2 cột). Trong lúc sản xuất, băm mã `tools/` + `lib/` không đổi (`status.json`: `frozen_code_hash` = `code_hash`, `code_changed_since_freeze: false`). | `status.json`, `logs/produce_*.log` |
| 2. Video 60–90 s, 6–10 cảnh | **Chưa đạt độ dài:** 8 cảnh, **55,5 s**. Ước tính trước là 61,3 s (lệch 9%: tốc độ đọc video này nhanh hơn mẫu hiệu chỉnh). Bộ kiểm tra báo FAIL đúng. | `logs/build_report.json` |
| 3. Duyệt kịch bản/storyboard trước khi gọi API | Đạt: `approval.json` ghi băm từng cảnh; trước duyệt `produce.py` dừng `awaiting_approval`. (Giao diện duyệt chưa làm.) | `approval.json`, `versions/` |
| 4. Chạy lại nguyên đầu vào không gọi API thêm | **Đạt:** chạy lại 3 lần, `api_calls` giữ 8; mọi cảnh "SKIP voice", mọi clip "REUSE". | `logs/voice_*.log`, `logs/build_*.log` |
| 5. Sửa hành động một cảnh | **Đạt (thử trên bản sao):** đổi hành động cảnh 3 → chỉ dựng lại `s03` (2,2 s), 7 cảnh khác tái sử dụng, timeline vẫn đạt mọi kiểm tra. | log dựng của bản sao |
| 6. Sửa một câu thoại | **Chốt chặn đạt, chưa chạy API thật:** sửa lời cảnh 5 → `REFUSED` cho tới khi duyệt lại; sau khi duyệt lại, kế hoạch gửi API là **1 cảnh (114 ký tự, ≈83 credit), 7 cảnh không gửi**. Logic tạo lại một cảnh được kiểm thử bằng API giả (`tests/test_voice_project.py`). Chưa tốn credit để chạy thật. | dry-run, tests |
| 7. Dự án không ghi đè dự án khác | **Đạt:** không có tệp nào của video 1 bị sửa sau khi video 2 được duyệt; mỗi dự án có thư mục `assets/` riêng; `api_calls`/`credits` của video 1 giữ 9/593. | so sánh thời gian sửa tệp |
| 8. Đóng gói, mở lại, chỉnh sửa được | **Đạt:** `ops/package_project.py` → zip 20 MB không có `.env`; giải nén vào thư mục mới, `REBUILD`: tái sử dụng clip chạy, và `--force` dựng lại từ đầu cho **khung hình giống từng điểm ảnh** với bản gốc ở 8 mốc thời gian. Mở `scenes.ecproj` trong gói, đổi khớp vai/khuỷu tay → hình thay đổi đúng vùng tay. | các lệnh trong báo cáo |
| Chi phí giọng | 8 job, **583 credit thực tế** (dự toán đã duyệt ≈582). | `status.json`, `work/api_calls.jsonl` |

## Lỗi tìm thấy nhờ video 2 và đã sửa ở thành phần chung
Khung nhãn (`pills`) tràn khi chữ dài; tiêu đề/nhãn biểu đồ chạm viền bảng; chữ chưa căn giữa theo chiều dọc trong nhãn/chú giải; chữ ký dựng lại phụ thuộc toàn bộ hình (đã đổi sang chỉ hình cảnh dùng); phụ đề hai đoạn cùng hiện mờ ~2 khung hình ở ranh giới (đã sửa). Các sửa này làm **sau khi** sản xuất video 2 hoặc trước khi tạo giọng, và cả hai video đã dựng lại bằng mã mới (băm mã hiện tại được ghi lại; không cần gọi API).
Mã nhà phát triển thêm sau đó chỉ nằm trong `ops/` (tiện ích bằng chứng, không thuộc đường sản xuất).
