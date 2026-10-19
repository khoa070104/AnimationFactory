# Storyboard · Thử nhân vật Mai (v1)

**Trạng thái:** chưa có kịch bản - chờ AI chuẩn bị. **Chưa gọi API giọng nói.** Đối tượng: người đi làm trẻ, mới bắt đầu quản lý tiền.

**Thông điệp:** 

![Tổng quan](previews/contact_sheet.png)

## Tổng hợp
- 1 cảnh, 104 ký tự lời đọc, **ước tính 7.4 giây** (tốc độ đọc ≈ 15.3 ký tự/giây, cộng khoảng nghỉ đầu/cuối cảnh theo cấu hình `timing`/`hold_after`).
- **Ước tính chi phí giọng đọc: ≈ 74 credit** cho lần tạo đầu (giọng Edge `edge_vi-VN-HoaiMyNeural`, kèm mốc thời gian từng từ). Cách tính: 0.716 credit/ký tự (25 real Edge-voice jobs (2778 chars, 1989 credits incl. word timings); 3059 chars over 200 s of speech). Đây là ước tính, chỉ áp dụng cho giọng Edge, không quy ra tiền; số thật sẽ ghi vào log sau khi chạy.
- Sửa lời một cảnh chỉ tạo lại giọng của cảnh đó (tính theo ký tự cảnh đó); lời, giọng, tốc độ không đổi thì không gọi API.

| Cảnh | Tiêu đề | Ký tự | Ước tính (s) | Credit | Chuyển cảnh |
|---|---|---|---|---|---|
| s01 | Mai và chiếc ví | 104 | 7.4 | 74 | fade-out |

## s01 · Mai và chiếc ví

![s01](previews/s01.png)

- **Lời đọc:** Mai mở ví ra và thấy tiền vơi nhanh quá. Cô ấy chỉ vào hóa đơn rồi mỉm cười, vì đã tìm ra cách giữ tiền.
- **Phụ đề (từng đoạn, 1 dòng):** Mai mở ví ra và thấy tiền vơi nhanh quá. / Cô ấy chỉ vào hóa đơn rồi mỉm cười, / vì đã tìm ra cách giữ tiền.
- **Nhân vật:** Bi, biểu cảm `worried`, tư thế mở đầu `idle`
- **Hành động:** `enter` lúc 0.0 s; `point` tại cụm “chỉ vào hóa đơn”; `cheer` tại cụm “giữ tiền”. Đổi biểu cảm: “mỉm cười” → happy
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** wallet
- **Chữ trên màn hình:** Tiền đi đâu?
- **Chuyển cảnh:** fade-out

## Điểm cần bạn duyệt
1. Nội dung và thứ tự các cảnh.
2. Lời đọc từng cảnh (đây là văn bản sẽ gửi API).
3. Số liệu minh họa.
4. Giọng đọc.

Sau khi bạn duyệt: tôi mới gọi API giọng nói (một lần cho từng cảnh), rồi dựng bản xem thử.
