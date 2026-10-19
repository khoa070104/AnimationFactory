# Storyboard · Nhận lương xong tiền đi đâu? (v2)

**Trạng thái:** v2 - nội dung đã được duyệt có chỉnh s05-s08 (xem approval.json). **Giọng đã tạo:** 9 lượt gọi, 593 credit thực tế. Đối tượng: người đi làm trẻ.

**Thông điệp:** Ghi lại từng khoản và chia lương theo khung tham khảo 50-30-20 trên thu nhập thực nhận (điều chỉnh theo hoàn cảnh), để tiền có chỗ đi rõ ràng.

![Tổng quan](previews/contact_sheet.png)

## Tổng hợp
- 9 cảnh, 831 ký tự lời đọc, **ước tính 63.9 giây** (tốc độ đọc ≈ 15.0 ký tự/giây, cộng khoảng nghỉ đầu/cuối cảnh theo cấu hình `timing`/`hold_after`).
- **Ước tính chi phí giọng đọc: ≈ 594 credit** cho lần tạo đầu (giọng Edge `edge_vi-VN-HoaiMyNeural`, kèm mốc thời gian từng từ). Cách tính: 0.714 credit/ký tự (9 real Edge-voice jobs (831 chars, 593 credits incl. word timings); 831 chars over 55 s of speech). Đây là ước tính, chỉ áp dụng cho giọng Edge, không quy ra tiền; số thật sẽ ghi vào log sau khi chạy.
- Sửa lời một cảnh chỉ tạo lại giọng của cảnh đó (tính theo ký tự cảnh đó); lời, giọng, tốc độ không đổi thì không gọi API.

| Cảnh | Tiêu đề | Ký tự | Ước tính (s) | Credit | Chuyển cảnh |
|---|---|---|---|---|---|
| s01 | Lương về | 68 | 5.1 | 49 | cut |
| s02 | Chỉ còn sáu triệu | 71 | 5.3 | 51 | slide-left |
| s03 | Xem lại chi tiêu | 86 | 6.9 | 61 | slide-left |
| s04 | Khoản lặt vặt | 92 | 6.7 | 66 | slide-left |
| s05 | Xe hỏng | 94 | 7.3 | 67 | cut |
| s06 | Thử chia lương | 137 | 10.3 | 98 | slide-left |
| s07 | Áp dụng với 15 triệu | 90 | 7.2 | 64 | slide-left |
| s08 | Kỳ lương sau | 98 | 7.1 | 70 | slide-left |
| s09 | Kết | 95 | 8.0 | 68 | fade-out |

## s01 · Lương về

![s01](previews/s01.png)

- **Lời đọc:** Ting! Lương về rồi! Mười lăm triệu đồng. Hôm nay mình giàu nhất xóm!
- **Phụ đề (từng đoạn, 1 dòng):** Ting! Lương về rồi! / Mười lăm triệu đồng. / Hôm nay mình giàu nhất xóm!
- **Nhân vật:** Bi, biểu cảm `happy`, tư thế mở đầu `cheer`
- **Hành động:** `enter` lúc 0.0 s; `cheer` tại cụm “Hôm nay”
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** coin, notice, phone, sparkle
- **Chữ trên màn hình:** Ting!
- **Chuyển cảnh:** cut

## s02 · Chỉ còn sáu triệu

![s02](previews/s02.png)

- **Lời đọc:** Nhưng mới giữa tháng, tài khoản chỉ còn sáu triệu. Tiền đi đâu hết rồi?
- **Phụ đề (từng đoạn, 1 dòng):** Nhưng mới giữa tháng, / tài khoản chỉ còn sáu triệu. / Tiền đi đâu hết rồi?
- **Nhân vật:** Bi, biểu cảm `surprised`, tư thế mở đầu `point`
- **Hành động:** `point` tại cụm “chỉ còn”
- **Bối cảnh:** nền `blue`
- **Đạo cụ / hình:** phone
- **Chữ trên màn hình:** Số dư · 6.000.000đ · ? · ?
- **Chuyển cảnh:** slide-left

## s03 · Xem lại chi tiêu

![s03](previews/s03.png)

- **Lời đọc:** Mình ngồi xem lại. Tiền nhà bốn triệu, ăn uống hai triệu rưỡi, mua sắm một triệu rưỡi.
- **Phụ đề (từng đoạn, 1 dòng):** Mình ngồi xem lại. / Tiền nhà bốn triệu, / ăn uống hai triệu rưỡi, / mua sắm một triệu rưỡi.
- **Nhân vật:** Bi, biểu cảm `neutral`, tư thế mở đầu `point`
- **Hành động:** `point_seq` lúc 0 s
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** chart
- **Chữ trên màn hình:** (chữ nằm trong biểu đồ/hóa đơn)
- **Chuyển cảnh:** slide-left

## s04 · Khoản lặt vặt

![s04](previews/s04.png)

