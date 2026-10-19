# Hướng dẫn ngắn – Phase 3: từ brief đến video qua giao diện

Mở giao diện: chạy `phase2\ui\ui.bat` (hoặc `python phase2\ui\server.py`), mở địa chỉ in ra. Nhập **tên bạn** ở ô "Người duyệt" trên cùng (ghi vào lịch sử duyệt).

## Luồng 7 bước (mỗi bước là một tab / nút)
1. **Hồ sơ kênh** (tab *Hồ sơ kênh*, làm một lần): đối tượng, giọng văn, phong cách hình, nhân vật, điều cần tránh, thông điệp định hướng, giọng đọc, mục tiêu thời lượng. Dùng lại cho mọi video của kênh.
2. **Dự án mới** (nút *+ Dự án mới*): chủ đề, mục tiêu, thông điệp, thời lượng, tài liệu tham khảo, ngân sách; hoặc dán kịch bản có sẵn (AI sẽ không viết lại).
3. **AI chuẩn bị** (tab *Tổng quan*): nghiên cứu nguồn → kịch bản → storyboard → kế hoạch asset. Dừng ở chỗ cần bạn duyệt.
4. **Bạn duyệt**: tab *Kịch bản* (sửa lời, góp ý, nhờ AI sửa, chấp nhận/loại thông tin thiếu căn cứ, **Duyệt lời đọc**); tab *Asset* (**Duyệt kế hoạch** tạo ảnh).
5. **Tạo asset** (tab *Asset* → "Tạo asset theo kế hoạch"): ảnh mới là bản nháp; xem ảnh lớn/"Xem trong cảnh", **Duyệt/Loại** từng ảnh, "AI đề xuất prompt mới" theo góp ý. Rồi "Đưa asset đã duyệt vào cảnh".
6. **Storyboard** (tab *Storyboard*): chỉnh từng cảnh bằng form (nền, nhân vật, hành động, hình/biểu đồ); *Tạo ảnh xem trước*; **Duyệt storyboard**.
7. **Sản xuất** (tab *Sản xuất* → "Chạy sản xuất"): giọng → hoạt ảnh → ghép phim → kiểm tra. Xem video ở tab *Kết quả*, góp ý theo cảnh, xuất **gói bàn giao**.

## Quy tắc an toàn (tool tự bảo đảm)
- **Không có khoản phí nào trước khi bạn duyệt**: giọng đọc (credit) chỉ tạo sau khi bạn duyệt lời đọc; ảnh chỉ tạo sau khi bạn duyệt kế hoạch asset.
- **Duyệt gắn với nội dung**: sửa lời một cảnh → chỉ cảnh đó cần duyệt lại lời và tạo lại giọng; đổi hình/hành động → cần duyệt lại storyboard của cảnh đó; đổi ảnh đã duyệt → ảnh phải duyệt lại.
- **Hạn mức**: số lượt gọi AI, token, số lượt tạo ảnh, credit giọng đọc (mặc định trong `config.json` mục `ai.limits`, đổi riêng từng dự án ở *Brief → Ngân sách*). Việc vượt hạn mức bị từ chối trước khi bắt đầu, kèm giải thích ở tab *Sản xuất*.
- **Chạy lại không tốn thêm**: kết quả AI/ảnh/giọng đã có được dùng lại; "Chạy tiếp bước bị lỗi" chỉ làm phần còn thiếu.
- **Sửa lời tự cập nhật mốc**: phụ đề tạo lại; các mốc hành động/hiện hình gắn với cụm từ được tự dò lại theo lời mới (thay bằng thời điểm gần đúng nếu không còn cụm tương tự) và được liệt kê để bạn kiểm tra.
- **AI chỉ đề xuất**: "Nhờ AI sửa" hiện bảng thay đổi (trước/sau); chỉ khi bạn bấm *Áp dụng* mới lưu (phiên bản mới, bản cũ vẫn giữ).

## Kết nối AI (`phase2\config.json`, mục `ai`; mẫu ở `config.example.json`)
`provider: "agy"` (Antigravity CLI, đã cài và đăng nhập); `models.cheap` cho phân loại/trích xuất/kế hoạch asset, `models.quality` cho kịch bản/storyboard/xử lý góp ý; `fallback` dùng khi model chính lỗi (một lần, trong hạn mức); `agy_concurrency` = số lượt agy chạy cùng lúc trên cả máy (mặc định 1). agy chỉ báo token, **không báo tiền**: chi phí tiền hiển thị "chưa biết" trừ khi bạn khai `price_per_1k_tokens`.

## Phạm vi hình ảnh
Nhân vật Bi (rig có sẵn) + chữ/biểu đồ/bố cục của tool; Antigravity tạo **nền và đạo cụ mới** (ảnh tĩnh). Chưa có rigging nhân vật AI, chuyển cảnh chỉ cắt thẳng/mờ dần, chỉ tay phải.
