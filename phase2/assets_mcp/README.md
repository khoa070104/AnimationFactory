# MCP cục bộ: tạo asset bằng Antigravity (animation-factory-assets)

Máy chủ MCP qua stdio, hai công cụ, dùng `agy` (Antigravity CLI) làm bộ tạo ảnh. Logic nằm ở `tools/agy_jobs.py` và `tools/agy_image.py`
(dùng chung với dòng lệnh); `af_assets_server.py` chỉ chuyển đổi giao thức.

## Đăng ký (tự thêm vào cấu hình MCP của bạn)
```json
{"mcpServers": {"animation-factory-assets": {"command": "python", "args": ["D:/AnimationFactory/phase2/assets_mcp/af_assets_server.py"]}}}
```
Yêu cầu: `agy` đã cài và đăng nhập (`%LOCALAPPDATA%\agy\bin\agy.exe`, hoặc đặt biến `AGY_CMD` là mảng JSON lệnh khác).

## Công cụ
**`submit_asset_job`** — `project`, `asset_id`, `kind` (`prop` | `character` | `background`), `prompt`; tùy chọn `reference_images` (≤4 đường dẫn ảnh),
`transparent_background`, `display_width`, `regenerate`, `timeout_seconds` (30–900). Trả `job_id` ngay (`<asset_id>-<10 hex của chữ ký yêu cầu>`).
**`check_asset_job`** — `project`, `job_id`. Trạng thái: `queued`, `running`, `succeeded`, `failed`, `timeout`, `interrupted`.
Khi `succeeded`: `result` (file tương đối trong dự án, `sha256`, `tool_evidence`, `conversation_id`, `agent_model`, `usage`, `status`), `scene_item`, `use_in_scene`.

## Quy tắc đảm bảo
- **Bằng chứng đã gọi công cụ tạo ảnh:** log `stream-json` phải có sub-agent `image-generator` (hoặc `generate_image`); ảnh vẽ bằng code hoặc không có ảnh = lỗi, không thành asset.
- **File đúng job:** lấy từ bản ghi hội thoại của sub-agent của job đó (`log_uri`) và câu trả lời của chính lần chạy đó, và phải nằm trong `brain/<mã hội thoại của job>/`. Không có bước "ảnh mới nhất trên máy".
- **Thư mục dự án:** `projects/<project>/ai_assets/<asset_id>.png` (PNG gấp đôi kích thước hiển thị; prop/character tách nền trắng thành trong suốt; background cắt 16:9, không trong suốt) + `source/` (ảnh gốc) + `logs/`.
- **Manifest** (`ai_assets/manifest.json`): prompt, prompt đầy đủ, ảnh tham chiếu (sha256), mã băm file kết quả và ảnh gốc, `conversation_id`, nhãn model của agent đọc từ log (`image_model` luôn `null`: agy không công bố model của bộ tạo ảnh), số token, các lần thử, trạng thái duyệt.
- **Yêu cầu không đổi → dùng kết quả đã lưu**, không gọi agy (kể cả gửi lại khi job đang chạy: cùng một job).
- **Lỗi/timeout báo rõ, không lặp:** tối đa 2 lần thử mỗi lượt chạy (hết thời gian thì **không** thử lại), cùng yêu cầu thất bại 2 lần thì bị chặn cho đến khi `regenerate=true`. Job đang dở khi máy chủ dừng được đánh dấu `interrupted`, không tự chạy lại.
- **Một lượt agy tại một thời điểm** (hàng đợi tuần tự). Chế độ không giao diện không hỏi quyền: prompt cấm lệnh shell; không dùng `--dangerously-skip-permissions`.
- **Duyệt không phải công cụ MCP:** asset mới là `draft`; chủ dự án duyệt bằng `python phase2/tools/agy_image.py <project> approve <id> --by "tên"`. Cảnh chỉ dùng được asset đã duyệt.

## Toàn vẹn job / asset (vòng sửa lỗi 3)
- **Job gắn với dự án:** hàng đợi và `_inflight` khóa theo (đường dẫn dự án, job_id); cùng yêu cầu ở hai dự án là hai job độc lập.
- **Kết quả theo từng job:** bản ghi job lưu `snapshot` của chính nó; ảnh mỗi yêu cầu được giữ ở `ai_assets/versions/<asset>-<chữ ký>.png`. Nếu yêu cầu mới hơn thay asset, `check_asset_job` của job cũ trả `state: superseded` và kết quả của chính nó, không bao giờ trả ảnh của yêu cầu sau.
- **Cache kiểm tra file:** trả kết quả đã lưu chỉ khi file PNG còn và đúng sha256; nếu mất/hỏng thì báo lỗi rõ (`submit` báo lỗi, `check` trả `state: invalid`), không tự gọi agy; chỉ `regenerate=true` mới tạo lại.
- **Duyệt gắn với hash ảnh:** lúc duyệt ghi `approved_sha256`; bộ dựng và validator chỉ nhận `ai:<id>` khi file trên đĩa còn đúng hash đó (nếu không: `changed_after_approval`). Bản ghi duyệt cũ chưa có `approved_sha256` dùng hash trong manifest. Ảnh tạo lại luôn là `draft`.
- **Ghi nguyên tử + khóa:** file trạng thái job và manifest ghi qua file tạm + `os.replace`, đọc có thử lại; sửa manifest dùng khóa liên tiến trình và chỉ thay đúng mục của asset (không ghi đè duyệt của asset khác).

## Nhiều tiến trình dùng chung dự án (UI + MCP + CLI)
- Mỗi job `queued/running` ghi **chủ sở hữu** (`owner`: pid + dấu thời điểm tạo tiến trình, nên pid bị tái sử dụng không bị nhầm là chủ).
- Tiến trình khác `check`: job có chủ còn sống vẫn là `running`, không bị đổi sang `interrupted`. Chỉ job mà chủ đã mất mới thành `interrupted`.
- Tiến trình khác `submit` lại cùng yêu cầu khi job còn chạy: trả đúng job đó (kèm ghi chú "owned by process N"), `run` không tăng, không gọi agy.
- Quyết định gửi/ngắt chạy dưới khóa tệp theo dự án (`ai_assets/.jobs.lock`), nên hai tiến trình gửi cùng lúc chỉ có một tiến trình chạy.
- Giới hạn: hai tiến trình khác nhau có thể chạy agy **song song** cho các yêu cầu khác nhau (hàng đợi tuần tự chỉ trong từng tiến trình).

## Đưa vào bộ dựng qua dữ liệu cảnh (không sửa code từng video)
```json
{"type": "prop", "img": "ai:umbrella_ai", "x": 1000, "y": 760, "scale": 0.9, "appear": "cuối tháng"}
{"id": "s01", "bg": "ai:calm_room_ai", ...}
```
`validate_storyboard.py` và bộ dựng từ chối asset chưa duyệt/không tồn tại/bị loại. Sao chép vào `assets/` của dự án và chữ ký dựng lại chỉ phụ thuộc đúng ảnh cảnh đó dùng.

## Giới hạn đã biết
Mỗi job mất khoảng 1–2,5 phút và ~80 nghìn token của agy; chất lượng/phong cách chưa đảm bảo (luôn là bản nháp chờ duyệt); `character` mới chỉ là ảnh, chưa tách bộ phận/gắn khớp để chuyển động như Bi.
Kiểm thử: `tests/test_agy_image.py`, `tests/test_mcp_assets.py` (đầu-cuối qua stdio với `tests/fake_agy.py`), `tests/test_ai_refs.py`; kiểm tra thật: `ops/mcp_real_e2e.py`.
