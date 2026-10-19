# Nghiệm thu Chặng 1 — hợp đồng điều khiển, shot, camera, bố cục (20/10/2026)

Phạm vi theo bản duyệt: 0 ảnh mới, 0 lượt TTS trả phí (xác nhận bằng `usage_delta` = 0 trong mọi lần preview/dựng của chặng này). Token của AI/subagent là khoản riêng. Mã đã commit local (git, tag gốc `chang0-baseline`).

## 1. Đã làm (thật / chưa)
| Hạng mục | Kết quả |
|---|---|
| Bảng năng lực + quyết định thiết kế | `CHANG1_BANG_NANG_LUC.md` (3 subagent đọc mã; R3 video tham chiếu không chạy: chưa có file) |
| Shot có thời gian, giữ trạng thái | `tools/shots.py`, tương thích ngược; lỗi có mã/shot/trường; chồng lấn bị từ chối; `end` sớm = khoảng trống có chủ đích |
| Camera Remotion đóng khung theo kích thước đối tượng | `shots.frame` (hộp bao từ rig height×scale, đệm, trong canvas, trên dải phụ đề, zoom ≤ 2,2); camera là hàm thuần của thời gian → đổi shot không chạy lại động tác |
| Lớp theo vai trò | phụ đề cố định; item `space: world|screen`; `until` cho item rời màn hình; **cô lập tiêu điểm**: ở shot cận, nội dung/nhân vật không phải trọng tâm mà lấn vào khung bị mờ đi (phát hiện nhờ phiên nghiệm thu độc lập) |
| Thành phần đồ họa theo dữ liệu | `compare` (hai cột theo tỷ lệ), `highlight`, `grid` đủ ô theo lời; chữ vẽ từ dữ liệu |
| Lớp điều khiển một lõi, hai cửa | `tools/af_core.py` + CLI `tools/af.py` + adapter MCP (cùng server assets); stdout JSON, mã lỗi, `expect_hash`, job + heartbeat, `paid_calls_this_run`; **không có lệnh duyệt** |
| Preview | ảnh mỗi shot (kèm `shot`, thời điểm), contact sheet, clip nhẹ, QA; chỉ dựng lại cảnh đổi |
| Tài liệu cho phiên mới | `HUONG_DAN_AF.md`, 2 ví dụ `examples/story_label.json`, `examples/explain_process.json` |
| Test | 166 test Python (gồm các test chạy node) + 22 test node đạt (`evidence/tests_log.txt`) |

## 2. Hai đoạn thử (cùng thành phần, không nhánh theo project/scene)
- **Kể chuyện** `demo_chang1_story` (17,0 s): rộng → cận nhãn → phản ứng Linh → phản ứng Tuấn → rộng; Tuấn xách túi, nhìn nhau (gaze).
- **Giải thích** `demo_chang1_explain` (16,8 s, 2 cảnh): người dẫn + danh sách 3 bước (cận) + so sánh hai cột (cận) + chốt (cận người dẫn). Số liệu ghi "minh họa" trên màn hình.
- Trước/sau cùng đầu vào: `evidence/chang1/before_after_story.jpg`, `before_after_explain.jpg`. Preview: `evidence/chang1/contact_*.jpg`. Clip: `projects/demo_chang1_*/output/*_draft.mp4` (giọng nháp im lặng).

## 3. Nghiệm thu bằng dữ liệu (đều có test tự động)
| Phép thử | Kết quả |
|---|---|
| Đổi mục tiêu camera (focus sang vùng khác) | dựng lại đúng cảnh đổi, camera khác (`test_changing_the_camera_target…`) |
| Nhãn dài hơn | cảnh báo "…px wide but the content panel is …": rút ngắn rồi hết cảnh báo |
| Asset không tồn tại / cụm lời sai / focus không có | `MISSING_ASSET`, `CUE_NOT_IN_VOICE`, `UNKNOWN_FOCUS` kèm cảnh/shot/trường/`next_action`; ghi bị từ chối không đổi gì |
| Hash cũ | `STALE_HASH`, không ghi đè |
| Sửa dữ liệu rồi dựng được, không sửa mã theo mẫu | có |

