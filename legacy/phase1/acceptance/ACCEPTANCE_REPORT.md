# Phase 1 – Báo cáo nghiệm thu (bản bổ sung bằng chứng)
Trạng thái: **Hoàn thành bản thử kỹ thuật – chờ bạn duyệt cảm quan (xem/nghe) và chạy launcher một lần bằng tay.**

| # | Tiêu chí | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Kết nối 3 app qua CLI | Đạt (qua CLI headless; **chưa dùng MCP**) | `logs/run_*.log`; mỗi app được gọi trong 1 bước log |
| 2 | API giọng nói trả audio thật | Đạt kỹ thuật | `work1/audio/*.mp3`, `api_calls.jsonl` (task_id, credit) |
| 3 | Nghe/đúng lời đọc | **Chưa nghe bằng tai.** Kiểm tra tự động (nay nằm trong `run_all`, lỗi thì dừng): từ engine đọc == văn bản gửi (20/20 và 35/35 từ), từ cuối không vượt thời lượng file, đuôi lặng ≤1,5s | `tools/verify_audio.py`, `tests/test_verify_audio.py` |
| 4 | Nhân vật tách bộ phận + 3 chuyển động (+ nhịp thứ 4: đổi mặt vui cuối) | Đạt theo khung hình đã xem; **bạn cần xem video** | `out1/final.mp4`, `assets/` |
| 5 | Thời lượng 20–30s, đủ 2 cảnh | Đạt: **25,8 s** (Scene1 11,5s, Scene2 14,3s) | log PASS "duration within 20-30 s" |
| 6 | Chạy một lệnh bằng launcher giao cho bạn | Đạt: chạy **bằng `run.bat`** (qua cmd, `NOPAUSE=1`) từ thư mục output/work mới. Chưa bấm đúp trong Explorer | `out1/logs/run_20261018_141745.log` |
| 7 | Lưu → mở lại project → render lại | Đạt (headless CLI): mở lại `scenes.ecproj`, `film.fcproj` ở tiến trình mới, render khung hình; xuất lại 25,8s, `offlineMedia: []`. Chưa mở bằng giao diện app | `reopen_*.png`, `end.png`, `s1.png` |
| 8 | Đổi màu áo / tốc độ chỉ tay / chạy lại không trùng | Đạt | bên dưới |
| 9 | Log từng bước, lỗi, thời gian, lượt gọi API | Đạt | `logs/`, `logs/api_calls.jsonl` |

## Chi tiết kiểm tra 8
- **Đổi áo + tốc độ** (`out_variant/variant_blue_fast.mp4`, `--shirt #2E86DE --point-speed 0.3`): chuyển tay 0,5 s → 0,3 s (keyframe 3,3→3,8 thành 3,5→3,8; đều đến đích đúng lúc từ "Tiền" bắt đầu ở 3,8 s). Lần chạy này **không ghi đè** `project/config.json` (đã đối chiếu: vẫn `#F26B21`, 0.5).
- **Chạy lại nguyên đầu vào** (`final.mp4`, `final_rerun.mp4`, và 2 lần nữa với biến thể): mỗi lần Scene1 = 15 layer, Scene2 = 20 layer, 0 tên layer trùng; timeline đúng 2 clip hình + 2 clip tiếng. Lần chạy lại **không gọi API** ("SKIP voice… reusing audio").
- Âm thanh trên timeline: scene1.mp3 0,3→10,27 s, scene2.mp3 11,77→24,6 s; video Scene1 0→11,47, Scene2 11,47→25,8.

## Đồng bộ
Mốc chỉ tay/hiện chữ/đổi mặt lấy từ **mốc thời gian từng từ do chính engine giọng trả về** (không còn ước lượng theo độ dài chữ). Chưa căn khớp miệng (ngoài phạm vi Phase 1).

## API và cấu hình
- `GET /v1/task/{task_id}` **không có trong tài liệu được cung cấp**; tìm ra bằng thử, hoạt động. Đổi được bằng `AI33_TASK_PATH`.
- Timeout HTTP 60 s, chờ job tối đa 600 s, GET thử lại tối đa 3 lần. **Lệnh tạo job không tự thử lại**; task_id lưu `*.mp3.task` để lần sau tiếp tục job cũ thay vì trả tiền thêm. (Cơ chế resume được kiểm tra bằng đọc code, **chưa mô phỏng mất mạng**.)
- Cấu hình mặc định sau thử nghiệm: không đổi (`project/config.json`). Lúc trước tôi đã từng ghi đè rồi trả lại mặc định; nay không còn ghi đè.
- Lượt gọi API của lần nghiệm thu: 2 job (65+8 và 101+13 credit = 187), ghi trong `logs/api_calls.jsonl`. Các lần chạy lại/biến thể không gọi API. Trước đó còn vài job thử khi phát triển (chưa có log, chưa thống kê credit).

