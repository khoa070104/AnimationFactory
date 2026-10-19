# Storyboard · Quỹ khẩn cấp là gì, nên có bao nhiêu? (v3)

**Trạng thái:** v3 - cảnh 6 dùng heo đất do Antigravity tạo (piggy_ai, đã duyệt). **Giọng đã tạo:** 9 lượt gọi, 653 credit thực tế. Đối tượng: người đi làm trẻ.

**Thông điệp:** Quỹ khẩn cấp là khoản tiền để riêng cho việc không báo trước; khung tham khảo là ba đến sáu tháng chi tiêu thiết yếu, điều chỉnh theo hoàn cảnh.

![Tổng quan](previews/contact_sheet.png)

## Tổng hợp
- 9 cảnh, 913 ký tự lời đọc, **ước tính 68.4 giây** (tốc độ đọc ≈ 15.0 ký tự/giây, cộng khoảng nghỉ đầu/cuối cảnh theo cấu hình `timing`/`hold_after`).
- **Ước tính chi phí giọng đọc: ≈ 652 credit** cho lần tạo đầu (giọng Edge `edge_vi-VN-HoaiMyNeural`, kèm mốc thời gian từng từ). Cách tính: 0.714 credit/ký tự (9 real Edge-voice jobs (831 chars, 593 credits incl. word timings); 831 chars over 55 s of speech). Đây là ước tính, chỉ áp dụng cho giọng Edge, không quy ra tiền; số thật sẽ ghi vào log sau khi chạy.
- Sửa lời một cảnh chỉ tạo lại giọng của cảnh đó (tính theo ký tự cảnh đó); lời, giọng, tốc độ không đổi thì không gọi API.

| Cảnh | Tiêu đề | Ký tự | Ước tính (s) | Credit | Chuyển cảnh |
|---|---|---|---|---|---|
| s01 | Máy giặt hỏng | 92 | 6.7 | 66 | cut |
| s02 | Cách xoay xở thường gặp | 104 | 7.5 | 74 | slide-left |
| s03 | Quỹ khẩn cấp là gì | 105 | 7.6 | 75 | slide-left |
| s04 | Nên có bao nhiêu | 105 | 8.2 | 75 | slide-left |
| s04b | Chi tiêu thiết yếu gồm gì | 98 | 7.1 | 70 | slide-left |
| s05 | Tính ví dụ | 113 | 8.7 | 81 | slide-left |
| s06 | Bắt đầu nhỏ | 97 | 7.1 | 69 | slide-left |
| s07 | Cách làm | 110 | 7.9 | 78 | slide-left |
| s08 | Kết | 89 | 7.6 | 64 | fade-out |

## s01 · Máy giặt hỏng

![s01](previews/s01.png)

- **Lời đọc:** Sáng nay máy giặt hỏng, thợ báo sửa hết hai triệu. Mà cuối tháng rồi, ví mình gần như trống!
- **Phụ đề (từng đoạn, 1 dòng):** Sáng nay máy giặt hỏng, / thợ báo sửa hết hai triệu. / Mà cuối tháng rồi, / ví mình gần như trống!
- **Nhân vật:** Bi, biểu cảm `surprised`, tư thế mở đầu `shrug`
- **Hành động:** `shrug` tại cụm “hỏng”
- **Bối cảnh:** nền `blue`
- **Đạo cụ / hình:** bill, exclaim, wallet
- **Chữ trên màn hình:** Ví gần như trống
- **Chuyển cảnh:** cut

## s02 · Cách xoay xở thường gặp

![s02](previews/s02.png)

- **Lời đọc:** Nhiều người sẽ quẹt thẻ tín dụng hoặc vay bạn bè. Việc trước mắt xong, nhưng một khoản nợ mới xuất hiện.
- **Phụ đề (từng đoạn, 1 dòng):** Nhiều người sẽ quẹt thẻ tín dụng / hoặc vay bạn bè. / Việc trước mắt xong, / nhưng một khoản nợ mới xuất hiện.
- **Nhân vật:** Bi, biểu cảm `worried`, tư thế mở đầu `cheek`
- **Hành động:** `shrug` tại cụm “Nhiều người”
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** pills
- **Chữ trên màn hình:** Nợ mới
- **Chuyển cảnh:** slide-left

## s03 · Quỹ khẩn cấp là gì

![s03](previews/s03.png)

- **Lời đọc:** Quỹ khẩn cấp là khoản tiền để riêng cho việc không báo trước, như mất việc, ốm đau hay sửa chữa đột xuất.
- **Phụ đề (từng đoạn, 1 dòng):** Quỹ khẩn cấp là khoản tiền để riêng / cho việc không báo trước, / như mất việc, ốm đau / hay sửa chữa đột xuất.
- **Nhân vật:** Bi, biểu cảm `happy`, tư thế mở đầu `idle`
- **Hành động:** `nod` tại cụm “Quỹ khẩn cấp”
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** jar, pills
- **Chữ trên màn hình:** Quỹ khẩn cấp
- **Chuyển cảnh:** slide-left

## s04 · Nên có bao nhiêu

![s04](previews/s04.png)