## 4. Nghiệm thu độc lập (9.7) — giới hạn nói thẳng
- Đã chạy **một subagent mới** (không kế thừa lịch sử), chỉ nhận `HUONG_DAN_AF.md`, brief và đường dẫn dự án `demo_chang1_accept` (bản nháp có 4 lỗi cài sẵn: cụm lời sai, focus không tồn tại, asset không tồn tại, và một lỗi chỉ thấy bằng mắt: cận sai nhân vật).
- Nó tự: đọc tài liệu → validate (3 lỗi có mã) → sửa → `project_put` → preview → xem ảnh → còn tự phát hiện cận sai nhân vật. **Không sửa mã.** 7 lệnh `af.py`, 0 chi phí.
- Nó cũng nêu các điểm tài liệu/tool chưa tốt; đã sửa: `project_get --what all` làm hỏng mã thoát (khóa `status` bị ghi đè), ảnh preview không ghi thời điểm, doc chưa nói `item:<type>`, `capabilities` cần `--project` để thấy nhân vật; và khung cận bị lấn bởi thẻ nhãn (đã thêm cô lập tiêu điểm).
- **CHƯA kiểm chứng với CLI thứ hai.** Gemini CLI báo "account requires setting GOOGLE_CLOUD_PROJECT" (cần cấu hình tài khoản của bạn); `claude -p` chạy tiến trình con báo "Not logged in"; `agy` không chạy được lệnh shell nếu không bật cờ bỏ qua quyền (cấm). Subagent không phải một CLI khác và có thể đã dùng cùng họ mô hình.
- MCP: server `animation-factory-assets` vẫn "Pending approval" trong Claude CLI (chỉ bạn duyệt được); adapter đã được thử qua giao thức JSON-RPC trực tiếp (`test_mcp_adapter_serves_the_same_core`), chưa thử qua một CLI thật.

## 5. Bảng 9 tiêu chí (Đạt / Cần sửa / Chưa kiểm chứng)
| # | Tiêu chí | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Ý nghĩa hình | **Đạt** cho 2 đoạn thử | story: mỗi shot có `purpose`; cận nhãn đúng lúc nhãn được đọc |
| 2 | Điểm tập trung | **Đạt** | cận nhãn / cận từng người; cô lập tiêu điểm bỏ vật lấn vào khung |
| 3 | Camera | **Đạt, có hạn chế** | phụ đề cố định (test điểm ảnh); không lộ ngoài nền; zoom ≤ 2,2 nên ảnh raster mềm hơn ở cận cao nhất (chưa xem ở màn hình lớn) |
| 4 | Nhân vật | **Cần sửa** | giữ nhận diện, nhìn theo đích; nhưng pose vẫn chủ yếu đứng, miệng không mấp máy (Chặng 2) |
| 5 | Tương tác | **Cần sửa** | cầm túi/giỏ ổn; chưa có đặt vật lên bàn, ngồi, mở cửa (Chặng 2) |
| 6 | Mỹ thuật | **Chưa kiểm chứng** | nền/nhân vật Antigravity thống nhất trong dự án; đánh giá thẩm mỹ cuối là của bạn |
| 7 | Đồ họa | **Đạt** | số ô khớp lời, chữ từ dữ liệu, `compare` tỷ lệ đúng; số liệu minh họa ghi rõ |
| 8 | Nhịp và tiếng | **Chưa kiểm chứng** | chỉ giọng nháp im lặng; không có kiểm nghe |
| 9 | Tái sử dụng | **Đạt** | 2 đoạn khác nhau cùng mã; đổi dữ liệu dựng đúng phần; cache đủ đầu vào (16 test chữ ký) |

## 6. Việc cần bạn
1. Xem hai clip và các contact sheet ở mục 2, ghi nhận xét mục 4, 6 (nhân vật, mỹ thuật).
2. Duyệt MCP `animation-factory-assets` trong Claude CLI nếu muốn nghiệm thu qua MCP; cấu hình `GOOGLE_CLOUD_PROJECT` cho Gemini CLI (hoặc cho tôi cách khác) nếu muốn thử CLI thứ hai. Tôi có thể đưa bạn một lệnh `claude` tương tác kèm brief để bạn tự chạy.
3. Quyết có sang Chặng 2 (asset phục vụ hành động: ngồi, cầm/đặt, che khuất) không.