## Hạn chế còn lại
- Chưa nghe giọng, chưa xem video bằng mắt thường (tôi chỉ xem khung hình PNG).
- SVG do script tạo, VectorCraft chỉ chuyển PNG; chưa chỉnh nhân vật trong editor. Chưa dùng MCP.
- Project lưu đường dẫn tuyệt đối (`D:\AnimationFactory\...`), không di chuyển được nếu không dựng lại.
- API key cũ đã dán vào chat: **bạn cần thu hồi và tạo key mới**. Gói ZIP không chứa `.env`.

## Sửa theo review lần 1 (đã làm và kiểm thử)
1. **Job cũ bị dùng nhầm:** `.task` nay lưu `{task_id, sig}` với sig = hash(text, voice, speed). Chỉ tiếp tục khi sig khớp; nếu không thì bỏ job cũ (cảnh báo), xóa audio/words cũ và tạo job mới. Test không tốn credit (HTTP giả): `tests/test_voice_resume.py` – 3/3 đạt (cùng kịch bản → tiếp tục, không tạo job mới; đổi kịch bản/tốc độ/giọng → job mới và audio đúng kịch bản mới). Hạn chế: job bị bỏ có thể đã tính phí ở phía ai33.
2. **Kiểm tra âm thanh sai:** điều kiện cũ `dur - last < 1.0` cho phép file ngắn vẫn đạt. Nay thất bại khi từ cuối kết thúc sau hết file (+0,15s dung sai), khi thiếu timings/file, khi lời khác, hoặc đuôi lặng >1,5s. Đã gắn vào `run_all` (trước bước dựng; lỗi thì xóa hash để lần sau tạo lại). Test: `tests/test_verify_audio.py` 5/5 đạt, gồm mp3 cắt còn ~1s và timings kéo dài; chạy `run_all` với mp3 bị cắt → `FAIL … audio CUT OFF`, exit 1, không xuất video.
3. **Media bàn giao:** ZIP nay có `work/Scene1.mp4`, `work/Scene2.mp4`, audio, words.json, assets, tools, tests. `rebuild_package.bat` (không cần API key): `rebuild_package.bat film` ghép lại từ clip có sẵn; không tham số thì dựng lại từ assets→EffectCraft→FilmCraft. Đã **giải nén ZIP vào thư mục mới** và chạy cả hai chế độ: ra `out
ebuilt.mp4` 25,8s 1920×1080 có audio, `offlineMedia: []`. `projects\*.ecproj/.fcproj` giữ đường dẫn tuyệt đối D:\ ban đầu (chỉ để tham khảo); bản dùng được được dựng lại theo đường dẫn tương đối bởi `rebuild_package.bat`.

## Bổ sung sau review lần 2: kiểm chứng đo thời lượng MP3 (FilmCraft 0.9.0, máy Windows thật)
- Chạy `tests/test_verify_audio.py` bằng FilmCraft thật, `AF_TEST_WORK` = thư mục `work` của gói giải nén: **5/5 chạy, không test nào bị SKIP**, log ở `logs/audio_tests_log.txt` (`test_truncated_audio_fails ... ok`; trường hợp mp3 cắt báo `audio CUT OFF: last word ends 9.14s but file is 1.27s`, mã thoát 1).
- FilmCraft `probe` **không đọc thời lượng cũ**: file gốc 9,96 s; file cắt còn 16 000 byte → 1,27 s.
- Dù vậy, `verify_audio.py` nay **giải mã thật** (`tools/decode_check.py`: FilmCraft render audio ra WAV rồi đo WAV): gốc probe 9,96 s / decode 9,97 s; file cắt 1,27 s / 1,27 s. Thời lượng đã giải mã là mốc quyết định; nếu metadata lệch >0,3 s so với giải mã thì báo lỗi. Hạn chế: chưa tạo được file MP3 có header khai thời lượng sai để thử riêng nhánh "metadata lệch".
- `run.bat` chạy lại đầy đủ với bộ kiểm tra mới: audio verification OK (0,8 s), toàn bộ PASS, 25,8 s.
