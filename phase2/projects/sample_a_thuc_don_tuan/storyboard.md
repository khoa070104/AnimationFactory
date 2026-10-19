# Storyboard · Lên thực đơn tuần để đỡ tốn tiền ăn (v17)

**Trạng thái:** bản nháp do AI soạn - chờ duyệt. **Giọng đã tạo:** 8 lượt gọi, 858 credit thực tế. Đối tượng: người đi làm trẻ, mới bắt đầu quản lý tiền.

**Thông điệp:** Quyết định bữa ăn trước khi đi chợ giúp tiết kiệm tiền và đỡ bỏ đồ ăn hỏng

![Tổng quan](previews/contact_sheet.png)

## Tổng hợp
- 8 cảnh, 1191 ký tự lời đọc, **ước tính 82.6 giây** (tốc độ đọc ≈ 15.3 ký tự/giây, cộng khoảng nghỉ đầu/cuối cảnh theo cấu hình `timing`/`hold_after`).
- **Ước tính chi phí giọng đọc: ≈ 853 credit** cho lần tạo đầu (giọng Edge `edge_vi-VN-HoaiMyNeural`, kèm mốc thời gian từng từ). Cách tính: 0.716 credit/ký tự (25 real Edge-voice jobs (2778 chars, 1989 credits incl. word timings); 3059 chars over 200 s of speech). Đây là ước tính, chỉ áp dụng cho giọng Edge, không quy ra tiền; số thật sẽ ghi vào log sau khi chạy.
- Sửa lời một cảnh chỉ tạo lại giọng của cảnh đó (tính theo ký tự cảnh đó); lời, giọng, tốc độ không đổi thì không gọi API.

| Cảnh | Tiêu đề | Ký tự | Ước tính (s) | Credit | Chuyển cảnh |
|---|---|---|---|---|---|
| s01 | Tủ lạnh đầy mà vẫn không có gì ăn | 136 | 9.5 | 97 | cut |
| s02 | Vòng lặp quen thuộc | 152 | 10.5 | 109 | cut |
| s03 | Bạn cùng nhà có mẹo hay | 124 | 8.7 | 89 | cut |
| s04 | Bước một: kiểm tra tủ lạnh trước | 164 | 11.3 | 117 | cut |
| s05 | Bước hai: đặt bữa ăn vào khung tuần | 163 | 11.3 | 117 | cut |
| s06 | Bước ba: viết danh sách chợ từ thực đơn | 152 | 10.5 | 109 | cut |
| s07 | Tuấn thử áp dụng | 133 | 9.3 | 95 | cut |
| s08 | Kết quả và thông điệp chốt | 167 | 11.5 | 120 | fade-out |

## s01 · Tủ lạnh đầy mà vẫn không có gì ăn

![s01](previews/s01.png)

- **Lời đọc:** Tuấn nhìn vào tủ lạnh... rau héo, thịt quên rã đông, hộp đồ ăn thừa không rõ mua hồi nào. Cuối tuần lại phải đổ bỏ. Tiền đi đâu hết vậy?
- **Phụ đề (từng đoạn, 1 dòng):** Tuấn nhìn vào tủ lạnh... / rau héo, thịt quên rã đông, / hộp đồ ăn thừa không rõ mua hồi nào. / Cuối tuần lại phải đổ bỏ. / Tiền đi đâu hết vậy?
- **Nhân vật:** Bi, biểu cảm `worried`, tư thế mở đầu `idle`
- **Hành động:** `enter` lúc 0 s; `cheek` tại cụm “lại phải đổ bỏ”; `shrug` tại cụm “Tiền đi đâu hết vậy”. Đổi biểu cảm: “rau héo” → worried; “Tiền đi đâu hết vậy” → surprised
- **Bối cảnh:** nền `ai:bg_kitchen`
- **Đạo cụ / hình:** ai:prop_messy_fridge, exclaim, wallet
- **Chữ trên màn hình:** Tiền đi đâu hết?
- **Chuyển cảnh:** cut

## s02 · Vòng lặp quen thuộc

![s02](previews/s02.png)

