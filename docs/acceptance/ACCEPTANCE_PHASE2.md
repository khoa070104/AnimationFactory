# Animation Factory – Phase 2: báo cáo kiểm kê và nghiệm thu (2026-10-18)

**Nguyên tắc báo cáo:** đối chiếu trực tiếp mã nguồn, dữ liệu dự án và kết quả chạy; chỉ chạy bổ sung phần còn thiếu hoặc bị ảnh hưởng bởi thay đổi mã. Sample chỉ để chứng minh chức năng. Trạng thái: **đã xác minh / đã viết nhưng chưa xác minh / làm một phần / chưa làm / đang bị chặn**.

**Phiên bản mã được kiểm tra** (không dùng Git): `evidence/code_manifest.json` (56 tệp có sha256; tổng `43dfd82d3d67e592`; riêng đường sản xuất `tools+lib+style` = `70b95d07d6ea8a12`). Mã băm mà `produce.py` ghi vào mỗi dự án: `11701db21ad47fec` (cả ba dự án được dựng lại bằng đúng mã này; `code_changed_since_freeze = false`). Kiểm thử: `evidence/tests_log.txt` (10 tệp, 56 kiểm thử, tất cả đạt).

## 1. Tool nhận gì, tạo gì
- **Đầu vào:** một thư mục dự án có `storyboard.json` (lời đọc, cảnh, nhân vật/biểu cảm/hành động, đạo cụ, chữ, biểu đồ, camera, thời điểm xuất hiện theo cụm lời đọc, cấu hình giọng/thời gian/mục tiêu); tùy chọn asset AI. Khóa API giọng nằm trong `.env` (người dùng tự nhập).
- **Đầu ra:** MP4 1920×1080 30 fps có giọng + phụ đề; project EffectCraft (`scenes.ecproj`) và FilmCraft (`film.fcproj`); ảnh xem trước từng cảnh; `storyboard.md` + `estimate.json` để duyệt; `status.json`, `approval.json`, log từng công đoạn, báo cáo kiểm tra.
- **Tự chạy:** kiểm tra dữ liệu → tạo asset (VectorCraft) → ảnh xem trước + dự toán → giọng (chỉ sau khi duyệt; dùng lại từ kho dùng chung nếu đã có) → kiểm tra audio → dựng từng cảnh (EffectCraft) → ghép (FilmCraft) → QA tự động (độ dài, khoảng lặng, phụ đề, chuyển động) → ghi trạng thái.
- **Claude chuẩn bị:** viết storyboard (lời, cue, bố cục), yêu cầu asset AI qua MCP, đọc log/báo cáo, sửa lỗi tool khi bộc lộ.
- **Người dùng làm:** nhập khóa API vào `.env`, duyệt nội dung (đúng phiên bản) và duyệt asset AI, xem/nghe để duyệt cảm quan, quyết định đăng ký MCP vào cấu hình của mình.
- **Video mới có phải sửa Python/JSX không?** **Không**, trong phạm vi thành phần có sẵn (8 hành động, 5 biểu cảm, 14 đạo cụ trong thư viện, biểu đồ cột/tròn, nhãn, chú giải, hóa đơn, thông báo, camera, `ai:<id>`). **Có** nếu cần loại đối tượng/hành động/đạo cụ chưa có (thêm vào thư viện dùng chung). Video 2 và `ui_demo` được dựng chỉ bằng dữ liệu; `tests/test_validate_and_generality.py` kiểm tra không còn nội dung video nào nằm trong mã dùng chung.
- **Ba app và Antigravity tham gia ở đâu:** VectorCraft: `p2_svg.ensure_png` đổi SVG → PNG 2× cho mọi nhân vật/đạo cụ/biểu đồ mỗi lần dựng. EffectCraft: `scene_anim.jsx` dựng rig, hoạt ảnh, camera, phụ đề và render từng cảnh; script lấy mẫu khớp cho QA. FilmCraft: đo/giải mã audio, ghép clip + tiếng, xuất MP4. Antigravity (`agy`): tạo ảnh asset qua `image-generator` (MCP, CLI hoặc giao diện); ảnh vào cảnh bằng `ai:<id>`.

## 2. Kiểm kê chức năng

