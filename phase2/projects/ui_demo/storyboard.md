# Storyboard · Quỹ khẩn cấp - bản thử qua giao diện (v4)

**Trạng thái:** . **Giọng đã tạo:** 0 lượt gọi, 0 credit thực tế. Đối tượng: người đi làm trẻ.

**Thông điệp:** Thử quy trình qua giao diện: nhập, duyệt, dựng.

![Tổng quan](previews/contact_sheet.png)

## Tổng hợp
- 3 cảnh, 281 ký tự lời đọc, **ước tính 21.4 giây** (tốc độ đọc ≈ 15.0 ký tự/giây, cộng khoảng nghỉ đầu/cuối cảnh theo cấu hình `timing`/`hold_after`).
- **Ước tính chi phí giọng đọc: ≈ 201 credit** cho lần tạo đầu (giọng Edge `edge_vi-VN-HoaiMyNeural`, kèm mốc thời gian từng từ). Cách tính: 0.714 credit/ký tự (9 real Edge-voice jobs (831 chars, 593 credits incl. word timings); 831 chars over 55 s of speech). Đây là ước tính, chỉ áp dụng cho giọng Edge, không quy ra tiền; số thật sẽ ghi vào log sau khi chạy.
- Sửa lời một cảnh chỉ tạo lại giọng của cảnh đó (tính theo ký tự cảnh đó); lời, giọng, tốc độ không đổi thì không gọi API.

| Cảnh | Tiêu đề | Ký tự | Ước tính (s) | Credit | Chuyển cảnh |
|---|---|---|---|---|---|
| a1 | Mở đầu | 89 | 6.5 | 64 | cut |
| a2 | Bắt đầu nhỏ | 97 | 7.1 | 69 | cut |
| a3 | Kết | 95 | 7.8 | 68 | cut |

## a1 · Mở đầu

![a1](previews/a1.png)

- **Lời đọc:** Quỹ khẩn cấp không làm bạn giàu lên, nhưng giúp một bất ngờ không biến thành khủng hoảng.
- **Phụ đề (từng đoạn, 1 dòng):** Quỹ khẩn cấp không làm bạn giàu lên, / nhưng giúp một bất ngờ không biến thành / khủng hoảng.
- **Nhân vật:** Bi, biểu cảm `happy`, tư thế mở đầu `cheer`
- **Hành động:** `cheer` tại cụm “không làm”
- **Bối cảnh:** nền `blue`
- **Đạo cụ / hình:** jar
- **Chữ trên màn hình:** Quỹ khẩn cấp
- **Chuyển cảnh:** cut

## a2 · Bắt đầu nhỏ

![a2](previews/a2.png)

- **Lời đọc:** Chưa đủ ngay cũng không sao. Hãy bắt đầu bằng mục tiêu nhỏ, như một tháng chi tiêu, rồi tăng dần.
- **Phụ đề (từng đoạn, 1 dòng):** Chưa đủ ngay cũng không sao. / Hãy bắt đầu bằng mục tiêu nhỏ, / như một tháng chi tiêu, / rồi tăng dần.
- **Nhân vật:** Bi, biểu cảm `neutral`, tư thế mở đầu `point`
- **Hành động:** `point_seq` lúc 0 s
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** chart
- **Chữ trên màn hình:** (chữ nằm trong biểu đồ/hóa đơn)
- **Chuyển cảnh:** cut

## a3 · Kết

![a3](previews/a3.png)

- **Lời đọc:** Từ hôm nay, hãy ghi lại từng khoản và chia lương ngay khi nhận. Tiền của bạn sẽ biết rõ chỗ đi!
- **Phụ đề (từng đoạn, 1 dòng):** Từ hôm nay, hãy ghi lại từng khoản và / chia lương ngay khi nhận. / Tiền của bạn sẽ biết rõ chỗ đi!
- **Nhân vật:** Bi, biểu cảm `happy`, tư thế mở đầu `cheer`
- **Hành động:** `nod` tại cụm “Từ hôm nay”; `cheer` tại cụm “Tiền của bạn”
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** -
- **Chữ trên màn hình:** 1 · Ghi lại từng khoản · 2 · Chia lương khi nhận · 3 · Tiết kiệm trước
- **Chuyển cảnh:** cut

## Điểm cần bạn duyệt
1. Nội dung và thứ tự các cảnh.
2. Lời đọc từng cảnh (đây là văn bản sẽ gửi API).
3. Số liệu minh họa nếu có.
4. Giọng đọc.

Sau khi bạn duyệt: tôi mới gọi API giọng nói (một lần cho từng cảnh), rồi dựng bản xem thử.
