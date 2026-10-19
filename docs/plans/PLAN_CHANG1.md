# Kế hoạch Chặng 1 — hợp đồng điều khiển, shot, camera, bố cục (bản chuẩn bị, 20/10/2026)

Chưa sửa mã nào cho bản giao việc v1. Tài liệu này là kế hoạch + yêu cầu cần bạn quyết/cung cấp. Giữ nguyên: Remotion làm bộ dựng chính, Craft làm dự phòng, dự án/asset/giọng/cache/duyệt/ngân sách hiện có, không xây lại web, không thêm dịch vụ điều phối.

## 1. Bảng năng lực hiện có (từ những gì tôi đã chạy; "chưa chứng minh" nghĩa là cần subagent R1/R2 đối chiếu mã)
| Năng lực | Hiện có? | Bằng chứng | Phần thiếu cho Chặng 1 |
|---|---|---|---|
| Storyboard cấp scene (nền, nhân vật, hành động, cue, đồ họa, holds) | Có | storyboard v17 chạy, 153 test | Không có cấp **shot**: chưa có mục đích hình, đối tượng trọng tâm, cỡ cảnh, hướng nhìn |
| Camera | **Chỉ Craft**, 1 preset/scene (push_in, pull_out, pan) | `sbload.resolve_camera`, `scene_anim.jsx` | Remotion **chưa có camera**; chưa có cận theo đối tượng, nhiều shot trong 1 scene |
| Tách lớp thế giới / giao diện | Chưa | `Clip.tsx`: phụ đề và panel vẽ cùng lớp với cảnh | Phụ đề/panel cố định khi camera chạy |
| Bố cục | Có (`layout.compose/nudge`, khung nội dung) | test_layout, v17 | Bố cục theo kiểu shot (cận, so sánh), chiều sâu, lớp che |
| Nhân vật AI + rig + cầm đồ | Có (cầm/viết/xách, cheer một tay) | Sample A | Pose ngồi/với/chạm; điểm tiếp xúc; trạng thái vật (Chặng 2) |
| Đồ họa dữ liệu | Có grid, chart (cố định kích thước), legend, pills | Sample A | So sánh hai phía, đường/biểu đồ vẽ dần, nhấn vùng (một nhóm nhỏ tham số hóa) |
| Cue theo audio thật | Có (words.json) | v17 | Khoảng nghỉ/nhấn cấu hình; kiểm tra nghe |
| Âm thanh nhiều lớp | Chỉ giọng | — | Nhạc nền/ambience/SFX chưa có |
| CLI | Có rời rạc (produce, prepare, approve, build_*, capabilities) | `capabilities` in JSON | Không có hợp đồng thống nhất: stdout JSON sạch, mã lỗi theo vị trí, job id |
| MCP | Chỉ **assets** (submit/check job) | `assets_mcp/af_assets_server.py`; `claude mcp list`: **Pending approval** | Adapter cho validate/preview/render/jobs/review; cần bạn duyệt |
| Phiên bản/khóa dự án | Có (versions/, approvals, agy slots) | tests | Kiểm tra khóa khi nhiều CLI cùng ghi |
| Ảnh mốc / clip preview | Một phần (frame còn thủ công) | — | Lệnh preview trả contact sheet + clip thấp độ phân giải |
| Kiểm nghe | Chưa | — | Chỉ ASR (faster-whisper, có sẵn) kiểm chữ/cắt cuối; "nghe tự nhiên" cần người |
| Kiểm soát phiên bản mã | **Không có git** | không có `.git` | Không rollback sạch, không worktree song song |

## 2. Các bước thực thi (một người ghi mã, tuần tự — các file lõi dùng chung)
1. **Hợp nhất bảng năng lực** từ R1/R2 + quyết định thiết kế ngắn (schema shot, quy ước lớp world/screen, danh sách cỡ cảnh).
2. **Shot schema** tương thích ngược (scene không có `shots` = 1 shot ngầm định): `purpose`, `focus` (nhân vật/đạo cụ/vùng/biểu đồ), `kind` (rộng, hành động, phản ứng, cận vật, so sánh, đồ họa), `size`, `gaze`, `camera` (target + zoom + ease), `cues`. Validator trả lỗi theo `shot_id/field`; capabilities công bố phiên bản schema.
3. **Remotion**: lớp world (nền+nhân vật+vật) có camera theo target và chuyển giữa shot; lớp screen (phụ đề, nhãn cần cố định) không bị camera kéo; kiểm tra không lộ ngoài nền; không phóng ảnh để giả góc quay mới.
4. **Đồ họa theo dữ liệu**: thêm so sánh hai phía + đường/thanh vẽ dần + nhấn vùng (tham số hóa), tái dùng grid; chữ luôn từ dữ liệu.
5. **Lớp điều khiển mỏng `af`** (một lõi, hai cửa): CLI `af capabilities|project|validate|estimate|preview|render|jobs|artifacts|review --json` và adapter MCP gọi chung; stdout JSON sạch, log ra stderr; lỗi có mã + vị trí + `next_action`; job id, chạy lại không gọi provider thêm; `charged_calls`/`paid_calls_this_run` đúng. Bọc `produce.py`, `capabilities.py`, MCP assets sẵn có.
6. **Preview**: ảnh mốc theo sự kiện (trước/lúc/sau) + contact sheet + clip thấp độ phân giải, đường dẫn trong `artifacts`.
7. **Hai đoạn thử 15–25 s dữ liệu khác nhau** bằng thành phần dùng chung, không nhánh theo project/scene ID: (A) kể chuyện hai nhân vật: bối cảnh → chi tiết quan trọng → phản ứng, dùng asset Sample A đã có (bếp, Tuấn, Linh, túi, tủ lạnh); (B) giải thích một quy trình giả định 3 bước + so sánh hai cách, dữ liệu minh họa ghi rõ, không cần asset mới.
8. **Trước/sau cùng đầu vào**, đổi thứ tự/độ dài nhãn/vị trí bằng dữ liệu, ảnh mốc + clip; bảng 9 tiêu chí (Đạt/Cần sửa/Chưa kiểm chứng + timestamp).
9. **Nghiệm thu độc lập (9.7)**: đóng phiên xây, phiên mới chỉ có tài liệu + brief + đường dẫn dự án phải tự tạo/validate/preview/sửa/render. CLI thứ hai (xem mục 4).
Điều kiện dừng: lỗi thiết kế cần bạn quyết (ví dụ cần góc quay mới → cần asset đúng góc, thuộc Chặng 2).

