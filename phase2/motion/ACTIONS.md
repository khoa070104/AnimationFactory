# Thư viện hành động Bi v2 (lib/bi_motion.jsx)

**Biểu cảm (5):** happy, neutral, worried, surprised, thinking. Đổi biểu cảm bằng chuyển mờ 0,15 s giữa hai lớp mặt cùng pivot.

**Hành động (8):**
| Tên | Mô tả | Thời lượng mặc định |
|---|---|---|
| `enter` | đi vào từ trái, chân và tay đung đưa, dừng có nảy nhẹ | 1,45 s |
| `point` | chỉ tay phải (tham số `hold`, `speed`) | 2,2 s |
| `cheer` | hai tay giơ mừng, nhún lên | 2,25 s |
| `wave` | vẫy tay phải (6 nhịp) | ~2,3 s |
| `cheek` | tay phải lên má, lo lắng, đầu nghiêng | 2,2 s |
| `hold_phone` | cầm điện thoại trước ngực (đạo cụ gắn vào khớp bàn tay) | 2,4 s |
| `shrug` | nhún vai, mặt suy nghĩ | 1,6 s |
| `nod` | gật đầu 3 lần | 1,9 s |

**Tư thế tên sẵn:** idle, point, cheer, wave_a/b, cheek, cheek_b, phone, shrug, nod_a/b, step_a/b. Chuyển trực tiếp giữa hai tư thế bất kỳ (không cần về idle); khuỷu tay không bao giờ quay qua tư thế gập hết (luôn duỗi qua 0), vai/đầu/chân đi đường ngắn nhất.

**Đạo cụ cầm tay:** `holdProp(comp, bi, "R"|"L", ảnh, scale, pivot, rot, offset)` gắn vào null `hand_R/hand_L`, đi theo cánh tay chính xác.

**Kiểm tra tự động:** `tools/check_motion.py` (xem motion/motion_report.json) và `tests/test_motion_checks.py`.