- **Lời đọc:** Khung tham khảo là chi tiêu thiết yếu của ba đến sáu tháng. Thu nhập không ổn định thì nên giữ nhiều hơn.
- **Phụ đề (từng đoạn, 1 dòng):** Khung tham khảo là chi tiêu thiết yếu / của ba đến sáu tháng. / Thu nhập không ổn định / thì nên giữ nhiều hơn.
- **Nhân vật:** Bi, biểu cảm `neutral`, tư thế mở đầu `point`
- **Hành động:** `point_seq` lúc 0 s
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** chart
- **Chữ trên màn hình:** (chữ nằm trong biểu đồ/hóa đơn)
- **Chuyển cảnh:** slide-left

## s04b · Chi tiêu thiết yếu gồm gì

![s04b](previews/s04b.png)

- **Lời đọc:** Chi tiêu thiết yếu là những khoản không thể bỏ: tiền nhà, ăn uống, điện nước, đi lại và thuốc men.
- **Phụ đề (từng đoạn, 1 dòng):** Chi tiêu thiết yếu là những khoản / không thể bỏ: tiền nhà, ăn uống, / điện nước, đi lại và thuốc men.
- **Nhân vật:** Bi, biểu cảm `neutral`, tư thế mở đầu `point`
- **Hành động:** `point_seq` lúc 0 s
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** pills
- **Chữ trên màn hình:** Chi tiêu thiết yếu
- **Chuyển cảnh:** slide-left

## s05 · Tính ví dụ

![s05](previews/s05.png)

- **Lời đọc:** Ví dụ chi tiêu thiết yếu mỗi tháng là tám triệu. Ba tháng là hai mươi bốn triệu, sáu tháng là bốn mươi tám triệu.
- **Phụ đề (từng đoạn, 1 dòng):** Ví dụ chi tiêu thiết yếu / mỗi tháng là tám triệu. / Ba tháng là hai mươi bốn triệu, / sáu tháng là bốn mươi tám triệu.
- **Nhân vật:** Bi, biểu cảm `happy`, tư thế mở đầu `phone`, cầm calculator
- **Hành động:** (giữ tư thế)
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** board, legend
- **Chữ trên màn hình:** Ví dụ
- **Chuyển cảnh:** slide-left

## s06 · Bắt đầu nhỏ

![s06](previews/s06.png)

- **Lời đọc:** Chưa đủ ngay cũng không sao. Hãy bắt đầu bằng mục tiêu nhỏ, như một tháng chi tiêu, rồi tăng dần.
- **Phụ đề (từng đoạn, 1 dòng):** Chưa đủ ngay cũng không sao. / Hãy bắt đầu bằng mục tiêu nhỏ, / như một tháng chi tiêu, / rồi tăng dần.
- **Nhân vật:** Bi, biểu cảm `happy`, tư thế mở đầu `point`
- **Hành động:** `point` tại cụm “mục tiêu nhỏ”
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** ai:piggy_ai
- **Chữ trên màn hình:** Mục tiêu đầu tiên: 1 tháng · 8.000.000đ
- **Chuyển cảnh:** slide-left

## s07 · Cách làm

![s07](previews/s07.png)

- **Lời đọc:** Mỗi kỳ lương, chuyển một khoản cố định sang tài khoản riêng. Cố gắng không đụng tới, trừ khi thật sự khẩn cấp.
- **Phụ đề (từng đoạn, 1 dòng):** Mỗi kỳ lương, chuyển một khoản cố định / sang tài khoản riêng. / Cố gắng không đụng tới, / trừ khi thật sự khẩn cấp.
- **Nhân vật:** Bi, biểu cảm `happy`, tư thế mở đầu `idle`
- **Hành động:** `nod` tại cụm “Mỗi kỳ lương”
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** pills, wallet
- **Chữ trên màn hình:** (chữ nằm trong biểu đồ/hóa đơn)
- **Chuyển cảnh:** slide-left

## s08 · Kết

![s08](previews/s08.png)

- **Lời đọc:** Quỹ khẩn cấp không làm bạn giàu lên, nhưng giúp một bất ngờ không biến thành khủng hoảng.
- **Phụ đề (từng đoạn, 1 dòng):** Quỹ khẩn cấp không làm bạn giàu lên, / nhưng giúp một bất ngờ / không biến thành khủng hoảng.
- **Nhân vật:** Bi, biểu cảm `happy`, tư thế mở đầu `cheer`
- **Hành động:** `cheer` tại cụm “không biến thành”
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** jar, sparkle
- **Chữ trên màn hình:** Bất ngờ không thành khủng hoảng
- **Chuyển cảnh:** fade-out

## Điểm cần bạn duyệt
1. Mạch kể: bất ngờ (hỏng máy giặt) → cách xoay xở thường gặp → quỹ khẩn cấp là gì → nên có bao nhiêu → ví dụ → bắt đầu nhỏ → cách làm → kết.
2. Khung tham khảo 'ba đến sáu tháng chi tiêu thiết yếu' (nhiều hơn nếu thu nhập không ổn định): đúng ý, hay muốn diễn đạt khác?
3. Số liệu minh họa: sửa máy giặt 2 triệu; chi tiêu thiết yếu 8 triệu/tháng → 24 triệu (3 tháng), 48 triệu (6 tháng).
4. Lời đọc từng cảnh (đây là văn bản sẽ gửi API) và giọng đọc HoaiMy.

Sau khi bạn duyệt: tôi mới gọi API giọng nói (một lần cho từng cảnh), rồi dựng bản xem thử.