## 3. Subagent song song để nghiên cứu (chỉ đọc) — đề xuất **4**, rồi 1 phiên độc lập ở cuối
| # | Việc | Vì sao tách | Đầu ra |
|---|---|---|---|
| R1 | Kiểm toán năng lực storyboard/layout/camera/rig/Remotion (đối chiếu với bảng mục 1, chạy thử) | Đọc nhiều file; kết luận gọn | Bảng có/chưa/chưa chứng minh + bằng chứng file:dòng |
| R2 | Kiểm toán hợp đồng CLI/MCP: stdout/exit code từng lệnh, jobs, khóa đồng thời, MCP assets, endpoint UI | Độc lập với R1 | Danh sách lệnh cần bọc, chỗ log lẫn stdout, rủi ro ghi đè |
| R3 | Phân tích hai video tham chiếu: danh sách shot theo timestamp (cỡ cảnh, mục đích, chuyển chú ý) | Cần xem hàng trăm khung | Bảng shot + mẫu biểu diễn ý trừu tượng (**cần file video**) |
| R4 | Nghiên cứu Remotion: camera/zoom có lớp cố định, mask/che, trộn nhiều track audio, Studio/Player, giới hạn render | Cần tra tài liệu web | Ghi chú khả thi + đoạn mã mẫu tối thiểu |
Không thêm agent ghi mã song song: không có git nên không cô lập được, và shot schema/Clip.tsx/layout là file dùng chung dễ ghi đè. Cuối Chặng 1 thêm **1 agent độc lập** (không nhận kết luận của tôi) cho nghiệm thu 9.7, và tùy chọn 1 agent review mã. Tổng 4 + 1 (+1).

## 4. Điều tôi cần từ bạn / còn thiếu
1. **Hai video tham chiếu**: không thấy file trên máy (đã tìm theo tên). Cho đường dẫn (hoặc xác nhận chỉ dùng mô tả trong bản giao việc → R3 bỏ).
2. **Duyệt MCP `animation-factory-assets`**: đang "Pending approval" trong Claude CLI; chỉ bạn duyệt được (chạy `claude`, chọn duyệt).
3. **CLI thứ hai để thử 9.7**: máy **không có Codex CLI**; có `gemini` và `agy`. Chọn dùng cái nào (cần đã đăng nhập), hoặc ghi "chưa kiểm chứng với CLI thứ hai".
4. **Nghe giọng**: tôi không nghe được. Có faster-whisper (đã có model) để kiểm chữ/cắt từ cuối/khoảng nghỉ; "tự nhiên/cảm xúc" cần bạn nghe. Xác nhận cách này.
5. **Nhạc nền / hiệu ứng**: tool chưa có; tôi không có nguồn âm thanh được phép dùng. Cho thư mục nhạc/SFX có bản quyền, hoặc cho phép chỉ làm khoảng lặng + SFX tổng hợp đơn giản (ffmpeg). Không thuộc Chặng 1 nhưng ảnh hưởng thiết kế lớp audio.
6. **`git init` cho `D:\AnimationFactory`** (cục bộ, không đẩy đi đâu): để rollback và cho phép worktree cô lập khi cần song song. Có đồng ý?
7. **Ngân sách trả phí**: Chặng 1 cần **0 credit và 0 ảnh mới** (dùng lại asset Sample A, đoạn B không cần asset). Chặng 2/3 sẽ xin riêng.
8. **Sample A còn treo**: video 92,6 s vượt tiêu chí đã khóa 60–90 s. Chọn: chấp nhận và ghi quyết định (nới lên 95 s), hoặc rút lời + tạo lại giọng (tốn credit). Tôi không tự nới.
9. **Giấy phép Remotion**: cần xác nhận quy mô công ty (≤ 3 người miễn phí; từ 4 người cần Company License).
10. **Cho phép dùng subagent** theo mục 3 (tốn token song song).

## 5. Rủi ro đã biết
- Camera 2D chỉ tạo cận/pan/zoom; đổi góc thật cần asset đúng góc (Chặng 2).
- Chữ trong thế giới (nhãn trên bàn) và chữ màn hình phải phân biệt rõ, nếu không camera đẩy chữ ra khỏi khung.
- Ảnh hưởng ngược: thay đổi Remotion không được làm hỏng đường Craft (giữ test); mọi thay đổi shot tương thích ngược.
- Đánh giá thẩm mỹ cuối cùng phải là người xem; test chỉ chặn lỗi cụ thể.
