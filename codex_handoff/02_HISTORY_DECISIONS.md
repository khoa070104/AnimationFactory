# Lịch sử công việc và quyết định

Không phải transcript. Số liệu dưới đây là các mốc; trừ khi ghi “review”, kết quả chủ yếu do Claude triển khai báo lại trong chat.

## 1. Khởi đầu

Người dùng tìm hiểu Hermes, agent, remake các app Adobe có MCP. Sau đó cài VectorCraft + EffectCraft + FilmCraft, có Antigravity, Claude 5.x và API tạo giọng. Mục tiêu chuyển từ tự làm video sang xây xưởng video tự động, người dùng duyệt.

Hermes/JEV là trao đổi khám phá ban đầu, chưa có quyết định phải tích hợp vào kiến trúc hiện tại. Không thêm chúng như yêu cầu bắt buộc.

## 2. Phase 1 — một lệnh dựng được cảnh

Yêu cầu: kịch bản ngắn + tham khảo nhân vật + API giọng → 20–30 giây, hai cảnh, ít nhất xuất hiện/chỉ tay/đổi biểu cảm, có project chỉnh sửa, chạy lại không trùng layer/clip, đổi màu/tốc độ được, lỗi truy được về từng khâu.

Claude báo:
- Tạo D:\AnimationFactory, work, output.
- Tìm VectorCraft 0.13.1, EffectCraft 0.11.1, FilmCraft 0.9.0 với CLI.
- make_assets.py sinh SVG bộ phận, VectorCraft convert PNG.
- build_scenes.py + scenes_template.jsx dựng layer/keyframe trong EffectCraft.
- build_film.py ghép clip/audio trong FilmCraft.
- run_all.py, config.json, run.bat, HUONG_DAN.md.
- Giọng ai33, nữ Edge HoaiMy. Tài liệu thiếu endpoint lấy task; từng đoán /v1/task/{id} và báo chạy được. Đây là lịch sử, không phải đặc tả API có thể tin mãi.
- Bản đầu 19,3 giây; bản kiểm lại 25,8 giây.
- Đổi màu áo, tốc độ chỉ tay, chạy lại không nhân layer được báo đạt.
- Bộ kiểm âm thanh 5 test thực qua FilmCraft: MP3 cắt 1,27 s phải fail khi từ cuối ở 9,14 s, exit 1.
- Probe file gốc 9,96 s, giải mã WAV 9,97 s; file cắt cùng 1,27 s. Ngưỡng lệch metadata/giải mã 0,3 s; nhánh header khai sai chưa có test riêng khi báo.
- Gói AnimationFactory_Phase1_Evidence.zip khoảng 16 MB, không .env.
Kiểm tự động không thay việc nghe chất lượng/đánh giá phong cách.

## 3. Phase 2 — bộ dựng dùng lại và giao diện duyệt

Bi v2/v2.1:
- Thêm vai/khuỷu/cổ, IK hai đoạn, chỉnh áo/vai; gán parent trong EffectCraft giữ world transform nên phải đặt lại rotation/scale phù hợp.
- Báo đóng băng Bi v2.1, ảnh chuẩn giống từng pixel, 8 hành động/5 biểu cảm, clip demo 25,8 s.
- Những con số/góc rig là chi tiết của nhân vật cũ, không hard-code thành chuẩn cho mọi nhân vật.

Video 1:
- “Nhận lương xong tiền đi đâu?”, 9 cảnh.
- Approval gắn bản kịch bản, 9 lượt giọng thật, 593 credit thực tế; preview 70,7 s.
- Chỉ dựng lại cảnh đổi; cache/hash và timing theo lời được thêm.

Video 2:
- “Quỹ khẩn cấp…”, 8 cảnh; khoảng 61 s/582 credit là dự toán lúc đề xuất, không mặc định là chi phí thực.
- Tạo dự án từ template, produce.py, kiểm storyboard, dự toán.
- Sửa pill dài, phụ đề, fade và cache chỉ phụ thuộc asset cảnh thật dùng.
- Người dùng nhắc rõ phải tổng quát hóa tool; không tiếp tục tối ưu sample đơn lẻ.

