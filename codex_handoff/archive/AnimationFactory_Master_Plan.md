# AnimationFactory — kế hoạch tổng hợp từ topic đến hoạt hình và duyệt Telegram

Phiên bản kế hoạch: 2 — cập nhật sau báo cáo nghiệm thu Phase 3, ngày 18/10/2026.
Trạng thái: kế hoạch phát triển tiếp trên nền Phase 3 hiện có; không phải xác nhận nghiệm thu mã nguồn.
Căn cứ: báo cáo “Phase 3 – Báo cáo nghiệm thu” trong Pasted markdown.md, phản hồi trải nghiệm của người dùng và kế hoạch tổng hợp trước.
Phạm vi đã đọc để cập nhật: nội dung báo cáo và kế hoạch. Chưa mở mã nguồn, log bằng chứng hoặc video Phase 3 được nêu trong báo cáo. Các khả năng “đã có” dưới đây đều là theo báo cáo của Claude và cần đối chiếu đúng bản code khi bắt đầu triển khai.

## 1. Mục tiêu sản phẩm và kết luận sau đối chiếu

Người dùng nhập topic; có thể kèm story guideline, ảnh/mô tả nhân vật, người xem, thị trường, phong cách, thời lượng và ngân sách. Tool tự nghiên cứu, chọn góc kể, viết kịch bản, lập scene và prompt, giao Antigravity tạo bộ hình, rồi Claude điều phối Craft để tạo hoạt ảnh, ghép giọng và gửi video qua Telegram để duyệt.

Nếu chưa có nhân vật, tool phải tự đề xuất và sinh nhân vật phù hợp câu chuyện. Nhân vật chính, nhân vật phụ, bối cảnh và đạo cụ phải đi từ kế hoạch sản xuất đến ảnh tạo thật; không mặc định lấy Bi hay tài sản của sample.

Phase 3 theo báo cáo đã có một nền vận hành đáng kể: giao diện, gọi LLM lúc chạy, kiểm tra storyboard, tạo một số ảnh, voice, cache, ngân sách, phê duyệt và phục hồi. Không yêu cầu xây lại các phần này.

Khoảng thiếu cốt lõi là:
- Chính sách hiện tại ưu tiên dùng lại asset đã duyệt từ dự án khác.
- Chưa có bộ hình nhân vật AI → tách phần/khớp → chuyển động trong Craft.
- Storyboard còn bị giới hạn bởi danh mục nhân vật/hành động sẵn có.
- Chưa có bằng chứng runtime Claude lập kế hoạch cho nhân vật AI mới và điều phối việc dựng nhân vật đó.
- Tra cứu xác minh nguồn đã có nhưng chưa tương đương nghiên cứu cơ hội SEO/xu hướng/cạnh tranh.
- FreeLLMAPI và duyệt Telegram chưa được báo cáo là đã triển khai.

Ưu tiên triển khai: tạo một cảnh ngắn bằng nhân vật AI mới và chuyển động thật trước, sau đó mở rộng nhiều cảnh, rồi hoàn thiện nghiên cứu cơ hội và Telegram. Đây là thứ tự phát triển; luồng sử dụng cuối cùng vẫn bắt đầu bằng nghiên cứu topic.

## 2. Bảng nền hiện có: giữ lại, mở rộng hay bổ sung

