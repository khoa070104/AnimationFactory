# Asset Antigravity qua MCP đi vào cảnh (chạy trên bản sao)

- **umbrella_ai** (prop): job `umbrella_ai-90c3537188` state `succeeded`; file `ai_assets/umbrella_ai.png` [202, 600] sha256 `a64120f46a4fdee6…`; tool_evidence=True; hội thoại `0d072075-a640-43e8-929c-48960d37f768`; agent_model `Gemini 3.8 Flash (High)`; image_model `None` (not exposed by agy); tokens 53651; trạng thái gốc `draft`
- **calm_room_ai** (background): job `calm_room_ai-deed835bee` state `succeeded`; file `ai_assets/calm_room_ai.png` [3840, 2160] sha256 `62b1f914a9df158f…`; tool_evidence=True; hội thoại `f55d998e-97bf-4fb0-8d6d-9a893b5f5a88`; agent_model `Gemini 3.8 Flash (High)`; image_model `None` (not exposed by agy); tokens 43950; trạng thái gốc `draft`

- Dữ liệu cảnh `s01` đổi: `bg: ai:calm_room_ai` + prop `ai:umbrella_ai` (không sửa code). Validator: `0 error(s), 0 warning(s)`
- Dựng: render ['s01', 's02', 's03', 's04', 's04b', 's05', 's06', 's07', 's08'], tái sử dụng 0 cảnh; mã thoát 0
- Dựng lại không đổi: render không cảnh nào
- Sau khi loại `umbrella_ai`, validator: `["ERROR   s01: AI asset 'umbrella_ai' is 'rejected'; only approved assets can be used in scenes"]`

Khung hình đã dựng của cảnh (xem `mcp_scene_frame.png`); ảnh gốc phông: `mcp_scene_background_source.jpg`.
