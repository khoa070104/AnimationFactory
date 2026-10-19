# Animation Factory – hướng dẫn vận hành (Phase 2)

Công cụ sản xuất video giải thích 2D từ **dữ liệu** (storyboard JSON). Làm video mới = tạo dự án mới và nhập dữ liệu; không sửa Python/JSX.

## 1. Cách nhanh nhất: giao diện
```
python phase2\ui\server.py            (hoặc chạy phase2\ui\ui.bat)  ->  mở http://127.0.0.1:8765/
```
Chỉ nghe ở 127.0.0.1, có token mỗi lần chạy. Bốn khu vực:
- **Nội dung:** đề bài, trạng thái duyệt, dự toán, kịch bản lời đọc, ô JSON để nhập/sửa storyboard (Kiểm tra → Lưu; lưu bản cũ vào `versions/`, tăng phiên bản). **Duyệt phiên bản này** gắn với đúng nội dung đang hiển thị (nội dung đổi thì từ chối).
- **Storyboard:** thẻ từng cảnh (ảnh xem trước, sửa lời, phụ đề tự tạo lại, góp ý, cờ "đổi lời / đổi hình sau khi duyệt", nút dựng lại cảnh).
- **Dựng phim:** nút tạo xem trước và chạy sản xuất, tiến độ từng công đoạn, lỗi ở công đoạn nào, kết quả kiểm tra, nhật ký.
- **Kết quả:** video xem thử, project chỉnh sửa được, asset AI (duyệt/loại, gửi yêu cầu tạo).

## 2. Dòng lệnh
```
python phase2\tools\new_project.py ten_du_an --title "Tiêu đề"
# nhập projects\ten_du_an\storyboard.json  (xem mục 4)
python phase2\tools\produce.py projects\ten_du_an --until storyboard   # kiểm tra + xem trước + dự toán
python phase2\tools\approve.py projects\ten_du_an --by "tên người duyệt"  # chỉ sau khi chủ dự án duyệt
python phase2\tools\produce.py projects\ten_du_an                      # giọng (có chốt chặn) -> hoạt ảnh -> phụ đề -> MP4
```
`produce.py` ghi tiến độ và công đoạn lỗi vào `status.json` (`steps`) và `logs\`. Dừng ở `awaiting_approval` nếu chưa duyệt (không gọi API trả phí).

## 3. Quy tắc tiết kiệm và an toàn
- Giọng: chỉ tạo sau khi duyệt đúng phiên bản; **câu đã có giọng ở bất kỳ dự án nào dùng lại từ kho dùng chung** (`voice_cache`, khóa = lời + giọng + tốc độ), không gọi API.
- Dựng: mỗi cảnh có chữ ký riêng (dữ liệu cảnh + audio + đúng các hình nó dùng + rig + đúng các hành động/tư thế nó dùng + camera). Đổi hình chỉ dựng cảnh liên quan; đổi một hành động trong thư viện chỉ dựng các cảnh dùng hành động đó; đổi rig dựng mọi cảnh. QA chuyển động được lưu theo từng clip.
- Dự toán: `estimate.json` từ `cost_model.json` (hiệu chỉnh bằng `calibrate.py` từ job thật). Chi phí thực tế ở `status.json`; asset AI chỉ có số token (không có tiền/credit).
- Cấu hình công cụ: `AF_EFFECTCRAFT`, `AF_FILMCRAFT`, `AF_VECTORCRAFT`, `AF_FONT` hoặc `phase2\config.json {"paths": {...}}` (`python phase2\tools\toolpaths.py` để kiểm tra).

## 4. Dữ liệu storyboard (tóm tắt)
Mức dự án: `project, title, version, voice{voice_id,speed}`, tùy chọn `timing{lead,tail,word_pad}`, `export{fade_out}`, `character{shirt}`, `targets{duration:[min,max], scenes:[min,max]}` (mặc định 60–90 s, 6–10 cảnh), `subtitle_max_chars`, `review_points`.
Mức cảnh: `id, title, voice, bg (cream|blue|#RRGGBB|ai:<id>), bi{x,y,scale,face,pose,frontArms}`, tùy chọn `subtitles` (bỏ trống = tự chia ≤40 ký tự), `holds[]`, `rest`, `hold_after`, `camera` (`push_in|pull_out|pan_left|pan_right` hoặc `{zoom:[a,b], pan:[[x0,y0],[x1,y1]]}`), `actions[]` (`enter, point, point_seq, cheer, wave, cheek, hold_phone, shrug, nod`; mốc `at` giây hoặc `cue` = cụm trong lời đọc), `face_cues[]`, `items[]`.
Mục: `prop` (thư viện hoặc `ai:<id>`), `text`, `notice`, `chart`, `pills`, `pie`, `legend`, `bill`; mỗi mục có `appear` (giây hoặc cụm lời đọc). `validate_storyboard.py` báo lỗi (cue không có trong lời, hành động/tư thế/biểu cảm lạ, asset AI chưa duyệt, phụ đề lệch…) **trước** khi gọi API.

## 5. Asset AI (Antigravity)
`assets_mcp/README.md`: MCP hai công cụ `submit_asset_job` / `check_asset_job` (hoặc `agy_image.py`, hoặc giao diện). Asset mới là bản nháp, chủ dự án duyệt, cảnh dùng `ai:<id>` cho prop và `bg`.

## 6. Kiểm thử và bằng chứng
`python phase2\tests\test_*.py` (baseline Bi v2.1 giống từng điểm ảnh, chuyển động, giọng, validator, phụ thuộc, AI asset, MCP, giao diện). `phase2\evidence\` chứa log nghiệm thu; `phase2\ACCEPTANCE_PHASE2.md` là báo cáo tổng hợp.

## 7. Giới hạn
Đạo cụ là thư viện cố định (vật mới cần SVG hoặc asset AI); chỉ tay phải; bố cục do người nhập chọn tọa độ; chuyển cảnh chỉ là cắt thẳng (và mờ dần cuối video); nhân vật chỉ đổi màu áo; giọng chỉ thử với Edge HoaiMy; asset AI là ảnh tĩnh, không tự tách bộ phận để chuyển động.