| Hạng mục | Báo cáo Phase 3 nói đã có | Quyết định cho đợt tiếp |
| --- | --- | --- |
| Giao diện | ui/server.py, ui/static/index.html; 7 tab; brief, form storyboard, asset, kết quả, hồ sơ kênh | Giữ; mở rộng form nhân vật/series, chính sách asset và Telegram trong cấu trúc sẵn có |
| LLM lúc vận hành | llm.py, aiconfig.py; agy headless, đầu ra --json-schema; vai cheap/quality/fallback đã chạy thật | Giữ đường agy; thêm provider adapter FreeLLMAPI tùy chọn, không buộc thay backend đang dùng được |
| Model | Báo cáo ghi cheap = Gemini 3.8 Flash (Low), quality = Claude Sonnet 4.6; model thật đọc từ log agy | Đây là cấu hình được báo cáo, chưa phải xác minh độc lập về model/quyền truy cập; kiểm tra log lúc triển khai |
| Tra cứu nguồn | research.py tìm bằng web-search, mở URL, lưu URL cuối/thời điểm, đối chiếu dẫn chứng | Cải thiện tìm bài cụ thể và tỷ lệ nguồn dùng được; bổ sung nghiên cứu cơ hội chủ đề |
| Kịch bản/storyboard | prepare.py, capabilities.py, validator, sửa cấu trúc/bố cục có giới hạn | Giữ; mở rộng theo bộ nhân vật/rig của dự án thay vì chỉ danh mục mẫu |
| Sửa nội dung | revise.py; bảng trước/sau; áp dụng có kiểm tra phiên bản | Dùng lại cho sửa nhân vật, scene và phản hồi Telegram |
| Căn cue | realign.py dò cụm từ, không thấy thì chuyển mốc gần đúng | Giữ cơ chế; bổ sung độ tin cậy và cờ cần xem lại, không coi mốc gần đúng là khớp ngữ nghĩa |
| Hình AI | agy_jobs dùng chung UI/MCP; có tạo notebook_ai, tạo lại ảnh và selective rebuild thật theo báo cáo | Giữ job/cache/version; mở rộng sang bộ nhân vật, nhiều lớp nền, đạo cụ và ảnh tham chiếu |
| Chính sách dùng lại hình | Ưu tiên asset được duyệt ở dự án khác | Đổi mặc định cho dự án/series mới; chỉ dùng lại theo series hoặc lựa chọn rõ ràng |
| Rig nhân vật AI | Báo cáo xác nhận chưa có; chỉ tay phải | Là phần mới phải xây; không ép nhân vật mới dùng kích thước/điểm xoay riêng của Bi |
| Phê duyệt | approve.py, hash theo loại, approvals_history.jsonl; tên người duyệt tự khai | Giữ hash/lịch sử; bổ sung danh tính/ngữ cảnh duyệt, tách test/AI khỏi người thật |
| Ngân sách | budget.py, logs/ai_ledger.jsonl; hạn mức gọi/token/ảnh/voice, kiểm tra trước chạy | Giữ; mở rộng sang backend mới, mọi lần repair/retry/fallback và batch ảnh |
| Khóa agy toàn máy | agy_slots.py; mặc định 1 slot chung UI/MCP/CLI; chủ chết thì nhường | Đã có theo báo cáo: tích hợp mọi đường agy mới vào đây, không tạo cơ chế khóa thứ hai |
| Phục hồi và xuất gói | interrupted/resume; overview.py, produce.py, export_project.py, ZIP bàn giao | Giữ; thêm trạng thái nhân vật/rig và gửi Telegram |
| Chuyển động mẫu | lib/scene_anim.jsx đã sửa bằng cách xếp hành động nối tiếp để tránh giật khớp | Rà xung đột theo khớp/track và lệch cue; không mặc định mọi hành động đều phải nối đuôi |
| Telegram | Không được báo cáo là đã có | Bổ sung gửi video, nhận góp ý và duyệt theo phiên bản |
| FreeLLMAPI | Không được báo cáo là đã có | Bổ sung sau đường dựng hình AI; chỉ bật mặc định khi có kết quả thử phù hợp |

Tên module là theo báo cáo, cần xác định đường dẫn thật trong code. Không tự tạo một hệ thống song song nếu đã có module đáp ứng.

### Bằng chứng đang ở mức nào?

- Theo báo cáo: dự án lap_ngan_sach_chi_tieu_hang_th có 7 cảnh, video 80,2 giây 1920×1080, 7 lượt voice/743 credit, notebook_ai mới và hai asset dùng lại, 11/11 kiểm tra đầu ra đạt.
- Đây là bằng chứng được báo cáo cho luồng brief → video trên nền hiện tại; chưa chứng minh bộ nhân vật AI mới có thể hoạt hóa.
- Hai brief khác chủ đề mới được báo cáo chạy đến kịch bản/storyboard; chưa phải hai video với nhân vật mới.
- Tạo lại một asset và chỉ dựng lại s03 đã có bằng chứng chạy thật theo báo cáo.
- Sửa lời s05 mới chứng minh đến kế hoạch một cảnh/~146 credit và chặn trước duyệt; lần sinh giọng và dựng sau sửa chưa chạy thật. Giữ trạng thái “bằng chứng cuối còn thiếu”.
- Báo cáo không cho số tổng test Phase 3 rõ ràng. Không suy ra số test từ các tên test hoặc từ báo cáo Phase 2 cũ.
- Duyệt lời/storyboard của Khoa được báo cáo là có; ba asset đang được ghi duyệt từ thao tác thử của Claude chưa tương đương người dùng duyệt hình.
- Việc nghe/xem và duyệt chất lượng video vẫn là việc chưa hoàn tất theo báo cáo.

## 3. Hợp đồng sản phẩm

### 3.1. Đầu vào

Topic là trường tối thiểu. Các trường mở rộng:
- Nhân vật: mô tả ngoại hình/tính cách, ảnh tham khảo, trang phục, màu sắc, giọng, vai chính/phụ.
- Story guideline: chủ đề lớn, thế giới truyện, cách kể, thông điệp, mức hư cấu và nội dung cần tránh.
- Người xem/nền tảng: ngôn ngữ, thị trường, YouTube hoặc nền tảng khác, tỷ lệ khung hình.
- Sản xuất: thời lượng mục tiêu và khoảng cho phép, ngân sách, chế độ duyệt, tạo series mới hay tiếp series hiện có.

### 3.2. Đầu ra

- Nghiên cứu cơ hội có nguồn và mức tin cậy.
- Outline, kịch bản, storyboard và danh mục prompt/asset.
- Bộ hình mới qua Antigravity, bộ nhân vật có khớp và dữ liệu chuyển động.
- MP4 có giọng cùng project Craft chỉnh sửa được.
- Video gửi Telegram, lịch sử góp ý và phê duyệt gắn với phiên bản.
- Gói bàn giao, số liệu sử dụng/chi phí đã biết và các khoản chưa biết.
- Tiêu đề, mô tả, từ khóa và phương án thumbnail phù hợp nội dung, nếu bật gói xuất bản. Đăng công khai là thao tác riêng.

### 3.3. Quy tắc dùng tài sản

