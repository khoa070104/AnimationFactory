# Storyboard · Lập ngân sách chi tiêu hàng tháng cho người mới đi làm (v5)

**Trạng thái:** bản nháp do AI soạn - chờ duyệt. **Giọng đã tạo:** 7 lượt gọi, 743 credit thực tế. Đối tượng: người đi làm trẻ, mới bắt đầu quản lý tiền.

**Thông điệp:** Ghi lại mọi khoản chi, chia thu nhập thành nhóm, và xem lại mỗi tháng để điều chỉnh

![Tổng quan](previews/contact_sheet.png)

## Tổng hợp
- 7 cảnh, 1034 ký tự lời đọc, **ước tính 72.7 giây** (tốc độ đọc ≈ 15.3 ký tự/giây, cộng khoảng nghỉ đầu/cuối cảnh theo cấu hình `timing`/`hold_after`).
- **Ước tính chi phí giọng đọc: ≈ 740 credit** cho lần tạo đầu (giọng Edge `edge_vi-VN-HoaiMyNeural`, kèm mốc thời gian từng từ). Cách tính: 0.716 credit/ký tự (25 real Edge-voice jobs (2778 chars, 1989 credits incl. word timings); 3059 chars over 200 s of speech). Đây là ước tính, chỉ áp dụng cho giọng Edge, không quy ra tiền; số thật sẽ ghi vào log sau khi chạy.
- Sửa lời một cảnh chỉ tạo lại giọng của cảnh đó (tính theo ký tự cảnh đó); lời, giọng, tốc độ không đổi thì không gọi API.

| Cảnh | Tiêu đề | Ký tự | Ước tính (s) | Credit | Chuyển cảnh |
|---|---|---|---|---|---|
| s01 | Mở đầu: Tiền biến đâu mất? | 148 | 10.3 | 106 | cut |
| s02 | Vấn đề cốt lõi | 113 | 8.0 | 81 | cut |
| s03 | Bước một: Ghi lại | 139 | 9.7 | 100 | cut |
| s04 | Bước hai: Chia nhóm thu nhập | 137 | 9.6 | 98 | cut |
| s05 | Ví dụ minh họa | 178 | 12.2 | 127 | cut |
| s06 | Xem lại cuối tháng | 155 | 10.7 | 111 | cut |
| s07 | Kết: Chủ động với tiền | 164 | 12.2 | 117 | fade-out |

## s01 · Mở đầu: Tiền biến đâu mất?

![s01](previews/s01.png)

- **Lời đọc:** Lương vừa về, chưa cuối tháng đã hết. Bạn không tiêu hoang, nhưng tiền cứ biến mất không rõ lý do. Chuyện này xảy ra với rất nhiều người mới đi làm.
- **Phụ đề (từng đoạn, 1 dòng):** Lương vừa về, chưa cuối tháng đã hết. / Bạn không tiêu hoang, / nhưng tiền cứ biến mất không rõ lý do. / Chuyện này xảy ra với rất nhiều người / mới đi làm.
- **Nhân vật:** Bi, biểu cảm `worried`, tư thế mở đầu `idle`
- **Hành động:** `enter` lúc 0 s; `cheek` tại cụm “chưa cuối tháng đã hết”. Đổi biểu cảm: “tiền cứ biến mất” → surprised
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** wallet
- **Chữ trên màn hình:** ??? · Tiền đi đâu?
- **Chuyển cảnh:** cut

## s02 · Vấn đề cốt lõi

![s02](previews/s02.png)

- **Lời đọc:** Vấn đề không phải lương thấp. Vấn đề là mình không biết tiền mình đi đâu. Không theo dõi thì không thể kiểm soát.
- **Phụ đề (từng đoạn, 1 dòng):** Vấn đề không phải lương thấp. / Vấn đề là mình không biết tiền mình đi / đâu. / Không theo dõi thì không thể kiểm soát.
- **Nhân vật:** Bi, biểu cảm `thinking`, tư thế mở đầu `cheek`
- **Hành động:** `shrug` tại cụm “không biết tiền mình đi đâu”; `nod` tại cụm “Không theo dõi”. Đổi biểu cảm: “Không theo dõi” → neutral
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** arrow_down, shadow, wallet
- **Chữ trên màn hình:** Không kiểm soát được!
- **Chuyển cảnh:** cut

## s03 · Bước một: Ghi lại

![s03](previews/s03.png)

- **Lời đọc:** Bước đầu tiên rất đơn giản: ghi lại mọi khoản chi trong ngày. Cốc cà phê, tiền xe, bữa trưa. Ghi hết. Không cần app xịn, một tờ giấy là đủ.
- **Phụ đề (từng đoạn, 1 dòng):** Bước đầu tiên rất đơn giản: / ghi lại mọi khoản chi trong ngày. / Cốc cà phê, tiền xe, / bữa trưa. / Ghi hết. / Không cần app xịn, / một tờ giấy là đủ.
- **Nhân vật:** Bi, biểu cảm `neutral`, tư thế mở đầu `point`
- **Hành động:** `point` tại cụm “ghi lại mọi khoản chi”; `nod` tại cụm “Không cần app xịn”. Đổi biểu cảm: “rất đơn giản” → happy
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** ai:notebook_ai, bill, pills
- **Chữ trên màn hình:** (chữ nằm trong biểu đồ/hóa đơn)
- **Chuyển cảnh:** cut