- **Lời đọc:** Tuấn hay ghé siêu thị sau giờ làm, thấy gì rẻ mua nấy, về nhà không biết nấu gì. Vài ngày sau, đồ ăn hỏng, lại đặt đồ ăn ngoài. Rồi lại mua. Rồi lại bỏ.
- **Phụ đề (từng đoạn, 1 dòng):** Tuấn hay ghé siêu thị sau giờ làm, / thấy gì rẻ mua nấy, / về nhà không biết nấu gì. / Vài ngày sau, đồ ăn hỏng, / lại đặt đồ ăn ngoài. / Rồi lại mua. / Rồi lại bỏ.
- **Nhân vật:** Bi, biểu cảm `neutral`, tư thế mở đầu `idle`, cầm basket, phone
- **Hành động:** `carry` tại cụm “ghé siêu thị”; `hold_phone` tại cụm “lại đặt đồ ăn ngoài”. Đổi biểu cảm: “không biết nấu gì” → worried; “Rồi lại bỏ” → worried
- **Bối cảnh:** nền `ai:bg_supermarket`
- **Đạo cụ / hình:** arrow_down, pills
- **Chữ trên màn hình:** Vòng lặp quen thuộc
- **Chuyển cảnh:** cut

## s03 · Bạn cùng nhà có mẹo hay

![s03](previews/s03.png)

- **Lời đọc:** Một buổi tối, Linh, bạn cùng nhà, đang viết gì đó vào sổ. Tuấn hỏi. Linh cười: lập thực đơn tuần đấy, mất có mười phút thôi.
- **Phụ đề (từng đoạn, 1 dòng):** Một buổi tối, Linh, / bạn cùng nhà, đang viết gì đó vào sổ. / Tuấn hỏi. / Linh cười: / lập thực đơn tuần đấy, / mất có mười phút thôi.
- **Nhân vật:** Bi, biểu cảm `thinking`, tư thế mở đầu `idle`, cầm pen, notebook
- **Hành động:** `point` tại cụm “Tuấn hỏi”; `nod` tại cụm “mười phút thôi”. Đổi biểu cảm: “Tuấn hỏi” → neutral; “mười phút thôi” → surprised
- **Bối cảnh:** nền `ai:bg_kitchen`
- **Đạo cụ / hình:** notice, sparkle
- **Chữ trên màn hình:** Mẹo hay của Linh
- **Chuyển cảnh:** cut

## s04 · Bước một: kiểm tra tủ lạnh trước

![s04](previews/s04.png)

- **Lời đọc:** Linh giải thích: trước hết, xem tủ lạnh còn gì. Trứng còn ba quả, cà rốt còn một nửa, đậu hũ chưa mở. Liệt kê hết ra. Đây là nguyên liệu sẵn có, không cần mua thêm.
- **Phụ đề (từng đoạn, 1 dòng):** Linh giải thích: / trước hết, xem tủ lạnh còn gì. / Trứng còn ba quả, cà rốt còn một nửa, / đậu hũ chưa mở. / Liệt kê hết ra. / Đây là nguyên liệu sẵn có, / không cần mua thêm.
- **Nhân vật:** Bi, biểu cảm `neutral`, tư thế mở đầu `idle`
- **Hành động:** `nod` tại cụm “Liệt kê hết”. Đổi biểu cảm: “xem tủ lạnh còn gì” → thinking; “không cần mua thêm” → happy
- **Bối cảnh:** nền `ai:bg_kitchen`
- **Đạo cụ / hình:** ai:prop_messy_fridge, grid
- **Chữ trên màn hình:** Bước 1: Kiểm tra tủ lạnh
- **Chuyển cảnh:** cut

## s05 · Bước hai: đặt bữa ăn vào khung tuần

![s05](previews/s05.png)

- **Lời đọc:** Tiếp theo, Linh kẻ bảy ô tương ứng bảy ngày, điền bữa tối vào từng ô. Không cần cầu kỳ: thứ Hai trứng sốt cà, thứ Ba đậu hũ xào rau, thứ Tư canh. Đơn giản là được.
- **Phụ đề (từng đoạn, 1 dòng):** Tiếp theo, Linh kẻ bảy ô tương ứng bảy / ngày, điền bữa tối vào từng ô. / Không cần cầu kỳ: / thứ Hai trứng sốt cà, / thứ Ba đậu hũ xào rau, / thứ Tư canh. / Đơn giản là được.
- **Nhân vật:** Bi, biểu cảm `neutral`, tư thế mở đầu `idle`, cầm pen, notebook
- **Hành động:** `nod` tại cụm “Đơn giản là được”. Đổi biểu cảm: “Không cần cầu kỳ” → happy
- **Bối cảnh:** nền `ai:bg_kitchen`
- **Đạo cụ / hình:** grid
- **Chữ trên màn hình:** Bước 2: Lập khung tuần
- **Chuyển cảnh:** cut