| Chức năng | Trạng thái | File/module | Cách sử dụng | Bằng chứng chạy thật | Phần còn thiếu |
|---|---|---|---|---|---|
| Khuôn dự án mới | đã xác minh | `tools/new_project.py` | `new_project.py tên --title "..."` hoặc nút "Dự án mới" | `ui_demo` tạo qua giao diện | khuôn chỉ có 1 cảnh mẫu |
| Nạp storyboard có mặc định, phụ đề tự tạo | đã xác minh | `tools/sbload.py` | tự động mọi công cụ; bỏ `subtitles` = tự chia ≤40 ký tự | `test_dependencies.py`; `ui_demo` chạy với phụ đề tự động | — |
| Kiểm tra dữ liệu trước khi gọi API | đã xác minh | `tools/validate_storyboard.py` | `validate_storyboard.py PROJECT`; chạy trong `produce` và giao diện | `test_validate_and_generality.py` (cue lạ, hành động/tư thế/biểu cảm/màu/nền/đạo cụ lạ, phụ đề lệch/dài, asset AI chưa duyệt) | không kiểm tra va chạm bố cục giữa các mục |
| Thư viện nhân vật Bi v2.1 (rig, 5 biểu cảm, IK tay) | đã xác minh | `lib/bi_rig.jsx`, `tools/p2_svg.py`, `approved/bi_v2.1` | `buildBi` trong mọi cảnh; đổi áo `character.shirt` | `test_baseline.py` (3 khung giống từng điểm ảnh) | chỉ đổi được màu áo; chỉ tay phải |
| 8 hành động + chuyển tiếp | đã xác minh | `lib/bi_motion.jsx` | `actions[]` theo `cue`/`at` | clip trình diễn + `check_motion.py` (83 điểm đánh dấu khớp ≤4 px, phone gắn tay, không xuyên thân, không bật/ngược) | chưa có tay trái/hành động mới |
| Bộ dựng cảnh dùng chung | đã xác minh | `lib/scene_anim.jsx`, `tools/build_storyboard.py`, `tools/build_video.py` | `build_video.py` / `produce.py` | video 1 (9 cảnh), video 2 (9 cảnh), `ui_demo` (3 cảnh) | bố cục tọa độ do người nhập chọn |
| Chữ, biểu đồ, nhãn, chú giải, hóa đơn, thông báo | đã xác minh | `build_storyboard.expand` | mục `chart/pills/pie/legend/bill/notice/text` | 3 dự án; lỗi chung tìm thấy qua video 2 đã sửa (nhãn tràn, tiêu đề chạm viền, căn dọc) | thêm loại biểu đồ mới cần mã |
| Camera | làm một phần | `scene_anim.jsx`, `sbload.resolve_camera` | `camera: push_in|pull_out|pan_left|pan_right` hoặc `{zoom,pan}` | `ui_demo` (đầu nhân vật phóng 1,12 lần ở cảnh push_in); phụ đề đứng yên | chỉ một đoạn zoom/pan tuyến tính mỗi cảnh |
| Giọng đọc có chốt chặn | đã xác minh | `tools/voice_project.py`, `tools/approve.py`, Phase 1 `tools/voice.py` | sau `approve.py`; chỉ cảnh đổi lời mới gọi | `test_voice_project.py`; video 2 thêm cảnh: 1 CALL + 8 SKIP; `ui_demo`: 3 CACHE-HIT, 0 API | chỉ thử giọng Edge HoaiMy; `voice.py` ở thư mục Phase 1 |
| Kho giọng dùng chung | đã xác minh | `voice_project.cache_*`, `voice_cache/` | tự động theo khóa (lời, giọng, tốc độ) | `ui_demo` 0 lượt gọi; test hai dự án | — |
| Kiểm tra audio (không cắt, đúng lời) | đã xác minh | `tools/audio_checks.py`, `tools/decode_check.py` | trong `voice_project` | test truncated/sai lời (phase 1+2) | chưa ai nghe giọng |
| Đồng bộ theo mốc từ | đã xác minh | `tools/cues.py` | `cue`, `appear`, phụ đề | báo cáo dựng: mọi cue/phụ đề trong cảnh | căn khớp miệng ngoài phạm vi |
| Phê duyệt gắn phiên bản | đã xác minh | `tools/approve.py`, giao diện | `approve.py` / nút Duyệt | `test_ui_server.py` (409 khi nội dung đổi), cờ "đổi sau khi duyệt" | — |
| Dự toán và chi phí | đã xác minh | `estimate.json`, `calibrate.py`, `cost_model.json` | tự động | dự toán video 2 582 → thực tế 583 (+70 cho s04b) | mô hình từ 9 job một giọng; ước tính thời lượng lệch ±9% |
| Lệnh sản xuất | đã xác minh | `tools/produce.py` | `produce.py PROJECT [--until storyboard]` | log mọi dự án; dừng `awaiting_approval` | — |
| Dựng lại chọn lọc | đã xác minh | `build_video.py` (chữ ký cảnh) | tự động | `evidence/dependency_cache_video2.md` (8 tình huống) | — |
| Đóng gói + dựng lại từ gói | đã xác minh | `ops/package_all.py`, `REBUILD.bat` | xem mục 5 | dựng lại `ui_demo` từ gói giải nén | project `.ecproj` giữ đường dẫn tuyệt đối (dựng lại bằng REBUILD) |
| MCP Antigravity (2 công cụ) | đã xác minh | `assets_mcp/af_assets_server.py`, `tools/agy_jobs.py`, `tools/agy_image.py` | đăng ký theo `assets_mcp/README.md` | 7 test đầu-cuối stdio (agy giả) + 2 job thật (`evidence/mcp_jobs`) | chưa đăng ký vào cấu hình của bạn; chờ quyết định |
| Asset AI vào cảnh | đã xác minh | `ai:<id>` trong `expand`/validator/`bg_spec` | `{"type":"prop","img":"ai:id"}`, `bg:"ai:id"` | video 2 cảnh 6 dùng heo đất (chỉ cảnh 6 dựng lại); `evidence/mcp_scene_video2.md` | `character` AI chỉ là ảnh tĩnh |
| Kiểm tra nền trong suốt | đã xác minh | `agy_image.transparency_report` | tự động sau hậu xử lý | 2 ảnh thật đạt (góc alpha 0, chủ thể 40–56%); test từ chối ảnh không nền trắng | — |
| Giao diện nội bộ | **đã xác minh một phần** | `ui/server.py`, `ui/static/index.html` | `ui\ui.bat` | một lượt thật trong trình duyệt: tạo dự án → nhập JSON → kiểm tra → lưu → duyệt → chạy → xem video (`ui_demo`); 5 test API | sửa lời, góp ý, duyệt asset, gửi job AI từ giao diện mới được kiểm thử bằng API, chưa bấm trong trình duyệt; chưa có trình soạn storyboard dạng biểu mẫu |