Cần có chính sách dữ liệu rõ, ví dụ:
- New series: tạo bộ hình kể chuyện mới từ prompt/ảnh tham chiếu.
- Continue series: dùng lại nhân vật/asset đúng phiên bản của series đã chọn; tạo mới hình còn thiếu.
- Explicit library selection: người dùng chọn tài sản từ thư viện, có kiểm tra phù hợp nhận diện/phong cách.

Tên chế độ chỉ là đề xuất. Dự án cũ giữ chính sách và đường dẫn cũ để tiếp tục mở được; chỉ chuyển khi có thao tác migration rõ ràng. Thay mặc định không làm dự án đã duyệt tự tạo lại toàn bộ ảnh.

Không dùng lại ngầm asset của dự án khác chỉ vì đã approved. Được dùng lại mã dựng, rig schema, toán IK, template chuyển động, validator, job và cache.

Trong cùng một yêu cầu không đổi, luôn dùng cache hợp lệ. “Tạo mới cho series mới” không có nghĩa “gọi AI lại ở mọi lần chạy”.

## 4. Kiến trúc thực thi dựa trên Phase 3

Luồng cuối:
Brief/topic → nghiên cứu cơ hội và kiểm chứng nguồn → kịch bản → storyboard cùng kế hoạch chuyển động → kế hoạch asset/prompt → agy_jobs tạo hình → chuẩn hóa/rig → adapter Craft dựng cảnh → audio/cue/timeline → kiểm tra → Telegram → góp ý → sửa đúng phần phụ thuộc.

Vai trò:
- Claude ở vai quality mở rộng từ llm.py qua đường gọi hiện có để lập kế hoạch nhân vật, cảnh và sửa theo phản hồi.
- Bộ điều phối kiểm tra kế hoạch, giới hạn quyền/lượt gọi và thực thi qua adapter Craft. Claude có thể lập hoặc điều chỉnh lệnh/script thông qua giao diện công cụ được kiểm soát; không viết lại pipeline riêng cho từng tập.
- Cần bằng chứng runtime mới thực sự chọn hành động cho nhân vật/asset mới, không chỉ viết lời rồi gọi template Bi.
- Antigravity tạo hình qua lớp agy_jobs hiện có. Job ảnh, cache và lịch sử của UI/MCP dùng chung.
- agy_slots kiểm soát tất cả lượt agy dùng cho LLM hoặc hình. Tránh giữ một slot rồi chờ job con cũng cần chính slot đó.
- VectorCraft chuẩn bị/tổ chức tài sản; EffectCraft dựng lớp, khớp/keyframe/camera; FilmCraft dựng timeline, âm thanh và xuất phim. Khả năng import/tách lớp/rig mới phải kiểm tra bằng lệnh thật; thiếu thì có bước tiền xử lý và báo cáo rõ.
- API giọng và produce.py tiếp tục dùng nền hiện có.

Chưa cần đổi toàn bộ sang Claude API riêng: báo cáo đã có LLM trong luồng chạy qua agy. Việc cần làm là mở rộng và chứng minh khả năng điều phối mới, xác minh đường gọi/model thực tế, đồng thời giữ cấu hình thay backend. Không suy luận quyền API từ tên subscription.

## 5. Ba chặng triển khai tiếp

### Chặng 1 — Bộ hình mới → nhân vật có khớp → một cảnh chuyển động

Mục tiêu: xử lý khoảng thiếu cốt lõi bằng một bằng chứng ngắn, trước khi đầu tư thêm vào SEO hoặc hoàn thiện sample dài.

Các công việc:
1. Xác định chỗ ưu tiên dùng asset cũ trong prepare/asset planner; đưa chính sách new series/continue series vào brief, hồ sơ kênh và giao diện hiện có.
2. Thêm hồ sơ nhân vật và tài liệu phong cách: tỷ lệ, màu, trang phục, khuôn mặt, góc nhìn, tính cách và các đặc điểm phải giữ.
3. Từ một topic, dùng pipeline kịch bản hiện có lập một cảnh ngắn và kế hoạch chuyển động. Chưa cần hoàn thiện hệ thống chấm điểm SEO để chứng minh bước này.
4. Asset planner sinh danh mục đầy đủ: nhân vật chính, nhân vật phụ nếu cảnh có, mặt/tư thế/bộ phận, nền trước/sau và đạo cụ.
5. Prompt pack tự sinh theo yêu cầu chuyển động: góc nhìn, bộ phận riêng, vùng nối khớp, nền trong suốt, vùng trống để đặt nhân vật/chữ và ảnh tham chiếu.
6. Dùng Antigravity tạo character sheet chuẩn rồi các phần/biến thể bám cùng nhận diện. Không dùng model ID ảnh suy đoán; nếu agy không trả thì ghi chưa biết.
7. Chuẩn hóa ảnh và tạo cấu trúc khớp theo dữ liệu. Có phương án tách/cắt bộ phận, hoàn thiện vùng bị che và overlap tại khớp; không ghép một bộ tay sample lên thân AI mới.
8. Mở rộng capabilities.py và validator theo rig hiện tại của dự án: phần nào thực sự có và hành động nào thực sự hỗ trợ. UI và prompt LLM đọc cùng danh mục.
9. Mở rộng adapter/scene_anim để nhận phần thân, pivot, chiều dài khớp, phạm vi và thứ tự lớp từ rig; tránh hằng số chỉ đúng với Bi.
10. Import hình mới vào Craft, dựng clip 10–15 giây: ít nhất giơ/chỉ tay, đổi biểu cảm và tương tác với một đạo cụ; có giọng ngắn nếu cần kiểm tra cue.
11. Hiển thị bộ nhân vật trong tab Asset sẵn có, xem trong cảnh và tạo lại đúng phần. Duyệt hình gắn hash; rig tham chiếu đúng phiên bản hình.

