# Sample A bản nháp v14 — đã sửa theo review (phần dùng chung)

Video: `output/sample_a_thuc_don_tuan_v14_draft.mp4` (83,5 s, 8 cảnh, Remotion, giọng nháp im lặng). Kiểm tra tự động đạt: 1080p có audio, tiêu chí khóa trước, thời lượng, số cảnh, phụ đề, độ trễ cue, chuyển động. Đây không thay cho việc bạn xem/nghe.

## Lỗi trong video → cách sửa ở thành phần dùng chung
| Lỗi thấy | Sửa chung | Bằng chứng |
|---|---|---|
| Icon ảnh tải lỗi (s06) | Bộ xuất thiếu ảnh ô màu/mũi tên của chú giải; nay xuất đủ **và từ chối dựng nếu bất kỳ ảnh nào thiếu** | test_remotion kiểm swatch; lỗi "pictures missing from the export" |
| Bảng 4 ô dù lời nói 7 ngày | Validator **báo lỗi** khi số ô ≠ số lời nói ("bảy ô/ngày/mục"); bảng 1 cột là danh sách 1 dòng/hàng; prompt dặn rõ | test; s05 nay đủ 7 hàng, 3 hàng điền theo lời |
| Tủ lạnh nổi che bảng; chữ chồng nền | `layout.compose`: nhân vật ra hai mép, **mọi nội dung xếp dọc trong một khung** giữa hai nhân vật, ảnh lớn nằm trong khung, đạo cụ nhỏ do `nudge` đặt chỗ trống; có **nền mờ** phía sau khối nội dung khi nền là ảnh; mọi vật che nhân vật hay che nội dung bị báo | test_layout + test_phase4_feedback; s04 dùng danh sách nguyên liệu + tủ lạnh trong khung |
| Túi bị lật trên đầu khi giơ tay; túi quá to | `cheer` khi một tay đang cầm chỉ giơ tay còn lại; túi cầm tay nhỏ hơn (≤170 px); validator cảnh báo hành động khác làm vật cầm vung theo | test; s07 túi giữ thẳng; s02 bỏ nhún vai |
| Thẻ trắng chỉ có dấu tích (s06) | Validator cảnh báo prop `card`; bỏ khỏi s06 | — |
| Lời "đang ngồi viết" nhưng nhân vật đứng | Đổi một câu s03: "đang ngồi viết gì đó ở bàn" → **"đang viết gì đó vào sổ"** (lời cần bạn duyệt trước khi tạo giọng) | storyboard v10 |

## Còn lại (nói thẳng)
- Chưa thể hiện: mở cửa tủ lạnh, xếp đồ vào tủ, ngồi ăn (ghi trong `action_gaps` từng cảnh); Linh "viết" bằng cách cầm sổ trước ngực, chưa có tư thế ngồi viết.
- Linh cầm bút ở tay phải nên khi chỉ tay/vẫy bút vung theo (validator cảnh báo, chưa đổi hành động).
- Chuyển động mới chỉ kiểm bằng QA tự động và mắt tôi qua khung hình; bạn cần xem video thật.
- Khi chỉnh dữ liệu (bảng 7 hàng, danh sách s04, bỏ shrug, bỏ thẻ) tôi sửa tay storyboard (v9–v14); lần chạy AI sau sẽ tự sinh đúng nhờ quy tắc mới nhưng chưa chạy lại để kiểm chứng.

## Nghiệm thu "đổi dữ liệu thì dựng lại đúng phần liên quan"
Bỏ một hành động ở s02 → dựng lại chỉ s02 (24 s), 7 cảnh còn lại dùng lại; không gọi API ảnh/giọng.

## Lời cần duyệt trước khi tạo giọng
Chỉ 2 câu thay đổi so với kịch bản AI: s03 ("đang viết gì đó vào sổ") và s06 ("hạn chế mua thừa và bỏ phí"). Giọng ước tính 860 credit.
