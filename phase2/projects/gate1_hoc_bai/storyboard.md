# Storyboard · Ba thói quen giúp tập trung học bài (v5)

**Trạng thái:** bản nháp do AI soạn - chờ duyệt. **Chưa gọi API giọng nói.** Đối tượng: người đi làm trẻ, mới bắt đầu quản lý tiền.

**Thông điệp:** Tập trung là kỹ năng luyện được, bắt đầu từ những thói quen nhỏ

![Tổng quan](previews/contact_sheet.png)

## Tổng hợp
- 3 cảnh, 515 ký tự lời đọc, **ước tính 36.2 giây** (tốc độ đọc ≈ 15.3 ký tự/giây, cộng khoảng nghỉ đầu/cuối cảnh theo cấu hình `timing`/`hold_after`).
- **Ước tính chi phí giọng đọc: ≈ 368 credit** cho lần tạo đầu (giọng Edge `edge_vi-VN-HoaiMyNeural`, kèm mốc thời gian từng từ). Cách tính: 0.716 credit/ký tự (25 real Edge-voice jobs (2778 chars, 1989 credits incl. word timings); 3059 chars over 200 s of speech). Đây là ước tính, chỉ áp dụng cho giọng Edge, không quy ra tiền; số thật sẽ ghi vào log sau khi chạy.
- Sửa lời một cảnh chỉ tạo lại giọng của cảnh đó (tính theo ký tự cảnh đó); lời, giọng, tốc độ không đổi thì không gọi API.

| Cảnh | Tiêu đề | Ký tự | Ước tính (s) | Credit | Chuyển cảnh |
|---|---|---|---|---|---|
| s01 | Mở đầu – Minh và chị gái | 141 | 9.8 | 101 | cut |
| s02 | Ba thói quen nhỏ | 224 | 15.3 | 160 | cut |
| s03 | Kết – Bắt đầu từ hôm nay | 150 | 11.1 | 107 | fade-out |

## s01 · Mở đầu – Minh và chị gái

![s01](previews/s01.png)

- **Lời đọc:** Minh hay ngồi học mà cứ nhìn điện thoại, học một lúc lại mất tập trung. Chị gái nhìn thấy, cười rồi nói: thôi để chị chỉ cho mấy cái mẹo nhỏ.
- **Phụ đề (từng đoạn, 1 dòng):** Minh hay ngồi học mà cứ nhìn điện thoại, / học một lúc lại mất tập trung. / Chị gái nhìn thấy, / cười rồi nói: / thôi để chị chỉ cho mấy cái mẹo nhỏ.
- **Nhân vật:** Bi, biểu cảm `neutral`, tư thế mở đầu `phone`
- **Hành động:** `enter` lúc 0 s; `hold_phone` tại cụm “nhìn điện thoại”; `shrug` tại cụm “mất tập trung”. Đổi biểu cảm: “nhìn điện thoại” → happy; “mất tập trung” → worried; “thôi để chị” → surprised
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** exclaim, phone
- **Chữ trên màn hình:** (chữ nằm trong biểu đồ/hóa đơn)
- **Chuyển cảnh:** cut

## s02 · Ba thói quen nhỏ

![s02](previews/s02.png)

- **Lời đọc:** Một, cất điện thoại ra chỗ khác, đừng để gần tay. Hai, học theo từng đợt ngắn, khoảng hai mươi đến ba mươi phút thôi. Ba, nghỉ giải lao đúng lúc để não nạp lại năng lượng. Chị bảo: tập trung là kỹ năng, cứ luyện dần là được.
- **Phụ đề (từng đoạn, 1 dòng):** Một, cất điện thoại ra chỗ khác, / đừng để gần tay. / Hai, học theo từng đợt ngắn, / khoảng hai mươi đến ba mươi phút thôi. / Ba, nghỉ giải lao đúng lúc để não nạp / lại năng lượng. / Chị bảo: / tập trung là kỹ năng, / cứ luyện dần là được.
- **Nhân vật:** Bi, biểu cảm `happy`, tư thế mở đầu `point`
- **Hành động:** `enter` lúc 0 s; `point_seq` lúc 0 s; `nod` tại cụm “cứ luyện dần”. Đổi biểu cảm: “cất điện thoại” → neutral; “tập trung là kỹ năng” → happy
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** pills
- **Chữ trên màn hình:** (chữ nằm trong biểu đồ/hóa đơn)
- **Chuyển cảnh:** cut

## s03 · Kết – Bắt đầu từ hôm nay

![s03](previews/s03.png)

- **Lời đọc:** Minh thử ngay hôm đó và học tập trung hơn và hoàn thành phần bài đã đặt ra. Bạn cũng vậy, bắt đầu từ thói quen nhỏ thôi, không cần phải hoàn hảo ngay.
- **Phụ đề (từng đoạn, 1 dòng):** Minh thử ngay hôm đó và học tập trung / hơn và hoàn thành phần bài đã đặt ra. / Bạn cũng vậy, bắt đầu từ thói quen nhỏ / thôi, không cần phải hoàn hảo ngay.
- **Nhân vật:** Bi, biểu cảm `happy`, tư thế mở đầu `cheer`
- **Hành động:** `enter` lúc 0 s; `cheer` tại cụm “học tập trung hơn và”; `nod` tại cụm “bắt đầu từ thói quen”. Đổi biểu cảm: “học tập trung hơn và” → happy; “không cần phải hoàn hảo” → happy
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** legend, sparkle
- **Chữ trên màn hình:** 3 thói quen nhỏ:
- **Chuyển cảnh:** fade-out

## Điểm cần bạn duyệt
1. Mạch kể và thứ tự các cảnh.
2. Lời đọc từng cảnh (đây là văn bản sẽ gửi API giọng đọc).
3. Thông tin cần kiểm chứng (nếu có).
4. Hình ảnh, hành động từng cảnh.

Sau khi bạn duyệt: tôi mới gọi API giọng nói (một lần cho từng cảnh), rồi dựng bản xem thử.