Phạm vi đầu: nhân vật 2D hình người đơn giản dạng cutout, nền chia lớp, ít góc nhìn. Hỗ trợ thay mặt/tư thế có kiểm soát. Chưa cam kết mọi ảnh đầu vào, nhân vật 3D hoặc xoay 360 độ đều tự rig được.

Đầu ra:
- Chính sách dùng asset mới/theo series.
- Character profile, prompt pack, ảnh chuẩn và bộ phần/tư thế/biểu cảm.
- Manifest nguồn tạo/version/hash/job; rig có khớp.
- Clip ngắn và project chỉnh sửa dùng hình mới, kèm log gọi công cụ.

Điều kiện qua chặng:
- Các hình kể chuyện trong bài này được tạo thật qua Antigravity; không đọc thư mục hình sample.
- Chuyển động bộ phận nhìn thấy được; pan/zoom cả ảnh không thay thế được.
- Nhận diện nhất quán và không hở khớp nghiêm trọng.
- Chỉ đổi mô tả nhân vật/phong cách trong dữ liệu đã tạo được bộ mới mà không viết renderer riêng.
- Project mở lại giữ các lớp. Chặn đường dẫn sample là test độc lập, không xóa tài sản của người dùng.
- Clip đạt là bằng chứng kỹ thuật; chưa tự đánh dấu người dùng đã duyệt phong cách.

### Chặng 2 — Kể chuyện nhiều cảnh bằng nhân vật mới, âm thanh và sửa từng phần

Mục tiêu: mở rộng cảnh đã chứng minh thành tool dựng cả câu chuyện, giữ năng lực cache/duyệt/voice hiện có.

Các công việc:
1. Mở rộng prepare.py/capabilities.py theo bộ nhân vật mới: vai chính/phụ, đối thoại, quan hệ, hành động, biểu cảm, đồ vật, camera và lớp nền.
2. Tạo storyboard bám kịch bản, có mục đích từng cảnh và nhịp kể; tránh chỉ minh họa các câu bằng chữ/biểu đồ. Kịch bản cần có mở đầu thu hút, mục tiêu/vấn đề của nhân vật, diễn biến, chuyển biến và kết thúc phù hợp guideline. Người duyệt đánh giá mức dễ hiểu, tính cách nhất quán và ý nghĩa của chuyển động, không chỉ lỗi kỹ thuật.
3. Cho nhân vật tương tác với đạo cụ hoặc nhân vật khác. Một hành động có mục tiêu/tọa độ và mốc lời, không gắn với vị trí của sample.
4. Kế hoạch nền có vùng đặt nhân vật, chữ và điểm quan trọng. Khi nền đã vẽ sẵn đạo cụ thì xác định rõ có đặt thêm đạo cụ rời hay không; tránh trùng hình.
5. Mở rộng layout.py ngoài hộp chữ/layer: vùng an toàn, lớp che trước/sau, khuôn mặt/chủ thể quan trọng của nền. Trường hợp chưa đánh giá tự động được phải đánh dấu cần xem preview.
6. Rà lib/scene_anim.jsx: giải quyết xung đột theo khớp/track. Cho phép chuyển động độc lập đồng thời; xung đột cùng khớp phải cắt ngắn, trộn hoặc sắp lịch rõ ràng. Không chỉ đẩy mọi hành động về sau rồi làm lệch lời.
7. Ghi mốc dự định và mốc thực của cue, sai lệch và lý do. Ngưỡng chấp nhận được chốt trước bài thử; vượt ngưỡng phải sửa hoặc chờ xem lại.
8. Dùng realign.py hiện có sau sửa lời. Cụm mất/đổi nghĩa tạo mốc gần đúng phải có cờ cần xem lại; đổi ý lớn phải lập lại cue theo câu mới.
9. Dùng API giọng hiện có; kiểm tra audio thật/giải mã. Nhiều giọng chỉ khi API hỗ trợ và đã thử; mouth-open theo audio không được báo thành lip-sync ngữ âm chính xác.
10. Dựng theo thời lượng audio thực. Giữ khoảng thời lượng người dùng đã chốt; nếu lệch thì điều chỉnh nội dung/pacing trong quyền đã cho hoặc đưa lựa chọn. Không tự nới khoảng để bài test đạt.
11. Giữ renderer nhiều cảnh, selective rebuild, export_project và ZIP. Chỉ scene/voice/asset phụ thuộc thay đổi mới làm lại.
12. Bổ sung trạng thái rig/character generation vào cơ chế interrupted/resume và chi phí hiện có.

