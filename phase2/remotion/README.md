# Remotion renderer (phase2/remotion)

Bộ dựng thay thế cho đường Craft. Chọn bằng `produce.py --renderer remotion` hoặc `"renderer": "remotion"` trong brief; mặc định vẫn là Craft.
Mọi thứ quyết định *cái gì xảy ra* (storyboard, cue, bố cục, bảng, holds, giọng, duyệt, ngân sách) dùng lại tool hiện có; Remotion chỉ vẽ.

## Lệnh
```bash
python phase2/tools/produce.py PROJECT --renderer remotion            # sản xuất (cần nhân vật đã duyệt + giọng thật)
python phase2/tools/produce.py PROJECT --renderer remotion --draft    # bản nháp, giọng nháp im lặng, nhân vật nháp được phép
python phase2/tools/build_remotion.py PROJECT [--draft] [--force]     # chỉ bước dựng
python phase2/tools/export_remotion.py PROJECT WORKDIR --scenes s03   # chỉ xuất dữ liệu
cd phase2/remotion && npx remotion studio src/index.ts --public-dir=PROJECT/remotion/public    # xem trước / sửa trong Studio
node --test phase2/remotion/tests/sig.test.mjs                                      # test chữ ký cache
```
Project chỉnh sửa được = `PROJECT/remotion/public` (clip.json = dữ liệu cảnh, assets, rigs, audio) + source `phase2/remotion/src`. `PROJECT/remotion/out/scenes/*.mp4` là clip từng cảnh.

## Không có vật thay thế âm thầm
- Mỗi nhân vật AI phải có rig dựng từ ảnh của chính nó; dựng chính thức cần "approved". Nhân vật không có rig → từ chối. Dùng rig của dự án khác chỉ với `--placeholder ID=RIG@PROJECT`, bản dựng bị đánh dấu nháp và ghi vào `clip.json`.
- Asset AI (nền, đạo cụ, đạo cụ cầm tay) phải được duyệt; không có thì lỗi, không thay bằng ảnh thư viện.
- Giọng: cần giọng thật còn mới (hoặc `--draft`). Bước này không bao giờ gọi API trả phí.

## Dựng lại tăng dần (`sig.mjs`)
Mỗi cảnh có chữ ký gồm: dữ liệu cảnh, rig + ảnh của MỌI nhân vật trong cảnh, mọi ảnh cảnh dùng (và kích thước), font, audio, fps/kích thước/png scale/màu, code renderer và thư viện chuyển động. Đổi thứ không dùng trong cảnh thì không dựng lại cảnh đó. Có test (`tests/sig.test.mjs`).

## QA
Cùng báo cáo như Craft (`logs/build_report.json`): video 1920x1080 có audio, tiêu chí khóa trước, thời lượng, số cảnh, phụ đề, độ trễ cue ≤ ngưỡng, và `check_motion.row_checks` trên chính các giá trị khớp mà renderer vẽ (giới hạn khớp, không giật/lật, tay không xuyên thân).
Khóa key ở lưới khung hình (như EffectCraft) để hai bộ dựng thấy cùng đường cong.

## Cài đặt
npm (nguồn chính thức), trong dự án: remotion/@remotion/cli/@remotion/player 4.0.536, react/react-dom 19.3.1, typescript 7.0.2. Node ≥ 22, ffmpeg trên PATH. Lần render đầu tải Chrome Headless Shell vào `node_modules/.remotion`.
Giấy phép Remotion: miễn phí cá nhân / công ty ≤ 3 người; từ 4 người cần Company License.
`_spike/` là bản thử 3 cảnh ban đầu (có dùng rig Gate 1 làm placeholder) để đối chiếu.