## s06 · Bước ba: viết danh sách chợ từ thực đơn

![s06](previews/s06.png)

- **Lời đọc:** Từ thực đơn đó, Linh lập danh sách mua đúng những gì còn thiếu. Không mua theo cảm hứng nữa. Có danh sách, vào chợ ra nhanh, hạn chế mua thừa và bỏ phí.
- **Phụ đề (từng đoạn, 1 dòng):** Từ thực đơn đó, Linh lập danh sách mua / đúng những gì còn thiếu. / Không mua theo cảm hứng nữa. / Có danh sách, vào chợ ra nhanh, / hạn chế mua thừa và bỏ phí.
- **Nhân vật:** Bi, biểu cảm `neutral`, tư thế mở đầu `idle`, cầm pen, notebook
- **Hành động:** `nod` tại cụm “vào chợ ra nhanh”. Đổi biểu cảm: “Có danh sách” → happy
- **Bối cảnh:** nền `ai:bg_kitchen`
- **Đạo cụ / hình:** legend
- **Chữ trên màn hình:** Bước 3: Danh sách đi chợ
- **Chuyển cảnh:** cut

## s07 · Tuấn thử áp dụng

![s07](previews/s07.png)

- **Lời đọc:** Cuối tuần, Tuấn tự làm thực đơn lần đầu. Mười phút xong. Cầm danh sách ra chợ, mua đúng, về nhà, tủ lạnh gọn gàng. Cảm giác khác hẳn.
- **Phụ đề (từng đoạn, 1 dòng):** Cuối tuần, Tuấn tự làm thực đơn lần đầu. / Mười phút xong. / Cầm danh sách ra chợ, / mua đúng, về nhà, tủ lạnh gọn gàng. / Cảm giác khác hẳn.
- **Nhân vật:** Bi, biểu cảm `neutral`, tư thế mở đầu `idle`, cầm basket, ai:prop_shopping_bag
- **Hành động:** `carry` tại cụm “Cầm danh sách ra chợ”; `cheer` tại cụm “Cảm giác khác hẳn”. Đổi biểu cảm: “Mười phút xong” → surprised; “Cảm giác khác hẳn” → happy
- **Bối cảnh:** nền `ai:bg_kitchen`
- **Đạo cụ / hình:** ai:prop_tidy_fridge, notice, sparkle
- **Chữ trên màn hình:** Tuấn tự tin áp dụng
- **Chuyển cảnh:** cut

## s08 · Kết quả và thông điệp chốt

![s08](previews/s08.png)

- **Lời đọc:** Quyết định bữa ăn trước khi đi chợ giúp mình mua đúng, nấu đủ, bỏ ít hơn. Chỉ mười phút lập thực đơn, cả tuần bớt lo chuyện ăn uống và bớt thấy tiền không cánh mà bay.
- **Phụ đề (từng đoạn, 1 dòng):** Quyết định bữa ăn trước khi đi chợ giúp / mình mua đúng, nấu đủ, / bỏ ít hơn. / Chỉ mười phút lập thực đơn, / cả tuần bớt lo chuyện ăn uống và bớt / thấy tiền không cánh mà bay.
- **Nhân vật:** Bi, biểu cảm `happy`, tư thế mở đầu `idle`
- **Hành động:** `cheer` tại cụm “Chỉ mười phút lập thực đơn”; `nod` tại cụm “bớt lo chuyện ăn uống”. Đổi biểu cảm: “Quyết định bữa ăn” → happy; “tiền không cánh mà bay” → happy
- **Bối cảnh:** nền `ai:bg_kitchen`
- **Đạo cụ / hình:** pills, sparkle
- **Chữ trên màn hình:** 3 Lợi ích khi đi chợ
- **Chuyển cảnh:** fade-out

## Điểm cần bạn duyệt
1. Mạch kể và thứ tự các cảnh.
2. Lời đọc từng cảnh (đây là văn bản sẽ gửi API giọng đọc).
3. Thông tin cần kiểm chứng (nếu có).
4. Hình ảnh, hành động từng cảnh.

Sau khi bạn duyệt: tôi mới gọi API giọng nói (một lần cho từng cảnh), rồi dựng bản xem thử.