### Phạm vi asset AI đang hỗ trợ
Phông nền (16:9, cắt giữa, không trong suốt) và đạo cụ (nền trắng → trong suốt) dùng được trong cảnh. **Ảnh nhân vật** tạo được và vào cảnh như ảnh tĩnh, **nhưng chưa tách bộ phận/gắn khớp** nên không chuyển động như Bi. Model của bộ tạo ảnh không được agy công bố (ghi `image_model: null`); chi phí chỉ có token (≈44–80 nghìn/ảnh, 1–2,5 phút/ảnh).

## 3. Đối chiếu phạm vi Phase 2
| Đầu việc | Đạt? | Ghi chú |
|---|---|---|
| Cấu trúc dự án | ✔ | dữ liệu, assets, audio, duyệt, đầu ra riêng; khuôn mẫu; `ui_demo` tạo từ khuôn qua giao diện |
| Storyboard bằng dữ liệu | ✔ (camera một phần) | lời, nhân vật, biểu cảm, hành động, đạo cụ, bố cục, camera cơ bản, thời điểm theo cụm; dữ liệu sai báo trước khi dựng |
| Thư viện nhân vật | ✔ | 8 hành động, 5 biểu cảm, khớp/layer chỉnh được (đã thử đổi khớp trong project đóng gói); dùng lại ở 3 dự án |
| Bộ dựng dùng chung | ✔ | video 6–10 cảnh (9 và 9); `ui_demo` 3 cảnh qua `targets` cấu hình được |
| Giọng và đồng bộ | ✔ kỹ thuật | **chưa có người nghe giọng**; mọi kiểm tra là tự động |
| Phê duyệt và chi phí | ✔ | chi phí asset AI chỉ là token, ghi rõ chưa biết tiền |
| Lệnh sản xuất | ✔ | tiến độ/lỗi theo công đoạn trong `status.json` và giao diện |
| Dựng lại có chọn lọc | ✔ | kể cả thay đổi thành phần dùng chung: đổi một hành động chỉ dựng các cảnh dùng nó; đổi rig dựng mọi cảnh |
| Hai video độc lập | ✔ | xem `projects/video2_quy_khan_cap/EVIDENCE.md`: dựng bằng mã đóng băng, không sửa code riêng; **lỗi chung do dữ liệu video 2 làm lộ ra đã được sửa ở thành phần chung**, sau đó cả hai video dựng lại trên mã cuối |
| Giao diện nội bộ | ✔ một phần | xem bảng trên |
| Bàn giao | ✔ | gói zip + hướng dẫn + bằng chứng |