- **Lời đọc:** Điều bất ngờ là những khoản lặt vặt: cà phê, đồ ăn vặt, phí đăng ký. Cộng lại hết một triệu.
- **Phụ đề (từng đoạn, 1 dòng):** Điều bất ngờ là những khoản lặt vặt: / cà phê, đồ ăn vặt, phí đăng ký. / Cộng lại hết một triệu.
- **Nhân vật:** Bi, biểu cảm `thinking`, tư thế mở đầu `shrug`
- **Hành động:** `shrug` tại cụm “bất ngờ”
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** pills
- **Chữ trên màn hình:** Cộng lại: 1.000.000đ
- **Chuyển cảnh:** slide-left

## s05 · Xe hỏng

![s05](previews/s05.png)

- **Lời đọc:** Rồi xe hỏng, sửa hết ba triệu rưỡi. Chỉ còn hai triệu rưỡi cho nửa tháng. Thế là phải xoay xở!
- **Phụ đề (từng đoạn, 1 dòng):** Rồi xe hỏng, sửa hết ba triệu rưỡi. / Chỉ còn hai triệu rưỡi cho nửa tháng. / Thế là phải xoay xở!
- **Nhân vật:** Bi, biểu cảm `worried`, tư thế mở đầu `cheek`
- **Hành động:** `cheek` tại cụm “Rồi xe hỏng”
- **Bối cảnh:** nền `blue`
- **Đạo cụ / hình:** bill, exclaim, sweat
- **Chữ trên màn hình:** Còn lại: 2.500.000đ
- **Chuyển cảnh:** cut

## s06 · Thử chia lương

![s06](previews/s06.png)

- **Lời đọc:** Mình thử chia lương: năm mươi phần trăm cho thiết yếu, ba mươi cho mong muốn, hai mươi để tiết kiệm hoặc trả nợ. Tỷ lệ có thể điều chỉnh.
- **Phụ đề (từng đoạn, 1 dòng):** Mình thử chia lương: / năm mươi phần trăm cho thiết yếu, / ba mươi cho mong muốn, / hai mươi để tiết kiệm hoặc trả nợ. / Tỷ lệ có thể điều chỉnh.
- **Nhân vật:** Bi, biểu cảm `happy`, tư thế mở đầu `point`
- **Hành động:** `point` tại cụm “chia lương”. Đổi biểu cảm: “Mình thử” → happy
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** legend, pie
- **Chữ trên màn hình:** Khung tham khảo, trên lương thực nhận
- **Chuyển cảnh:** slide-left

## s07 · Áp dụng với 15 triệu

![s07](previews/s07.png)

- **Lời đọc:** Với lương thực nhận mười lăm triệu, ba phần là bảy triệu rưỡi, bốn triệu rưỡi và ba triệu.
- **Phụ đề (từng đoạn, 1 dòng):** Với lương thực nhận mười lăm triệu, / ba phần là bảy triệu rưỡi, / bốn triệu rưỡi và ba triệu.
- **Nhân vật:** Bi, biểu cảm `happy`, tư thế mở đầu `phone`, cầm calculator
- **Hành động:** (giữ tư thế)
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** board, legend
- **Chữ trên màn hình:** Thực nhận 15.000.000đ
- **Chuyển cảnh:** slide-left

## s08 · Kỳ lương sau

![s08](previews/s08.png)

- **Lời đọc:** Kỳ lương sau, mình đặt mục tiêu để riêng ba triệu ngay khi nhận lương, rồi chi trong phần còn lại.
- **Phụ đề (từng đoạn, 1 dòng):** Kỳ lương sau, mình đặt mục tiêu / để riêng ba triệu ngay khi nhận lương, / rồi chi trong phần còn lại.
- **Nhân vật:** Bi, biểu cảm `happy`, tư thế mở đầu `point`
- **Hành động:** `point` tại cụm “để riêng”
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** arrow_down, coin, jar
- **Chữ trên màn hình:** Kỳ lương sau: để riêng trước · 3.000.000đ
- **Chuyển cảnh:** slide-left

## s09 · Kết

![s09](previews/s09.png)

- **Lời đọc:** Từ hôm nay, hãy ghi lại từng khoản và chia lương ngay khi nhận. Tiền của bạn sẽ biết rõ chỗ đi!
- **Phụ đề (từng đoạn, 1 dòng):** Từ hôm nay, hãy ghi lại từng khoản / và chia lương ngay khi nhận. / Tiền của bạn sẽ biết rõ chỗ đi!
- **Nhân vật:** Bi, biểu cảm `happy`, tư thế mở đầu `cheer`
- **Hành động:** `nod` tại cụm “Từ hôm nay”; `cheer` tại cụm “Tiền của bạn”
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** sparkle
- **Chữ trên màn hình:** 1 · Ghi lại từng khoản · 2 · Chia lương ngay khi nhận · 3 · Tiết kiệm trước
- **Chuyển cảnh:** fade-out

## Điểm cần bạn duyệt
1. Nội dung và thứ tự các cảnh.
2. Lời đọc từng cảnh (đây là văn bản sẽ gửi API).
3. Số liệu minh họa nếu có.
4. Giọng đọc.

Sau khi bạn duyệt: tôi mới gọi API giọng nói (một lần cho từng cảnh), rồi dựng bản xem thử.