Đầu ra:
- Storyboard và kế hoạch chuyển động cho nhiều nhân vật/cảnh.
- Thư viện hành động áp dụng cho bộ hình mới; preview từng cảnh.
- Video 60–90 giây, 6–10 cảnh, audio, phụ đề và project chỉnh sửa.
- Bảng ảnh hưởng khi sửa một câu, asset, biểu cảm hoặc nhận diện nhân vật.
- Log thời lượng/cue, va chạm bố cục và kết quả xem/nghe.

Điều kiện qua chặng:
- Ít nhất ba loại chuyển động, hai biểu cảm và một tương tác có nghĩa với câu chuyện.
- Hình nhận diện ổn định qua cảnh; lời nghe đủ và hành động khớp ý.
- Kịch bản, nhân vật và nền khác sample cũ.
- Một lần sửa lời được sinh giọng và dựng lại thật đúng phạm vi, không chỉ dừng ở dry-run.
- Chạy lại không đổi không phát sinh lượt sinh LLM/ảnh/voice. Việc chủ động làm mới nghiên cứu là yêu cầu riêng.
- Các lỗi chung được sửa tại module dùng chung, không vá từng video.

### Chặng 3 — Nghiên cứu cơ hội, tối ưu LLM và duyệt Telegram trên giao diện hiện có

Mục tiêu: hoàn thành trải nghiệm nhập topic và nhận bản hoạt hình để duyệt, tận dụng bảy tab hiện tại.

A. Nghiên cứu và chọn chủ đề:
1. Giữ research.py và bộ đối chiếu nguồn; cải thiện truy vấn tìm bài cụ thể, theo liên kết ứng viên liên quan, ghi URL gốc/cuối, đoạn trích, ngày bài nếu có và thời điểm truy cập.
2. Không coi trang chủ tự động là sai, nhưng chỉ dùng claim thực sự được nội dung trang đó hỗ trợ. Không tìm được bằng chứng thì đánh dấu rõ và xử lý trong số vòng tìm lại hữu hạn.
3. Giữ chốt không đưa số liệu thiếu căn cứ vào lời đọc. Người dùng chấp nhận dùng một giả định không biến giả định thành thông tin đã xác minh.
4. Thêm cơ hội chủ đề: cụm từ, ý định người xem, tín hiệu nhu cầu/xu hướng, cạnh tranh ước tính, góc kể khác biệt, mức phù hợp guideline và lịch sử series.
5. Chọn nguồn dữ liệu nền tảng theo quyền truy cập thật. Đề xuất YouTube trước; không dùng độ khó tìm kiếm Google làm chỉ số cạnh tranh YouTube. Không bịa search volume hoặc endpoint dữ liệu.
6. Hiển thị số liệu đo được riêng với suy luận/xếp hạng AI. Trường thiếu để trống/ghi thiếu; không gán 0 rồi kết luận ít cạnh tranh.
7. Lưu lịch sử topic/tập để tránh trùng ý. Chỉ cập nhật nội dung chính thức của thế giới truyện từ bản được chấp nhận; vẫn theo dõi draft để tránh làm trùng công việc.

B. FreeLLMAPI và hiệu năng:
1. Thêm một backend adapter vào llm.py/aiconfig.py. Giữ agy backend và vai cheap/quality/fallback; không xây bộ điều phối mới.
2. Dùng thử FreeLLMAPI cho tóm tắt nguồn, phân loại, ý tưởng và prompt nháp. Antigravity vẫn tạo hình; voice vẫn dùng API hiện tại. Chưa thêm 9Router.
3. Kết quả phải qua cùng schema/validator và log về cùng ledger. Ghi actual model/provider nếu có; không biết thì ghi chưa biết.
4. Thử một tập nhỏ khoảng 20 tác vụ từ dữ liệu thực, so với agy hiện có về tỷ lệ đầu ra dùng được, số lần sửa, thời gian trung vị/P95 và chi phí đã biết. Bật theo từng loại việc nếu có lợi; không mặc định model tên “cheap” sẽ nhanh.
5. Thời gian 5–6 phút/phần AI và khoảng 1,5 phút/ảnh trong báo cáo là mốc tham khảo, cần đo lại cùng workload. Ưu tiên cache, giảm lượt repair và gom yêu cầu hợp lý trước khi tăng số slot.
6. Ngân sách hiện có phải tính mọi lượt tạo/repair/retry/fallback theo toàn job. Không để retry ở llm.py và gateway nhân số lần vô hạn. Kiểm tra đủ hạn mức trước mỗi lượt thực sự tốn quota.
7. FreeLLMAPI hỏng/hết quota có trạng thái hoặc fallback trong cấu hình được phép; không tự chuyển sang nhà cung cấp đắt hơn ngoài ngân sách. Không biến khoản chưa biết giá thành 0 đồng.