## 4. Các tình huống nghiệm thu
| Sample / thao tác | Kết quả |
|---|---|
| Video 1 | `video1_luong_v2_preview.mp4` 64,8 s, 9 cảnh, mọi kiểm tra đạt, mã `11701db21ad47fec`; còn cờ "đổi sau khi duyệt" ở s03, s05, s06, s07, s09 (thay đổi thời gian/hình sau khi duyệt, chờ chủ dự án duyệt lại) |
| Video 2 | `video2_quy_khan_cap_v3_preview.mp4` 62,1 s, 9 cảnh; một lệnh `produce.py` |
| Chạy lại video 2 không đổi | 0 lượt API, 0 cảnh dựng lại (`dependency_cache_video2.md` #1) |
| Đổi bố cục một cảnh (bản sao) | chỉ cảnh đó dựng lại, 0 lượt API (#4) |
| Đổi lời một cảnh, chạy khô | chặn tới khi duyệt lại; kế hoạch: 1 cảnh (123 ký tự, ≈89 credit), 8 cảnh không gửi; 0 lượt API (#5). Chạy thật một lần chỉ có test giả API (chưa tốn credit) |
| Thêm asset không dùng / sửa asset đang dùng | không dựng lại cảnh nào / chỉ dựng cảnh dùng (#2, #3) |
| Một cảnh dùng ảnh Antigravity qua MCP | job `umbrella_ai-90c3537188`, `calm_room_ai-deed835bee`; dữ liệu cảnh + render + gọi lại dùng cache (`mcp_scene_video2.md`); heo đất trong video 2 là bản đã duyệt |
| Một lượt qua giao diện | `ui_demo`: nhập → duyệt → dựng → xem, 0 lượt API (câu dùng lại từ kho giọng) |
| Sửa thành phần dùng chung | #6 (một hành động) và #7 (rig) trên bản sao của cây mã |

## 5. Hướng dẫn nhanh và bàn giao
Giao diện: `phase2\ui\ui.bat`. Dòng lệnh và dữ liệu: `phase2\HUONG_DAN_PHASE2.md`. Gói: `D:\AnimationFactory\AnimationFactory_Phase2_Acceptance.zip` (không có `.env`, khóa hay token; thiếu clip cảnh trung gian, dựng lại bằng `REBUILD.bat tên_dự_án` khoảng 2 phút, không cần khóa và không gọi API).

## 6. Hard-code còn lại (không phải nội dung video)
Thư viện đạo cụ và thiết kế Bi nằm trong `p2_svg.py` (đổi thiết kế = đổi mã); hằng số bố cục của các thành phần (bảng 820×600, độ lệch chữ 0,32×cỡ chữ, bề rộng nhãn 0,62×cỡ chữ/ký tự…) chỉnh theo font Inter; khung 1920×1080, 30 fps trong `style/tokens.json`; dự toán dùng `cost_model.json`; đường dẫn ba CLI giờ cấu hình được (`toolpaths.py`); giọng gọi qua `tools/voice.py` của Phase 1 và `.env` ở `D:\AnimationFactory`; chuỗi tiếng Việt trong tài liệu sinh tự động và giao diện.

## 7. Việc còn lại (theo thứ tự)
| Việc | Lý do | Đầu ra | Nghiệm thu |
|---|---|---|---|
| 1. Chủ dự án duyệt/loại `umbrella_ai`, `calm_room_ai`; duyệt lại các cảnh video 1 bị cờ; **thu hồi khóa API cũ đã dán vào chat** | quyết định thuộc về chủ dự án; bảo mật | trạng thái duyệt trong manifest/`approval.json`, khóa mới trong `.env` | `agy_image.py list`, `approve.py` |
| 2. Nghe/xem toàn bộ hai video | chưa ai nghe giọng; kiểm tra cảm quan không thay bằng tự động | góp ý theo cảnh | ghi góp ý trong giao diện |
| 3. Bấm thử trong trình duyệt: sửa lời, góp ý, duyệt asset, gửi job AI | mới có bằng chứng API | ảnh chụp/log thao tác | một lượt đầy đủ không gặp lỗi |
| 4. Đăng ký MCP vào cấu hình Claude của bạn | cấu hình lâu dài cần bạn đồng ý | mục trong `.mcp.json` | gọi `submit_asset_job` từ một phiên mới |
| 5. Trình soạn storyboard dạng biểu mẫu thay cho ô JSON | giảm lỗi nhập tay | form thêm/sửa cảnh, mục | tạo dự án mới không đụng JSON |
| 6. Chuyển cảnh thật (slide/dissolve), camera nhiều đoạn, tay trái, tách bộ phận nhân vật từ ảnh AI | giới hạn hiện tại | thành phần mới trong thư viện | dữ liệu dùng được không sửa mã |
| 7. Giọng/nhà cung cấp khác | mới thử Edge HoaiMy | mô hình chi phí theo nhà cung cấp | một video với giọng khác |
| 8. Khởi tạo Git (nếu muốn quản lý phiên bản theo commit) | hiện dùng danh sách mã băm | repository | `git log` |