UI/MCP/ảnh AI:
- UI có sửa lời, góp ý, duyệt asset, gửi job agy; thử coin_ui thật, draft.
- Sửa speed 1.0 thành 1 khi lưu JSON làm đổi hash giọng bằng canonical float.
- MCP animation-factory-assets cung cấp submit/check; một phiên Claude trước đã gọi hai tool thật, dùng cache umbrella_ai, không sinh mới.
- MCP pending approval ở phiên Chặng 1 sau là tình trạng khác: không suy ra mọi phiên/máy đều kết nối được.

Các vòng sửa job/asset đã báo:
- Key theo project + job, lưu version ảnh bất biến, superseded có kết quả riêng.
- Cache kiểm file + sha256, hỏng/mất phải lỗi, không tự gọi agy.
- approved_sha256 chống dùng ảnh bị thay sau duyệt.
- Ghi manifest nguyên tử và khóa liên tiến trình.
- Owner PID + thời điểm tạo process, tránh PID reuse; process khác không ngắt nhầm job sống.
- Gửi đồng thời cùng yêu cầu chỉ một chạy; owner chết mới interrupted.
- Mốc cuối vòng này: 66 test Phase 2 + 8 Phase 1; ZIP khoảng 95 MB.
Đây là cơ chế agy jobs. Lỗi khóa project/render ở lớp af mới trong Chặng 1 là nhóm khác và vẫn cần sửa theo review.

## 4. Phase 3 — từ brief tới video, rồi thay đổi quan trọng về asset

UI/prepare/LLM/approval/cache/budget đã có theo báo cáo. Người dùng phát hiện tool tận dụng mẫu cũ thay vì phát triển hình mới theo topic, nên chốt:
- Phải lập prompt và tạo nhân vật chính/phụ, nền, đạo cụ thật bằng Antigravity.
- AI dùng các hình đó để dựng hoạt hình và ghép giọng.
- Giữ nền vận hành, thay cách lập kế hoạch tài sản; không xây lại từ đầu.

Kế hoạch tổng hợp v2 ngày 18/10 nằm trong archive:
- Pipeline mới, source grounding, asset policy, series reuse.
- Thử FreeLLMAPI adapter cho tác vụ nhẹ; chưa thêm 9Router ở bước đó.
- Cuối luồng gửi Telegram duyệt có version/hash.
Đó là hướng phát triển, không phải báo cáo đã tích hợp.

Gate 1:
- Ba cảnh, hai nhân vật agy vẽ/rig, draft 35,3 → 36,3 s giọng im lặng.
- Mốc 135 →139 test.
- Sửa chung: hướng đi vào, chờ ngoài khung đến cue, đường đi, step_a tránh tay vào thân, cue nhân vật phụ khi sửa lời.

Sample A:
- Project sample_a_thuc_don_tuan: thực đơn tuần để đỡ tốn tiền ăn, brief 75 s.
- Minh đổi thành Tuấn; nhân vật còn lại Linh.
- Đề xuất ngân sách 14 ảnh, 40 lượt AI, 1200 credit giọng; phải xem approval thực tế.
- Lần đầu chỉ 3 cảnh do dùng kênh gate1 giới hạn 2–3; targets_of sửa ưu tiên thời lượng: 75 s →6–10 cảnh.
- Sau đó 8 cảnh, khoảng 1200 ký tự, hai nền + hai đạo cụ; một số cảnh nền trơn, emoji, ít tương tác.
- Gói GOI_DUYET_SAMPLE_A.md từng có bản sai cú pháp/tên; bản thay thế là bản phải xem. Không dựa bản đính kèm đầu tiên nếu không kiểm version.
- Mốc 140 test.

## 5. Remotion thay vai trò bộ dựng chính

Người dùng thấy quy trình quá phức tạp, muốn học từ video tham chiếu.
Thử Remotion:
- 3 cảnh Sample A, clip 29,8 s, dựng khoảng 31 s.
- Đổi một ô bảng: dựng lại 1 cảnh khoảng 15 s, không gọi API.
- 145 test được báo.
Sau đó Remotion trở thành bộ dựng chính, Craft dự phòng. Yêu cầu cũ mọi output phải qua ba Craft đã được thay đổi trong kiến trúc mới.

