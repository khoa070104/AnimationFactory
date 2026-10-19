# Chặng 1 — bảng năng lực, quyết định thiết kế (20/10/2026)
Nguồn: 3 subagent đọc mã (R1 năng lực, R2 hợp đồng CLI/MCP, R4 Remotion). R3 (video tham chiếu) không chạy: chưa có file, dùng phân tích trong bản giao việc.

## Hiện có / thiếu (bằng chứng do subagent đọc mã, chưa chạy test)
| Năng lực | Trạng thái | Module đổi |
|---|---|---|
| Schema scene + validate + cue bằng cụm lời | Có (`sbload.normalise`, `validate_storyboard`) | thêm `shots` (tương thích ngược) |
| Cấp shot | Thiếu | `tools/shots.py` (mới) |
| Camera | Chỉ Craft, 1 preset/scene; **Remotion không có**, `export_remotion` bỏ `camera` | export + `Clip.tsx` |
| Lớp world/screen | Thiếu: panel là prop trong `prims`; phụ đề đã vẽ sau cùng | `Clip.tsx`, `prims.space` |
| Hộp bao nhân vật/đạo cụ | Một phần: item có hộp (`layout.item_boxes`), nhân vật cứng ±200×600 | `shots.char_box` từ rig height×scale |
| Trạng thái qua đổi shot | Pose là hàm thuần của `t` → đổi shot không chạy lại enter nếu camera cũng là hàm của `t` | giữ, không bọc Sequence theo shot |
| Gaze | Chỉ `flip`; không có đích nhìn | `shots.gaze` → lịch flip + nghiêng đầu |
| Whitelist khóa scene | `sbstore.validate_obj`, prompt AI, `merge_scenes` | thêm `shots` |
| CLI | Rời rạc, log/stdout lẫn, không JSON (trừ `capabilities`) | lớp `af.py` bọc hàm, không bọc stdout |
| Job id | Chỉ ảnh agy (`agy_jobs`); còn lại không | job record mỏng (pid/log/exit) |
| Khóa dự án | Không có; `sbstore.save` không so hash; approve CLI không kiểm hash | `expect_hash` + khóa file dự án |
| MCP | Chỉ assets; đang "Pending approval" | adapter dùng chung lõi `af` |
| Duyệt | `approve.py` CLI cho phép tự duyệt | **không** đưa approve vào lệnh của AI |

## Quyết định thiết kế (từ phản hồi chủ dự án)
1. **Shot có thời gian**: `start` (giây hoặc cụm lời); kéo dài đến shot sau; `end` sớm hơn = khoảng trống có chủ đích (về toàn cảnh); `end` muộn hơn shot sau = chồng lấn → lỗi. Camera là hàm thuần của thời gian cảnh; nhân vật/đạo cụ giữ trạng thái, không chạy lại động tác xuất hiện.
2. **Khung hình theo kích thước đối tượng**: hộp bao + đệm + giới hạn zoom 2,2 (ảnh raster mềm quá mức đó) + giữ trong canvas + trên dải phụ đề. Nhân vật cao hơn/đạo cụ to hơn → khung tự đổi.
3. **Lớp theo vai trò**: phụ đề luôn `screen`; vật/nhãn trên vật `world` đi theo camera; bảng/panel mặc định `world`, đặt `space:"screen"` khi cần cố định.
4. **Lớp điều khiển tối thiểu**: capabilities → project get/put → validate → preview → render → artifacts (+ jobs đủ để tiếp tục; estimate dùng sẵn).
5. **Nghiệm thu bằng dữ liệu**: đổi mục tiêu camera/vị trí; nhãn dài; asset không tồn tại → lỗi chỉ đúng shot/trường; sửa dữ liệu rồi dựng được, không sửa mã theo mẫu.