## s04 · Bước hai: Chia nhóm thu nhập

![s04](previews/s04.png)

- **Lời đọc:** Tiếp theo, chia thu nhập thành các nhóm. Chi phí cố định như nhà, điện, nước. Chi phí sinh hoạt như ăn uống, đi lại. Và một phần để dành.
- **Phụ đề (từng đoạn, 1 dòng):** Tiếp theo, chia thu nhập thành các nhóm. / Chi phí cố định như nhà, / điện, nước. / Chi phí sinh hoạt như ăn uống, / đi lại. / Và một phần để dành.
- **Nhân vật:** Bi, biểu cảm `neutral`, tư thế mở đầu `idle`
- **Hành động:** `point_seq` lúc 0 s. Đổi biểu cảm: “chia thu nhập” → happy
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** ai:piggy_ai, legend, pie
- **Chữ trên màn hình:** (chữ nằm trong biểu đồ/hóa đơn)
- **Chuyển cảnh:** cut

## s05 · Ví dụ minh họa

![s05](previews/s05.png)

- **Lời đọc:** Ví dụ thu nhập mười triệu một tháng. Bạn có thể dành bốn triệu cho chi phí cố định, ba triệu sinh hoạt, hai triệu để dành, một triệu giải trí. Con số này là của bạn, bạn tự chọn.
- **Phụ đề (từng đoạn, 1 dòng):** Ví dụ thu nhập mười triệu một tháng. / Bạn có thể dành bốn triệu cho chi phí cố / định, ba triệu sinh hoạt, / hai triệu để dành, / một triệu giải trí. / Con số này là của bạn, / bạn tự chọn.
- **Nhân vật:** Bi, biểu cảm `happy`, tư thế mở đầu `point`
- **Hành động:** `point_seq` lúc 0 s. Đổi biểu cảm: “Con số này là của bạn” → neutral
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** chart
- **Chữ trên màn hình:** (chữ nằm trong biểu đồ/hóa đơn)
- **Chuyển cảnh:** cut

## s06 · Xem lại cuối tháng

![s06](previews/s06.png)

- **Lời đọc:** Cuối tháng, dành mười lăm phút xem lại. Nhóm nào vượt, nhóm nào còn dư. Rồi điều chỉnh cho tháng sau. Vài tháng là bạn hiểu rõ thói quen chi tiêu của mình.
- **Phụ đề (từng đoạn, 1 dòng):** Cuối tháng, dành mười lăm phút xem lại. / Nhóm nào vượt, nhóm nào còn dư. / Rồi điều chỉnh cho tháng sau. / Vài tháng là bạn hiểu rõ thói quen chi / tiêu của mình.
- **Nhân vật:** Bi, biểu cảm `thinking`, tư thế mở đầu `cheek_b`
- **Hành động:** `point_seq` lúc 0 s; `nod` tại cụm “điều chỉnh cho tháng sau”. Đổi biểu cảm: “Vài tháng” → happy
- **Bối cảnh:** nền `cream`
- **Đạo cụ / hình:** chart
- **Chữ trên màn hình:** Điều chỉnh & cải thiện
- **Chuyển cảnh:** cut

## s07 · Kết: Chủ động với tiền

![s07](previews/s07.png)

- **Lời đọc:** Lập ngân sách không cần giỏi toán. Chỉ cần ghi lại, chia nhóm, và xem lại mỗi tháng. Làm đều đặn, bạn sẽ chủ động hơn với tiền của mình. Bắt đầu ngay tháng này nhé.
- **Phụ đề (từng đoạn, 1 dòng):** Lập ngân sách không cần giỏi toán. / Chỉ cần ghi lại, chia nhóm, / và xem lại mỗi tháng. / Làm đều đặn, bạn sẽ chủ động hơn với / tiền của mình. / Bắt đầu ngay tháng này nhé.
- **Nhân vật:** Bi, biểu cảm `happy`, tư thế mở đầu `cheer`
- **Hành động:** `cheer` tại cụm “bạn sẽ chủ động hơn”; `wave` tại cụm “Bắt đầu ngay tháng này”. Đổi biểu cảm: “Làm đều đặn” → happy
- **Bối cảnh:** nền `ai:calm_room_ai`
- **Đạo cụ / hình:** pills, sparkle
- **Chữ trên màn hình:** Bắt đầu ngay hôm nay!
- **Chuyển cảnh:** fade-out

## Điểm cần bạn duyệt
1. Mạch kể và thứ tự các cảnh.
2. Lời đọc từng cảnh (đây là văn bản sẽ gửi API giọng đọc).
3. Thông tin cần kiểm chứng (nếu có).
4. Hình ảnh, hành động từng cảnh.

Sau khi bạn duyệt: tôi mới gọi API giọng nói (một lần cho từng cảnh), rồi dựng bản xem thử.
