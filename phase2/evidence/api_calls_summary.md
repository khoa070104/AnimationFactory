# Số lần gọi API và chi phí (theo log từng dự án)

| Dự án | Lượt gọi API giọng | Credit thực tế (giọng + mốc từ) | Ghi chú |
|---|---|---|---|
| video1_luong | 9 (831 ký tự) | 593 | 9 cảnh, lần đầu |
| video2_quy_khan_cap | 9 (913 ký tự) | 653 | 8 cảnh + 1 cảnh s04b thêm sau (70 credit); mọi lần chạy lại: 0 lượt |
| ui_demo | 0 (0 ký tự) | 0 | 3 câu dùng lại từ kho giọng dùng chung (CACHE-HIT), không gọi API |

Asset AI (Antigravity): 3 asset tạo thật qua CLI/MCP (piggy_ai, umbrella_ai, calm_room_ai); agy chỉ báo token (≈44–80 nghìn/ảnh), không có số tiền/credit; model của bộ tạo ảnh không được agy công bố (`image_model: null`), model của agent chính đọc từ log: Gemini 3.8 Flash (High).

Gọi thử trong lúc phát triển (chưa có log theo dự án, ước ≈ 6 job ngắn Phase 1) không nằm trong bảng.