C. UI, phê duyệt và Telegram:
1. Mở rộng bảy tab hiện có bằng nhân vật/series, chính sách asset, nghiên cứu cơ hội và trạng thái gửi. Không giao xây lại form storyboard đã có.
2. Phân biệt người thật, tác nhân AI, tài khoản thử và quyền tự sản xuất bản nháp. Tên tự nhập chỉ là nhãn hiển thị, không phải bằng chứng định danh.
3. Giữ approve.py/hash/history. Phê duyệt phải ràng buộc snapshot nội dung, asset, rig và bản dựng liên quan; nguồn duyệt web/Telegram được ghi rõ.
4. Mặc định giữ chế độ duyệt từng bước hiện có. Thêm chế độ tự dựng draft khi người dùng cho phép guideline/ngân sách; không giả mạo chữ ký người duyệt để đi qua gate.
5. Telegram gửi video thật cùng mã dự án, phiên bản, duration và tóm tắt chi phí/thay đổi. Link dự phòng phải mở được trên điện thoại, không dùng localhost/ổ D:.
6. Chỉ chat/user được cấu hình có quyền Duyệt/Yêu cầu sửa/Loại. Callback giữ phiên bản/hash, hết hiệu lực khi bản mới thay thế; xử lý callback lặp không tạo job lặp.
7. Góp ý đi qua revise.py: lập đề xuất và phạm vi thay đổi, hiển thị trước/sau, áp dụng có kiểm tra phiên bản; người dùng có thể xác nhận qua Telegram. Góp ý mơ hồ cần làm rõ trước lượt sinh tốn phí.
8. Lưu hàng đợi gửi, message ID và trạng thái. Nếu mất mạng sau gửi mà chưa rõ kết quả, giữ trạng thái chưa xác định để đối chiếu, không gửi lại mù quáng.
9. Xuất video/project/asset/log và gói metadata/thumbnail theo cơ chế export hiện có. Duyệt video không tự đăng công khai.

Đầu ra:
- Nghiên cứu cơ hội có nguồn và trạng thái bằng chứng.
- Adapter FreeLLMAPI có cấu hình, thử thật và báo cáo so sánh; có thể tắt mà luồng agy vẫn chạy.
- UI mở rộng và Telegram gửi/sửa/duyệt thật.
- Lịch sử tác nhân, phê duyệt, phiên bản và chi phí dùng chung.

Điều kiện qua chặng:
- Input topic → bộ hình mới → hoạt ảnh → video Telegram chạy từ giao diện.
- Người dùng yêu cầu sửa một cảnh và nhận bản mới; duyệt cũ không áp dụng cho bản mới.
- Nguồn thiếu/không truy cập được hiển thị đúng; không gắn nhãn SEO chắc chắn khi thiếu dữ liệu.
- Không đánh dấu hoàn thành tích hợp Telegram hoặc FreeLLMAPI chỉ từ mock.

## 6. Các điểm phải chỉnh sau báo cáo trước khi chốt nghiệm thu

| Điểm trong báo cáo | Yêu cầu xử lý |
| --- | --- |
| Cửa sổ brief đổi từ ±10 sang ±15 giây sau khi video 80,2 giây bị fail | Lưu target/min/max hoặc tolerance như điều kiện nghiệm thu trước chạy. 80,2 giây nằm trong mục tiêu chung 60–90, nhưng không được dùng việc nới cửa sổ để chứng minh đạt brief 70 ±10. Thay tiêu chí phải được ghi nhận và người dùng chấp nhận |
| Sửa giật khuỷu bằng cách nối tiếp enter và hành động theo cụm từ | Kiểm tra cả độ mượt và độ lệch cue/ý nghĩa. Chỉ hết giật chưa chứng minh chỉ tay đúng lúc |
| realign chuyển sang mốc gần đúng khi mất cụm | Gắn cờ cần xem lại/độ tin cậy; không tự coi là đã căn đúng nội dung |
| Ba asset ghi duyệt do thao tác thử của Claude | Giữ lịch sử, phân loại tác nhân thử và yêu cầu người dùng duyệt trước khi coi là hình đã được họ chấp nhận. Không viết lại lịch sử thành người thật |
| Tên người duyệt tự khai | Bổ sung ngữ cảnh xác thực người vận hành/web session hoặc Telegram user/chat. Không đồng nhất khóa tệp với xác thực người dùng |
| URL thường là trang chủ, nguồn bị thiếu căn cứ nhiều | Nâng chất lượng tìm và đối chiếu bài cụ thể, đo tỷ lệ claim có bằng chứng; không giải quyết bằng cách bỏ kiểm tra hoặc yêu cầu người dùng xác nhận hàng loạt |
| Nền AI có thể trùng/che hình rời | Asset plan quy định rõ thành phần nền và lớp rời; preview toàn cảnh kiểm tra chồng/che, nhất là mặt/tay/đạo cụ |
| Sửa s05 chỉ đến dry-run | Hoàn tất một ca sửa lời có voice thật trong Sample A; có thể dùng ca mới thay vì tiêu thêm cho sample cũ, nhưng phải ghi rõ bằng chứng thay thế |
| agy không trả tiền/model ảnh | Giữ “chưa biết”; giá cấu hình chỉ là ước tính. Bằng chứng gọi agy không được biến thành tên model ảnh tự suy đoán |
| Số tổng test Phase 3 chưa rõ | Bàn giao test summary có tên lệnh, số passed/failed/skipped, môi trường và phiên bản code tương ứng; không cộng số test từ nhiều thời điểm |

Đây là yêu cầu kiểm tra/tăng độ chắc của tool dựa trên báo cáo, chưa phải kết luận đã phát hiện lỗi trong code hiện tại.

## 7. Cache, bảo toàn chỉnh sửa và chuyển dữ liệu cũ

