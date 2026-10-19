# Phase 3 – dựng lại có chọn lọc, chạy THẬT trên bản sao `thu_thay_asset` (sao chép từ dự án đã có giọng thật)

Dự án gốc `lap_ngan_sach_chi_tieu_hang_th` (7 cảnh, 80,2 s, giọng thật 7 lượt / 743 credit) KHÔNG bị đụng; mọi thao tác dưới đây chạy trên bản sao. Người duyệt "Claude (kiểm thử, không phải chủ dự án)" là thao tác thử.

## Thay một asset (yêu cầu: chỉ cảnh dùng asset dựng lại, giọng giữ nguyên)
1. Góp ý ảnh `notebook_ai` ("vẽ cuốn sổ màu xanh dương, bìa dày hơn, không có bút chì, trên nền trắng") → AI (Gemini 3.8 Flash Low) đề xuất prompt mới → áp dụng → **1 job tạo ảnh thật qua Antigravity** → ảnh mới là bản *nháp*.
2. Duyệt ảnh mới → dựng lại: `rendered ['s03'] | reused ['s01','s02','s04','s05','s06','s07']`, **API giọng: 7 lượt trước và sau (0 lượt thêm)**. Log: `projects/thu_thay_asset/logs/build_20261018_2119*.log`.
3. Lần thử đầu cùng thao tác cho thấy hai lỗi đã sửa: (a) mô hình trả cả đối tượng JSON trong trường `prompt` → tool tách ra và từ chối prompt "nhại lại hướng dẫn"; (b) tạo lại ảnh bị lỗi nền trong suốt từng ghi đè mục asset đã duyệt bằng trạng thái `failed` → nay ảnh/duyệt cũ được giữ nguyên, lỗi lưu cạnh (`last_failure`), ảnh mới ghi ra tệp tạm và chỉ thay khi đạt (test `test_failed_regeneration_never_destroys_the_good_approved_asset`).

## Sửa một lời thoại (yêu cầu: hiển thị phần ảnh hưởng, yêu cầu duyệt lại đúng phần, chỉ tạo lại giọng cần thiết)
1. Sửa lời cảnh s05 (thêm một câu): `realigned 0` (các mốc vẫn khớp), phiên bản lưu mới.
2. Việc chờ bạn: "Duyệt lại lời đọc: s05" và "Duyệt lại hình/hành động: s05" — không cảnh nào khác.
3. Tạo giọng trước khi duyệt lại: `REFUSED: voice text/settings changed after approval in scenes ['s05']` (không gọi API).
4. Sau khi duyệt lại lời đọc, kế hoạch (dry-run): `1 scene(s) to generate (202 chars, est. ~146 credits), 0 from the shared voice cache, 6 unchanged (no API call)`. **Lần tạo giọng thật chưa chạy** (sẽ tốn ~146 credit; chưa có lệnh của chủ dự án).
