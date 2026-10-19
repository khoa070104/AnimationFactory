# AnimationFactory — hướng dẫn nhanh cho AI điều khiển (CLI/MCP), contract `af/1`

Bạn là đạo diễn; AnimationFactory là bàn dựng. Mọi lệnh dưới đây trả **một tài liệu JSON trên stdout** (log ở stderr). Lỗi có `code`, `scene_id`, `shot_id`, `field`, `message`, `next_action`. **Không có lệnh duyệt**: chỉ chủ dự án duyệt; tool không bao giờ tự duyệt hay tự tiêu tiền.

## Chạy
```
python D:/AnimationFactory/phase2/tools/af.py capabilities [--project NAME]   # catalog có phiên bản; KÈM --project thì liệt kê nhân vật + ảnh AI đã duyệt của dự án đó (không kèm: chỉ Bi có sẵn)
python .../af.py project_get   --project NAME [--what summary|storyboard|status|all]    # trả cả `hash`
python .../af.py project_put   --project NAME --storyboard-file F.json --expect-hash H [--autolayout]
python .../af.py validate      --project NAME [--storyboard-file F.json]
python .../af.py estimate      --project NAME                              # ký tự, giây, credit, ngân sách. Không phải quyền duyệt
python .../af.py preview       --project NAME [--scenes s01,s02] [--background]   # MIỄN PHÍ: ảnh mỗi shot, contact sheet, clip nhẹ, QA
python .../af.py render        --project NAME [--draft] [--background]     # dừng ở cổng duyệt: status waiting_approval
python .../af.py jobs          --project NAME [--job-id ID]                # running | succeeded | failed | waiting_approval | interrupted
python .../af.py artifacts     --project NAME
```
Mã thoát: 0 ok, 2 needs_changes/waiting_approval/running, 1 error. stdout là UTF-8 (tiếng Việt không bị escape): đọc bằng utf-8 (Windows: `PYTHONUTF8=1`). `project_get --what status|all` đưa trạng thái dự án trong khóa `project_status`. Cùng các lệnh có trong MCP (`.mcp.json`, server `animation-factory-assets`; Claude CLI cần bạn duyệt server một lần).

## Vòng làm việc
`capabilities` → `project_get` (lấy `hash`) → sửa storyboard → `validate` / `project_put --expect-hash` → `preview` → **mở contact sheet và các ảnh mốc (bạn xem được ảnh bằng công cụ đọc ảnh)** → sửa theo lỗi chỉ đúng cảnh/shot/trường → `preview` lại (chỉ cảnh đổi được dựng lại) → `render` → chủ dự án duyệt.
Nếu môi trường của bạn không đọc được ảnh/video/âm thanh, ghi "chưa kiểm tra" — đừng tự kết luận đã xem/nghe.

## Shot (cấp dưới scene; chỉ bộ dựng Remotion)
`scene.shots = [{id, start (giây | cụm lời), kind, size, focus, gaze, cut, ease, end, purpose}]` — không có `shots` = một khung rộng.
- `kind`: wide, action, reaction, prop, compare, graphic. `size`: wide, medium, close, detail.
- `focus`: `main` | `cast1`.. | `item:<chỉ số trong scene.items>` | `item:<tên ảnh của prop>` hoặc `item:<type của item>` (ví dụ `item:notice`, `item:grid`) | `[x,y,w,h]`. Khung tự lấy theo kích thước đối tượng (nhân vật cao hơn → lùi xa hơn), có đệm, trong canvas, trên dải phụ đề, zoom tối đa 2,2.
- `start` tăng dần; shot kéo dài tới shot sau; `end` sớm hơn shot sau = khoảng trống (về toàn cảnh); `end` muộn hơn = chồng lấn → lỗi `SHOT_OVERLAP`.
- Đổi shot **không chạy lại động tác**: nhân vật/đạo cụ giữ trạng thái, camera chỉ là hàm của thời gian.
- `gaze: [{who, at}]`: `at` = `cast1` | `main` | `item:..` | `left` | `right` | `[x,y]` (nhân vật quay mặt theo đích tại đầu shot).
- Lớp: phụ đề luôn cố định; mọi item mặc định đi theo camera (`space:"world"`), đặt `space:"screen"` để cố định; `until` (giây | cụm lời) cho item rời màn hình.

## Thành phần đồ họa (đổi dữ liệu, không đổi mã)
`grid` (bảng/danh sách, `cols:1` = một dòng mỗi hàng, số ô phải khớp lời "bảy ngày"…), `compare` (hai cột theo tỷ lệ giá trị), `highlight` (khung nét đứt), `chart`, `legend`, `pills`, `notice`, `bill`, `pie`, `text`, `prop` (thư viện hoặc `ai:<id>` đã duyệt).

## Dự án, cache, chi phí, duyệt
- `project_put` cần `expect_hash` (so sánh-rồi-ghi): hash cũ → `STALE_HASH`, đọc lại rồi gộp. Bản trước được giữ trong `versions/`.
- Chạy lại cùng yêu cầu đang chạy trả **cùng job**; không gọi provider thêm. Cache theo cảnh: chỉ cảnh có dữ liệu/ảnh/rig/font/audio/code thay đổi được dựng lại.
- `preview` và `render --draft` dùng giọng nháp im lặng: **0 ảnh, 0 giọng, 0 LLM**. `render` thật cần duyệt của chủ dự án và nằm trong ngân sách dự án; kết quả có `usage_delta`/`paid_calls_this_run`.
- Ảnh AI do Antigravity sinh qua MCP assets (`submit_asset_job`); ảnh mới là bản nháp, chỉ dùng được sau khi chủ dự án duyệt.

## Ví dụ
`phase2/examples/story_label.json` (kể chuyện: rộng → cận nhãn → phản ứng → phản ứng → rộng) và `phase2/examples/explain_process.json` (giải thích: người dẫn + danh sách bước + so sánh hai cách). Dựng bằng `python ops/chang1_demos.py story|explain` (chỉ dùng lớp điều khiển; ngân sách 0).

## Giới hạn đã biết
Camera 2D chỉ tạo cận/pan/zoom, không tạo góc quay mới. Chưa có: mở cửa, đặt vật lên bàn, ngồi (Chặng 2). Nhạc nền/SFX (Chặng 3). Giọng/âm thanh phải có người nghe xác nhận.
