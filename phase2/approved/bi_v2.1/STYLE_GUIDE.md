# Phong cách hoạt hình – Bi v2 (bản duyệt)

Trạng thái: **Hướng phong cách đã được duyệt; bản chỉnh v2.1 (khung 03 cận cảnh, vai/tay áo liền thân) chờ duyệt tính nhất quán.** Chưa mở rộng bộ nhân vật hay dựng video. Ba khung mẫu: `frames/frame01.png`, `frame02.png`, `frame03.png` (1920×1080); xem nhanh: `contact_sheet.png`.
Mọi giá trị dưới đây nằm trong `tokens.json`; mã sinh hình và dựng đều đọc từ file đó, đổi một chỗ là đổi toàn bộ.

## 1. Nguyên tắc
2D phẳng, tối giản, cho người trưởng thành. Mỗi cảnh có **một điểm tập trung** (khung 01: thông báo lương; 02: biểu đồ; 03: hóa đơn). Biểu cảm và đạo cụ kể chuyện, chữ ít.

## 2. Màu
| Vai trò | Mã | Dùng cho |
|---|---|---|
| Nét (ink) | `#1D1D1F` | mọi đường viền, mắt, miệng |
| Nền kem | `#FFF6E5` | cảnh vui / trung tính |
| Nền xanh nhạt | `#E7EEF5` | cảnh lo lắng / bất ngờ |
| Cam nhận diện của Bi | `#F26B21` | áo Bi (đổi bằng `--shirt`) |
| Da | `#FFE3C2` | đầu, tay |
| Quần / giày | `#2F3A56` / `#FFFFFF` | Bi |
| Xanh dương `#3B6FD8`, vàng `#FFC83D`, hồng `#D8508F`, teal `#1FA79A` | biểu đồ, đạo cụ |
| Xanh lá `#2E9E5B` | tiền vào, tích cực |
| Đỏ `#D64545` | chi bất ngờ, cảnh báo |

Quy tắc: tô phẳng, không đổ bóng gradient; chỉ có một bóng mờ dưới chân (`shadow`).

## 3. Nét vẽ
Nét đen **8 px** (ở 1920×1080, trước khi scale), đầu nét tròn, góc tròn. Chi tiết nhỏ (phím máy tính, dấu tích) dùng 5–6 px. Hình dựng ở 2× rồi hiển thị 50% để nét sắc khi phóng 1,5×.

## 4. Chữ
Font **Inter** (có sẵn trong EffectCraft, hỗ trợ tiếng Việt), đậm. Tối thiểu: tiêu đề 64 px, nội dung 44 px, nhãn 40 px (đọc được trên điện thoại). Số tiền: xanh lá = vào, đỏ = chi bất ngờ, đen = trung tính. Phụ đề video không quá 2 dòng.

## 5. Bố cục
Canvas 1920×1080, 30 fps. Chia đôi: nhân vật bên trái (chân ở y≈975–1040), đạo cụ/biểu đồ bên phải; cảnh cận dùng scale 2,4 (khung 03: đầu to, thân cắt khỏi khung, bàn tay đặt ở má, cách xa lông mày). Chừa lề ≥ 60 px. Một cảnh không quá 3 nhóm vật thể chính.

## 6. Biểu cảm (5, đủ 4 yêu cầu) và hành động
Biểu cảm: `happy`, `neutral`, `worried`, `surprised`, `thinking`. Đổi biểu cảm = chuyển mờ giữa hai lớp mặt cùng pivot.
Hành động có thể thực hiện ngay bằng rig hiện tại (chưa dựng thành thư viện chuyển động, sẽ làm sau khi bạn duyệt phong cách): xuất hiện (trượt vào), chỉ tay (vai + khuỷu), giơ tay mừng, đưa tay lên đầu, gật/nghiêng đầu, nghiêng người. Khung 01, 02, 03 đã dùng ba tư thế đầu tiên.

## 7. Rig của Bi (pivot theo pixel 1×)
| Bộ phận | Pivot | Cha |
|---|---|---|
| `Bi_root` | gốc ở chân, scale tổng | – |
| `hip_L/R` (null) | (∓36, −186) | root |
| `leg` ×2 | (30, 10) | hip |
| `waist` (null) | (0, −186) | root |
| `torso` (240×210, có mũ vai liền thân) | (120, 202) | waist |
| `shoulder_L/R` (null) | (∓80, −168) | waist |
| `arm_upper` | (20, 15) | shoulder |
| `elbow_L/R` (null) | (0, 85) | shoulder |
| `arm_lower` | (20, 15) | elbow |
| `neck` (null) | (0, −196) | waist |
| `head`, `face_*` | (110, 200) | neck |

Thứ tự lớp (dưới lên): bóng, chân, tay trên (tay áo mọc từ dưới mũ vai), thân, tay dưới + bàn tay, đầu, mặt. Tùy chọn `frontArms:"R"` kéo tay dưới lên trên đầu. **IK hai đoạn:** `pose.rHand` / `pose.lHand = [x, y]` (toạ độ gốc, px 1×) tự tính vai + khuỷu; vẫn chỉnh tay bằng `ls/le/rs/re` hoặc xoay trực tiếp các null `shoulder_*`, `elbow_*` trong project (đã thử: đổi `shoulder_R` = -95 trong `style_frames.ecproj` thì tay dang ra, các lớp khác giữ nguyên).

Xoay dương = chiều kim đồng hồ: tay trái (bên trái người xem) dang ra bằng góc dương, tay phải bằng góc âm. **Lưu ý kỹ thuật:** EffectCraft giữ nguyên tư thế thế giới khi gán parent (tự ghi đè xoay/scale cục bộ), nên rig luôn gán parent trước rồi đặt lại xoay=0, scale=100, sau đó mới đặt vị trí. Thư viện: `lib/bi_rig.jsx`.

## 8. Đạo cụ đã có
`phone`, `card` (thông báo), `board` + `bar_n` (biểu đồ cột sinh theo số liệu), `pie` (biểu đồ tròn), `wallet`, `calculator`, `coin`, `jar` (lọ tiết kiệm), `bill` (hóa đơn), `sweat`, `exclaim`, `sparkle`, `shadow`.

## 9. Điểm tôi muốn bạn quyết khi duyệt
1. Nhân vật còn "que" (tay, chân là nét/hình chữ nhật bo): giữ như vậy hay cần dày và nhiều chi tiết hơn (ngón tay, tóc, mũ)?
2. Điện thoại ở khung 01 để màn hình trống: giữ tối giản hay thêm nội dung (danh sách giao dịch)?
3. Chữ Inter đậm có hợp không, hay muốn font bo tròn thân thiện hơn?
4. Nền kem/xanh nhạt luân phiên theo cảm xúc: giữ quy tắc này?

## 10. Tái tạo
```
python phase2\tools\build_style_frames.py
```
Sinh lại asset (SVG → PNG qua VectorCraft), dựng `style_frames.ecproj` trong EffectCraft và render 3 PNG. Khung hình dùng đúng bộ phận có thể đưa vào quy trình animation (cùng cách parent, pivot, đặt tên layer).
