# Storyboard · Có nên trả nợ sớm hay đầu tư thêm? (v2)

**Trạng thái:** bản nháp do AI soạn - chờ duyệt. **Chưa gọi API giọng nói.** Đối tượng: người đi làm trẻ, mới bắt đầu quản lý tiền.

**Thông điệp:** So sánh lãi suất vay với mức sinh lời có thể đạt được, giữ quỹ khẩn cấp trước, rồi mới quyết định

![Tổng quan](previews/contact_sheet.png)

## Tổng hợp
- 8 cảnh, 1109 ký tự lời đọc, **ước tính 78.8 giây** (tốc độ đọc ≈ 15.0 ký tự/giây, cộng khoảng nghỉ đầu/cuối cảnh theo cấu hình `timing`/`hold_after`).
- **Ước tính chi phí giọng đọc: ≈ 791 credit** cho lần tạo đầu (giọng Edge `edge_vi-VN-HoaiMyNeural`, kèm mốc thời gian từng từ). Cách tính: 0.714 credit/ký tự (9 real Edge-voice jobs (831 chars, 593 credits incl. word timings); 831 chars over 55 s of speech). Đây là ước tính, chỉ áp dụng cho giọng Edge, không quy ra tiền; số thật sẽ ghi vào log sau khi chạy.
- Sửa lời một cảnh chỉ tạo lại giọng của cảnh đó (tính theo ký tự cảnh đó); lời, giọng, tốc độ không đổi thì không gọi API.

| Cảnh | Tiêu đề | Ký tự | Ước tính (s) | Credit | Chuyển cảnh |
|---|---|---|---|---|---|
| s01 | Tình huống quen thuộc | 121 | 8.7 | 86 | cut |
| s02 | Câu hỏi cần trả lời đầu tiên | 92 | 6.7 | 66 | cut |
| s03 | Nợ lãi cao thì trả trước | 148 | 10.5 | 106 | cut |
| s04 | So sánh hai con số | 145 | 10.3 | 103 | cut |
| s05 | Quỹ khẩn cấp phải có trước | 144 | 10.2 | 103 | cut |
| s06 | Ví dụ cụ thể | 143 | 10.1 | 102 | cut |
| s07 | Khi nào có thể cân bằng cả hai | 150 | 10.6 | 107 | cut |
| s08 | Takeaway và lời kết | 166 | 11.7 | 118 | fade-out |

## s01 · Tình huống quen thuộc

![s01](previews/s01.png)

- **Lời đọc:** Tháng này Bi vừa có một khoản tiền dư. Và ngay lập tức câu hỏi xuất hiện: trả nợ trước, hay đem đầu tư luôn cho sinh lời?
- **Phụ đề (từng đoạn, 1 dòng):** Tháng này Bi vừa có một khoản tiền dư. / Và ngay lập tức câu hỏi xuất hiện: / trả nợ trước, hay đem đầu tư luôn cho / sinh lời?
- **Nhân vật:** Bi, biểu cảm `thinking`, tư thế mở đầu `idle`
- **Hành động:** `enter` lúc 0 s; `cheek` tại cụm “câu hỏi xuất hiện”. Đổi biểu cảm: “trả nợ trước” → worried
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** arrow_down
- **Chữ trên màn hình:** TRẢ NỢ · ĐẦU TƯ
- **Chuyển cảnh:** cut

## s02 · Câu hỏi cần trả lời đầu tiên

![s02](previews/s02.png)

- **Lời đọc:** Trước khi quyết định, hãy hỏi một câu thôi: lãi suất khoản nợ của mình là bao nhiêu mỗi năm?
- **Phụ đề (từng đoạn, 1 dòng):** Trước khi quyết định, / hãy hỏi một câu thôi: / lãi suất khoản nợ của mình là bao nhiêu / mỗi năm?
- **Nhân vật:** Bi, biểu cảm `thinking`, tư thế mở đầu `cheek`
- **Hành động:** `shrug` tại cụm “hỏi một câu thôi”; `point` tại cụm “lãi suất khoản nợ”. Đổi biểu cảm: “Trước khi quyết định” → neutral; “lãi suất khoản nợ” → thinking
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** bill, exclaim
- **Chữ trên màn hình:** Lãi suất vay = ?
- **Chuyển cảnh:** cut

## s03 · Nợ lãi cao thì trả trước

![s03](previews/s03.png)

- **Lời đọc:** Nợ thẻ tín dụng hay vay tiêu dùng thường có mức lãi cực kỳ cao. Với những khoản này, trả nợ chính là khoản đầu tư sinh lời chắc nhất bạn có thể làm.
- **Phụ đề (từng đoạn, 1 dòng):** Nợ thẻ tín dụng hay vay tiêu dùng thường / có mức lãi cực kỳ cao. / Với những khoản này, / trả nợ chính là khoản đầu tư sinh lời / chắc nhất bạn có thể làm.
- **Nhân vật:** Bi, biểu cảm `worried`, tư thế mở đầu `cheek_b`
- **Hành động:** `cheek` tại cụm “lãi cực kỳ cao”; `cheer` tại cụm “khoản đầu tư sinh lời chắc nhất”. Đổi biểu cảm: “lãi cực kỳ cao” → worried; “sinh lời chắc nhất” → happy
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** bill, card, sweat
- **Chữ trên màn hình:** Trả nợ = Đầu tư tốt nhất!
- **Chuyển cảnh:** cut

## s04 · So sánh hai con số

![s04](previews/s04.png)