Báo cáo đã nêu lỗi AI chuẩn bị ghi đè storyboard/asset plan khi thư viện thay đổi, sau đó được sửa. Phải giữ hành vi bảo vệ chỉnh sửa thủ công và bản đã duyệt; không đưa lại phụ thuộc vào toàn bộ thư viện asset đang biến động.

Yêu cầu cho dữ liệu mới:
- Mỗi lần chuẩn bị dùng snapshot phiên bản brief, hồ sơ series/nhân vật, chính sách asset, schema/capabilities và prompt template liên quan.
- Sau khi chọn/tạo asset, giữ ID/hash cụ thể trong kế hoạch. Thêm một asset không liên quan vào thư viện không làm mọi cảnh cần dựng lại.
- Đổi character profile, style hoặc rig phải làm vô hiệu phần phụ thuộc đúng phạm vi. Không bỏ các đầu vào có ý nghĩa khỏi hash chỉ để tránh cache miss.
- Nếu đầu vào thay đổi nhưng đầu ra đã được người dùng sửa/duyệt, tạo đề xuất phiên bản mới hoặc trạng thái cần cập nhật; không ghi đè âm thầm và không trả cache cũ như còn phù hợp.
- Force phải chỉ rõ bước/phạm vi, lưu bản trước và hiển thị ảnh hưởng phê duyệt/chi phí. Không dùng force như giải pháp mặc định.
- Asset/rig đã dùng trong bản video cần có phiên bản bất biến để mở lại hoặc dựng lại đúng bản đó.
- Dữ liệu cũ thiếu trường mới có schema migration và mặc định tương thích; không làm dự án Phase 2/3 tự thay hình, gọi voice hoặc mất lịch sử.
- Actor cũ không xác định phải ghi chưa xác định; chỉ phân loại là thao tác thử khi có bằng chứng. Không vô hiệu hàng loạt duyệt thật vì một số asset test.
- Giao diện phổ thông không yêu cầu sửa JSON.

Có thể mở rộng dữ liệu đang có thay vì tạo trùng: channels/default.json, storyboard, asset plan/manifest, approvals_history.jsonl, logs/ai_ledger.jsonl, prepare/history và trạng thái job. Các cấu trúc character_profile, rig, research_opportunities, delivery/review là phần cần bổ sung hoặc ánh xạ.

## 8. Bộ nghiệm thu đợt tiếp

### Mốc đầu tiên — 10–15 giây chứng minh lõi
Topic mới → prompt pack → nhân vật/background/đạo cụ mới từ Antigravity → rig → chuyển động trong Craft. Không cần chờ hoàn thiện SEO hoặc Telegram để kiểm tra mốc này.

### Sample A — Dự án mới hoàn toàn
- Chủ đề khác mẫu tài chính ban đầu; một nhân vật chính, một nhân vật phụ, hai bối cảnh và đạo cụ có vai trò trong câu chuyện.
- Bộ hình kể chuyện tạo thật qua Antigravity; có job, prompt, tham chiếu, hash và nguồn cho từng asset.
- Chặn đọc thư mục hình mẫu; không xóa tài sản của người dùng. Cache bộ hình mới chưa có ở lần đầu, chạy lần hai phải dùng lại.
- Video 60–90 giây, 6–10 cảnh; tối thiểu ba chuyển động, hai biểu cảm, một tương tác nhìn thấy; audio đủ và project chỉnh sửa được.
- Khởi chạy bằng giao diện/entrypoint dùng chung. Không cần phiên Claude lập trình đứng ngoài sửa tay asset, dựng rig riêng hoặc viết thêm script riêng cho video trong lúc chạy bài nghiệm thu.
- Duyệt hình/nội dung bởi người thật hoặc dựng draft theo quyền đã ghi riêng; không sử dụng phê duyệt giả của tác nhân AI.
- Xem/nghe toàn bộ video; ghi lỗi theo scene/timecode.
- Sau Chặng 3, video được gửi, góp ý và duyệt thật qua Telegram.

### Sample B — Chứng minh thay topic/nhân vật
Dự án khác với nhân vật và bối cảnh mới, video 20–30 giây ít nhất ba cảnh. Dùng cùng code, chỉ thay dữ liệu/config. Nếu phát hiện lỗi chung, sửa ở module dùng chung và kiểm tra ảnh hưởng có mục tiêu.

### Sample C — Tiếp series
Một cảnh ngắn của tập tiếp theo dùng đúng phiên bản nhân vật của A, thêm đạo cụ/nền mới. Manifest thể hiện phần dùng lại có chủ đích; giữ nhận diện và không sinh lại hình đã có vô ích.