Sample A:
- Áp 5 asset, bản 83,8 s/8 cảnh; cảnh 4–6 còn rối.
- v14 khoảng 83,5 s; sửa icon, bảng đủ bảy ô, khung nội dung, túi không lật; 152 test.
- v17 khoảng 92,6 s; mốc 153 test. Có tiếng trong file, nhưng chưa có đánh giá nghe chủ quan đầy đủ ở review này.
- Mở tủ/xếp đồ/ngồi viết chưa hoàn tất như một bộ năng lực dùng chung.
- Sample A 92,6 s được xử lý như ngoại lệ demo kỹ thuật; không nới mọi video mục tiêu 60–90 s lên 95 s, không tự gọi giọng chỉ để cắt vài giây.

Thử nghiệm Remotion cũ từng lộ vấn đề cache thiếu dependency. Bộ test signature về sau đã được bổ sung; không tự gắn mọi lỗi spike cũ vào HEAD mới.

## 6. Định hướng chất lượng cho nhiều chủ đề

Hai tham chiếu:
- “Người đợi chuyến cuối” ở nhà ga: học reveal, điểm chú ý, vật quan trọng, che/lộ.
- “Thiếu ngủ ảnh hưởng thế nào”: học chuỗi toàn cảnh → thao tác → phản hồi, đồ họa giải thích, so sánh/metaphor.
Không xây riêng tool kinh dị hoặc sức khỏe. Không tái sử dụng phát ngôn sức khỏe như dữ liệu đã xác minh.

Tài liệu “Tool cho AI CLI…” chuyển trọng tâm:
- Chặng 1: hợp đồng điều khiển + shot/camera/bố cục.
- Chặng 2: tài sản, pose, tương tác, contact, occlusion.
- Chặng 3: âm thanh, nhịp, kiểm chứng đa nội dung.
Đây là lộ trình chất lượng mới, khác “Phase 1–3” ban đầu và khác cách đánh số trong Master Plan v2 cũ.

## 7. Chặng 1 — phạm vi đã chuẩn bị/triển khai

Giữ Remotion, không web mới, không orchestrator mới; một người ghi mã lõi.
Kế hoạch nghiên cứu 4 agent chỉ đọc và một phiên nghiệm thu độc lập đã được đề xuất/duyệt trong phạm vi đợt đó; không suy diễn thành quyền chạy vô hạn agent trong mọi phiên.

Các điểm thiết kế cần giữ:
- Shot có khoảng thời gian rõ; cue giải ra giây rồi mới kiểm thứ tự/end/ease.
- Pose/đồ vật liên tục qua shot, không phát lại entry mỗi lần đổi camera.
- Camera bbox/padding/background bounds; hướng nhìn theo từng nhân vật.
- Phân lớp world/screen theo ý nghĩa.
- Lớp af mỏng bọc core hiện có; đừng xây hệ job thứ ba.
- Hai đoạn thử 15–25 s: kể chuyện hai người với asset Sample A; giải thích quy trình/so sánh dữ liệu giả được ghi rõ.
- 0 ảnh mới/0 giọng trả phí.
- Thiếu video tham chiếu không chặn việc độc lập khác; MCP chưa duyệt chỉ chặn nghiệm thu đường MCP.
- ASR giúp kiểm chữ/cắt tiếng, không thay đánh giá giọng tự nhiên/cảm xúc.
- Thử CLI thứ hai có sẵn và đăng nhập được; không bắt cài Codex chỉ để đủ danh sách.
- Git cục bộ đã được đồng ý khi chưa có; nay repo tồn tại, không hỏi git init lại.
- Giấy phép Remotion phải đối chiếu điều kiện thực tế trước dùng thương mại, không lấy một câu về quy mô công ty trong lịch sử làm kết luận pháp lý.

## 8. Review và yêu cầu bàn giao hiện tại

Repo public để review: khoa070104/AnimationFactory.
Tại 677a84b, các nền tảng đã có nhưng sáu nhóm lỗi nguồn ngăn chốt Chặng 1. Review visual thêm cách gắn nhãn, biểu tượng, đường camera, framing phản ứng, ngắt phụ đề và hướng nhìn.

Người dùng hỏi có cần push MP4 không; quy trình thuận tiện là Release gắn commit/tag và link tải bản mới nhất của mỗi sample. Không cần commit mọi MP4 trung gian vào lịch sử Git. Bản video không tự đóng lỗi nguồn.

Yêu cầu mới nhất của người dùng chỉ là tổng hợp cuộc chat để Codex PC có ngữ cảnh. Gói bàn giao này không phải bằng chứng đã sửa lỗi, không cấp thêm quyền triển khai hay chi tiêu.