- **Lời đọc:** Nguyên tắc đơn giản thế này: nếu lãi vay cao hơn mức sinh lời bạn kỳ vọng, hãy ưu tiên trả nợ. Nếu lãi vay thấp hơn, bạn mới nên tính đến đầu tư.
- **Phụ đề (từng đoạn, 1 dòng):** Nguyên tắc đơn giản thế này: / nếu lãi vay cao hơn mức sinh lời bạn kỳ / vọng, hãy ưu tiên trả nợ. / Nếu lãi vay thấp hơn, / bạn mới nên tính đến đầu tư.
- **Nhân vật:** Bi, biểu cảm `neutral`, tư thế mở đầu `point`
- **Hành động:** `point_seq` lúc 0 s. Đổi biểu cảm: “ưu tiên trả nợ” → happy; “tính đến đầu tư” → happy
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** chart
- **Chữ trên màn hình:** (chữ nằm trong biểu đồ/hóa đơn)
- **Chuyển cảnh:** cut

## s05 · Quỹ khẩn cấp phải có trước

![s05](previews/s05.png)

- **Lời đọc:** Nhưng dù lãi vay thấp đến đâu, bạn cũng cần giữ lại một khoản dự phòng. Thường là ba đến sáu tháng chi tiêu, để phòng khi thu nhập bị gián đoạn.
- **Phụ đề (từng đoạn, 1 dòng):** Nhưng dù lãi vay thấp đến đâu, / bạn cũng cần giữ lại một khoản dự phòng. / Thường là ba đến sáu tháng chi tiêu, / để phòng khi thu nhập bị gián đoạn.
- **Nhân vật:** Bi, biểu cảm `neutral`, tư thế mở đầu `idle`
- **Hành động:** `nod` tại cụm “cần giữ lại”; `point` tại cụm “ba đến sáu tháng”. Đổi biểu cảm: “phòng khi thu nhập” → worried; “ba đến sáu tháng” → happy
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** jar, notice, sparkle
- **Chữ trên màn hình:** (chữ nằm trong biểu đồ/hóa đơn)
- **Chuyển cảnh:** cut

## s06 · Ví dụ cụ thể

![s06](previews/s06.png)

- **Lời đọc:** Ví dụ: bạn đang vay với lãi suất tám phần trăm mỗi năm. Nếu kênh bạn định đầu tư chỉ kỳ vọng năm đến sáu phần trăm, trả nợ trước là hợp lý hơn.
- **Phụ đề (từng đoạn, 1 dòng):** Ví dụ: / bạn đang vay với lãi suất tám phần trăm / mỗi năm. / Nếu kênh bạn định đầu tư chỉ kỳ vọng năm / đến sáu phần trăm, / trả nợ trước là hợp lý hơn.
- **Nhân vật:** Bi, biểu cảm `thinking`, tư thế mở đầu `nod_a`
- **Hành động:** `point` tại cụm “tám phần trăm”; `nod` tại cụm “Trả nợ trước là hợp lý”. Đổi biểu cảm: “chỉ kỳ vọng năm đến sáu” → surprised; “hợp lý hơn” → happy
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** bill
- **Chữ trên màn hình:** → Trả nợ trước!
- **Chuyển cảnh:** cut

## s07 · Khi nào có thể cân bằng cả hai

![s07](previews/s07.png)

- **Lời đọc:** Nếu lãi vay của bạn thấp, chẳng hạn dưới năm phần trăm, thì vừa trả nợ đúng kỳ hạn vừa bắt đầu tích lũy đều đặn mỗi tháng cũng là một lựa chọn hợp lý.
- **Phụ đề (từng đoạn, 1 dòng):** Nếu lãi vay của bạn thấp, / chẳng hạn dưới năm phần trăm, / thì vừa trả nợ đúng kỳ hạn vừa bắt đầu / tích lũy đều đặn mỗi tháng cũng là một / lựa chọn hợp lý.
- **Nhân vật:** Bi, biểu cảm `happy`, tư thế mở đầu `idle`
- **Hành động:** `point_seq` lúc 0 s; `cheer` tại cụm “lựa chọn hợp lý”. Đổi biểu cảm: “dưới năm phần trăm” → happy
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** coin, jar
- **Chữ trên màn hình:** Trả nợ · Tích lũy
- **Chuyển cảnh:** cut

## s08 · Takeaway và lời kết

![s08](previews/s08.png)

- **Lời đọc:** Tóm lại: giữ quỹ khẩn cấp trước, rồi so sánh lãi vay với mức sinh lời bạn thực sự kỳ vọng. Không cần giỏi toán, chỉ cần biết hai con số đó là bạn đã chủ động hơn rồi.
- **Phụ đề (từng đoạn, 1 dòng):** Tóm lại: / giữ quỹ khẩn cấp trước, / rồi so sánh lãi vay với mức sinh lời bạn / thực sự kỳ vọng. / Không cần giỏi toán, / chỉ cần biết hai con số đó là bạn đã chủ / động hơn rồi.
- **Nhân vật:** Bi, biểu cảm `happy`, tư thế mở đầu `cheer`
- **Hành động:** `cheer` tại cụm “Tóm lại”; `nod` tại cụm “chủ động hơn rồi”. Đổi biểu cảm: “biết hai con số đó” → happy
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** pills
- **Chữ trên màn hình:** (chữ nằm trong biểu đồ/hóa đơn)
- **Chuyển cảnh:** fade-out

## Điểm cần bạn duyệt
1. Mạch kể và thứ tự các cảnh.
2. Lời đọc từng cảnh (đây là văn bản sẽ gửi API giọng đọc).
3. Thông tin cần kiểm chứng (nếu có).
4. Hình ảnh, hành động từng cảnh.

Sau khi bạn duyệt: tôi mới gọi API giọng nói (một lần cho từng cảnh), rồi dựng bản xem thử.
