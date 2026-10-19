# Animation Factory – Hướng dẫn

## Chạy
Bấm đúp `run.bat` (hoặc `run.bat --shirt "#2E86DE" --point-speed 0.3`). Cuối cùng in PASS/FAIL các bài kiểm tra
và đường dẫn video. Mất khoảng 30–60 giây.

## Việc cần làm một lần
- Mở `.env`, điền `AI33_API_KEY=...` (không chia sẻ file này). Cần Python 3 và thư viện `requests`.

## Đổi kịch bản
Sửa `project\config.json`: `scene1.text` / `scene2.text` là lời đọc, `caption` là phụ đề hiện trên hình.
Giọng chỉ được tạo lại (tốn credit) khi lời, giọng hoặc tốc độ thay đổi; thêm `--redo-voice` để ép tạo lại.
Chọn giọng khác: `python tools\voice.py voices --provider edge --language Vietnamese`, rồi sửa `voice`.

## Đổi nhân vật
- Màu áo: `--shirt "#RRGGBB"` hoặc `shirt` trong config.
- Hình dáng: sửa `tools\make_assets.py` (các bộ phận: đầu, mặt 3 biểu cảm, thân, chân, tay).
- Chuyển động: `tools\scenes_template.jsx`. Tốc độ chỉ tay: `--point-speed` (giây mỗi lần chuyển, nhỏ hơn là nhanh).

## Đổi thư mục xuất
`--out-dir D:\Videos --name video.mp4` hoặc `outputDir` / `outputName` trong config (các tùy chọn lưu lại cho lần sau).

## Cấu trúc
`tools\` mã chạy · `assets\` SVG/PNG nhân vật · `work\` file trung gian (xóa được, tự dựng lại) · `output\` video.
Mỗi lần chạy dựng lại từ đầu nên không bị trùng layer/clip.

## Ghi chú kỹ thuật
- **Tùy chọn dòng lệnh chỉ áp dụng cho lần chạy đó**, không ghi đè `project\config.json` (cấu hình hiệu lực lưu ở `<work>/run_config.json`). Dùng `--work-dir` và `--out-dir` riêng để thử mà không đụng bản đang dùng.
- **Thời điểm chỉ tay, hiện chữ, đổi biểu cảm** lấy từ mốc thời gian từng từ do API giọng trả về (`sceneN.words.json`), cấu hình bằng `cues` trong config (cụm từ phải có trong lời đọc).
- **Log:** `<output>/logs/run_*.log` ghi từng bước, thời gian, PASS/FAIL; `<work>/api_calls.jsonl` ghi từng lượt gọi API (task_id, số credit, không có key).
- **Chống gửi trùng job tính phí:** lệnh tạo job không bao giờ tự thử lại. Nếu mất kết nối khi đang chờ, task_id lưu ở `*.mp3.task` và lần chạy sau tiếp tục job đó. Chỉ các lệnh GET được thử lại (tối đa 3 lần); chờ job tối đa 600 giây.
- **Endpoint `GET /v1/task/{task_id}` không có trong tài liệu được cung cấp**; đây là endpoint tìm ra bằng thử và đã chạy thành công. Có thể đổi bằng `AI33_TASK_PATH` trong `.env`.
- Project `.ecproj`/`.fcproj` lưu đường dẫn tuyệt đối tới `assets\png` và `work\` – đừng di chuyển thư mục nếu muốn mở lại bằng app.