### Kiểm tra vận hành gắn với rủi ro còn lại
1. Sửa một câu và gọi voice thật: chỉ audio/cue/cảnh phụ thuộc làm lại; không sinh lại hình.
2. Sửa một asset thật: giữ lại bằng chứng selective rebuild hiện có làm baseline, bổ sung ca mới khi thay schema/rig ảnh hưởng đến hành vi đó.
3. Sửa biểu cảm qua Telegram: tác động đúng cảnh hoặc các cảnh có phụ thuộc thực; callback lặp không chạy thêm.
4. Không đổi: không có lượt sinh AI/hình/voice mới; ghi riêng thao tác gửi lại video hoặc chủ động refresh nguồn.
5. Source/range/cue: claim thiếu nguồn, duration ngoài khoảng chốt trước, cue gần đúng hoặc bị dời quá ngưỡng có trạng thái đúng; không sửa điều kiện để báo pass.
6. Duyệt: hash đổi, actor thử, callback cũ/sai chat và đề xuất revise lỗi thời không được nhận thành duyệt hợp lệ.
7. Khóa/job: đường gọi mới tôn trọng agy_slots mặc định 1; ngắt/tiếp tục không trùng job; không deadlock do slot cha/con.
8. Cache migration: thêm asset không liên quan không làm dựng lại toàn bộ; đổi profile có ý nghĩa làm đúng phần cần cập nhật; bản chỉnh tay không bị ghi đè.
9. Budget: repair/retry/fallback của backend mới đều được ghi ledger và chịu hạn mức. Tắt FreeLLMAPI thì đường agy còn dùng được.
10. Telegram gián đoạn có trạng thái gửi rõ; thiếu bot/chat thì đánh dấu mục chưa chạy, không ghi hoàn thành.

Dùng test hiện có làm baseline, chỉ thêm kiểm tra cho hành vi mới hoặc rủi ro thay đổi. Không yêu cầu dựng lại hàng loạt video cũ chỉ để tăng số bằng chứng.

## 9. Gói bàn giao và cách chứng minh

Mở rộng export_project.py để gói bàn giao có:
- Báo cáo đối chiếu yêu cầu với module thật và phiên bản code.
- Config mẫu không chứa bí mật; hướng dẫn cập nhật/khởi động/tiếp tục.
- Schema và quy tắc migration/policy asset; dữ liệu Sample A/B/C.
- Script/storyboard/asset plan/prompt pack/rig/manifest.
- Ảnh gốc Antigravity và project Craft chỉnh sửa.
- Video, preview, kết quả nghe/xem và lịch sử review.
- Log có chọn lọc: actual provider/model khi biết, job ảnh, lệnh Craft, voice, usage/chi phí, cache và Telegram. Che token/credential và thông tin không cần bàn giao.
- Test summary thực tế, lỗi/skip và giới hạn còn lại.
- Bảng phân biệt thao tác người dùng, AI lúc vận hành, AI lúc lập trình và mock.

Các tệp cần đối chiếu từ báo cáo Phase 3 khi bắt đầu: HUONG_DAN_PHASE3.md, config.example.json mục ai, channels/default.json, evidence/tests_log.txt, evidence/phase3/real_runs.md và evidence/phase3/selective_rebuild.md. Chúng được báo cáo là tồn tại, chưa được đọc trong lần cập nhật kế hoạch này.

Báo cáo từng chặng theo mẫu: năng lực dùng chung đã thêm → module thay đổi → đầu vào → công cụ chạy thật → đầu ra/bằng chứng → chi phí/thời gian → giới hạn còn lại. Không lấy số lượng test hoặc độ đẹp một sample làm đại diện cho việc đạt toàn bộ sản phẩm.

## 10. Lệnh giao việc tiếp theo cho Claude

“Đọc kế hoạch phiên bản 2 này và code Phase 3 hiện tại. Giữ lại UI bảy tab, agy headless, validate/revise/realign, budget/ledger, approvals theo hash, agy_jobs, agy_slots, selective rebuild và export đã có.

Bắt đầu bằng bảng đối chiếu module và xác nhận bằng chứng hiện có. Ưu tiên sửa chính sách asset của dự án/series mới và triển khai nhân vật AI có khớp. Tạo bằng chứng 10–15 giây: topic mới → Antigravity tạo bộ hình mới → Craft tạo chuyển động thật. Các bước phải thành năng lực dùng chung của tool.

Sau mốc đó mở rộng thành video kể chuyện nhiều cảnh; xử lý duration/cue/approval còn yếu; rồi cải thiện nghiên cứu cơ hội, thêm adapter FreeLLMAPI và tích hợp duyệt Telegram theo ba chặng.

Không viết lại những phần đã có, không tối ưu tiếp video mẫu cũ khi không giải quyết yêu cầu dùng chung, không đổi ngưỡng kiểm tra để mẫu đạt, không báo mock là chạy thật. Chỉ đánh dấu hoàn thành theo bằng chứng của từng tiêu chí.”

Các điều kiện cần cấp khi đến bước tương ứng: cấu hình model/đường gọi hoạt động, hạn mức ảnh/voice, nguồn dữ liệu nghiên cứu có quyền truy cập, bot token/chat Telegram cấu hình tại máy. Có thể hoàn thành phần độc lập trước; hạng mục thiếu điều kiện phải ghi blocked, không giả lập thành hoàn thành.

## 11. Chốt hoàn thành

Tool nhận topic mới và tùy chọn nhân vật/guideline, tự tạo bộ hình phù hợp chuyển động qua Antigravity, Claude lập kế hoạch và điều phối Craft, ghép giọng, gửi Telegram và xử lý góp ý theo phiên bản. Sample A/B/C chứng minh được tạo mới, thay dự án và tiếp series bằng cùng code.

Phase 3 hiện tại là nền để mở rộng. Nghiệm thu cũ không bị phủ nhận, nhưng không được dùng để thay thế bằng chứng cho nhân vật AI mới, nghiên cứu cơ hội SEO hoặc duyệt Telegram.