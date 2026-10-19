# Sample A — thay đổi và danh sách ảnh cuối để chốt lượt sinh

Storyboard v5 · 8 cảnh · lời 1200 ký tự (~83,3 s, trong khoảng 60–90 s) · bộ dựng Remotion (`renderer: remotion` khi chạy `produce.py --renderer remotion`).

## Đã đổi so với bản trước
- Lời s06: "hạn chế mua thừa và bỏ phí" (bỏ khẳng định tuyệt đối).
- Không còn emoji; tên nhân vật chính là Tuấn, phụ là Linh. Hồ sơ Minh cũ đã chuyển khỏi thư mục nhân vật.
- Bảng thực đơn (s05) là `grid` do Craft/Remotion vẽ, chữ tiếng Việt chính xác, điền từng ô theo lời. Hiện 4 ô (Thứ Hai, Ba, Tư, "Thứ Năm–CN"); bảng đủ 7 ô cần bố cục khác vì vùng giữa chỉ rộng ~400 px khi có hai nhân vật (chưa làm).
- Tương tác: Linh viết (bút tay phải + sổ thư viện tay trái) ở s03, s05, s06; Tuấn xách giỏ ở s02, s07. Các hành động chưa thể hiện đúng (mở tủ lạnh, xếp đồ vào tủ, ngồi ăn…) được ghi vào `action_gaps` của từng cảnh, không bị đổi âm thầm.
- 7 chỗ đạo cụ/chữ chồng nhau đã được dời tự động (công cụ mới `layout.nudge`, không gọi AI).
- Số cảnh theo thời lượng/brief; kế hoạch asset không còn ảnh tham chiếu của Bi hay sample.

## Danh sách ảnh cuối (9 ảnh, trần 14)
| # | Ảnh | Dùng ở cảnh | Cách đưa vào video |
|---|---|---|---|
| 1–2 | Tuấn: bảng bộ phận + bảng 5 khuôn mặt | tất cả cảnh có Tuấn | rig (khớp, chuyển động) |
| 3–4 | Linh: bảng bộ phận + bảng 5 khuôn mặt | s03–s06, s08 | rig |
| 5 | `bg_kitchen` nền bếp–phòng ăn | s01, s03, s04, s05, s06, s07, s08 | nền cảnh (một ảnh dùng chung 7 cảnh) |
| 6 | `bg_supermarket` nền siêu thị | s02 | nền cảnh |
| 7 | `prop_messy_fridge` tủ lạnh bừa | s01, s04 | đạo cụ cạnh nhân vật (trạng thái "trước") |
| 8 | `prop_tidy_fridge` tủ lạnh gọn | s07 | đạo cụ ("sau") |
| 9 | `prop_shopping_bag` túi đi chợ đầy | s07 | cầm trong tay Tuấn (`hold`) |

Dự phòng sinh lại khi ảnh nhân vật hỏng (tối đa 1 lần mỗi ảnh nhân vật): +4 → trần xấu nhất 13/14.
Bút, giỏ, sổ, bảng ô, chữ, phụ đề là thành phần dựng bằng code/thư viện, không tốn ảnh.

## Giọng
1200 ký tự → ước tính **860 credit** (trần đã đặt 1200). Chỉ chạy sau khi bạn duyệt nội dung (kịch bản + storyboard v5) và đồng ý dùng credit.

## Việc cần bạn làm (tôi không tự làm thay)
1. Duyệt kế hoạch asset (9 ảnh ở trên) để tôi sinh bằng Antigravity thật.
2. Sau khi ảnh sinh ra: duyệt từng ảnh nhân vật/asset trong giao diện (duyệt gắn với đúng file).
3. Duyệt kịch bản + storyboard, đồng ý dùng ~860 credit giọng → tôi tạo giọng thật và dựng bản nghiệm thu bằng Remotion.
