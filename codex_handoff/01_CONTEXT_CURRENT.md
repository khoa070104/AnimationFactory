# Ngữ cảnh hiện hành — đọc trước khi làm

## 1. Sản phẩm thật sự cần xây

**AnimationFactory là tool sản xuất hoạt hình để các AI CLI sử dụng. Người dùng là người định hướng và duyệt.**

Các câu chốt của người dùng:
> “Mục tiêu là tạo tool sản xuất video chứ k phải cứ optimize cái sample.”
> “Ko được gom only 1 chủ đề.”
> “Sau này tôi sẽ cho các cli như claude, or chatgpt or antigravity -> để nó dùng tool và tạo ra video hoạt hình.”

Đầu vào mong muốn:
- Topic, story guideline/định hướng kênh, người xem, thị trường/ngôn ngữ, thời lượng, phong cách và ngân sách.
- Hình/mô tả nhân vật chính; nếu chưa có, tool đề xuất và tạo.
- Tham khảo có thể giúp học cách kể bằng hình, không biến mọi dự án thành cùng một thể loại.

Luồng đích:
Topic → nghiên cứu cơ hội nội dung và nguồn → đề xuất góc kể → kịch bản → scene/shot → kế hoạch asset + prompt → Antigravity tạo nhân vật chính/phụ, background, đạo cụ → rig/pose/animation → ghép giọng/âm thanh → QA + preview → gửi Telegram để người dùng duyệt.

AI CLI làm đạo diễn/điều phối, đọc capabilities, gọi thao tác có cấu trúc, xem preview và sửa. AnimationFactory cung cấp công cụ tin cậy; web là nơi người dùng xem/góp ý/duyệt trên cùng dữ liệu.

“ChatGPT CLI” trong trao đổi là cách gọi mong muốn môi trường AI có thể dùng CLI/MCP; không phải bằng chứng tồn tại hay đã cài một sản phẩm có tên đó. Kiểm tra công cụ thực tế trên PC.

## 2. Quyết định kiến trúc hiện hành

- **Remotion làm bộ dựng chính. Craft là đường dự phòng.**
- VectorCraft/EffectCraft/FilmCraft là nền triển khai ban đầu. Giữ phần còn có ích và khả năng tương thích đã cam kết; không bắt mỗi lần dựng phải đi vòng qua cả ba app chỉ để chứng minh đã dùng.
- Giữ dự án, asset, giọng, cache, ngân sách, approvals và UI hiện có. Không xây lại web hoặc thêm dịch vụ điều phối mới cho Chặng 1.
- Một lõi điều khiển, CLI và MCP là adapter gọi cùng lõi. UI cũng phải dùng quy tắc lưu/khóa/duyệt tương thích.
- Storyboard cấp scene đang mở rộng thành shot. Scene giữ bối cảnh/trạng thái; shot điều khiển khung nhìn, trọng tâm, thời gian, bố cục.
- Lớp world gồm đối tượng trong thế giới; lớp screen gồm thứ được cố định theo màn hình. Xác định theo vai trò ngữ nghĩa, không mặc định mọi chữ hay mọi panel thuộc screen.
- Zoom/pan 2D không tạo ra góc quay thật mới. Muốn góc nhìn khác phải có asset phù hợp.

## 3. Chính sách ảnh và nhân vật

Người dùng đã phản đối việc tool mặc định tận dụng nhân vật/asset của video mẫu.

- Dự án mới: kế hoạch nội dung phải sinh ra yêu cầu hình ảnh thật; Antigravity tạo bộ ảnh phù hợp nhân vật/bối cảnh/đạo cụ.
- Dự án cùng series: tái dùng nhận diện và phiên bản asset có chủ đích, không trộn tùy tiện.
- Thư viện tài sản chỉ dùng khi brief/policy cho phép.
- Riêng hai sample Chặng 1 hiện tại được dùng lại asset Sample A để kiểm chứng camera/contract, với 0 ảnh mới. Đây không phải thay đổi mục tiêu sản phẩm.
- Không buộc mọi ảnh phải có một rig phức tạp. Có thể chọn rig, các tư thế vẽ sẵn, hoặc animation đơn giản theo yêu cầu cảnh và khả năng thật.
- Chữ tiếng Việt, số liệu, nhãn bảng/biểu đồ cần chính xác: dựng từ dữ liệu bằng code/vector, không giao mô hình ảnh viết chữ chính xác.
- Sinh ảnh mới luôn draft; phê duyệt gắn đúng file/hash/phiên bản. Không dùng tên người duyệt nhập tự do như bằng chứng xác thực danh tính.

## 4. Người dùng và AI chia việc

Người dùng: chiến lược kênh, giới hạn ngân sách, duyệt nội dung/phong cách và chất lượng cuối.
AI: nghiên cứu, lập kế hoạch, tạo prompt, gọi tool, kiểm tra, sửa thành phần chung và báo cáo.
Không bắt người dùng ra quyết định kỹ thuật thường nhật hoặc xác nhận lại việc đã ủy quyền. Hỏi khi có thay đổi phạm vi/chi phí/quyền truy cập thật sự cần quyết định.

Không tự coi “test pass” là người dùng đã duyệt. Không tự duyệt thay người dùng. Phân biệt phê duyệt kiểm thử với phê duyệt sản xuất.

## 5. Trạng thái gần nhất

- Repo public: https://github.com/khoa070104/AnimationFactory.git
- Bản review nguồn gần nhất: 677a84b8479d89f2647cb60e11b93718bc004ecc.
- **Chặng 1 đã có nền tảng nhưng chưa đủ điều kiện nghiệm thu hoàn tất tại bản review đó.**
- Có sáu nhóm lỗi nguồn và ba hạng mục kế hoạch chưa hoàn tất; xem 03.
- Có góp ý visual cho demo story v7; xem 04. Không được mặc định những góp ý này đã được sửa ở HEAD mới.
- Báo cáo triển khai nói 166 test Python + 22 test Node đạt. Review độc lập gần nhất chỉ xác nhận 5 test Python shot + 22 test Node cùng các ca tái hiện riêng; chưa chạy lại toàn bộ và chưa render hai sample từ đầu.
- Demo story đã có MP4; demo explainer mới có contact sheet trong phần bằng chứng này.
- Hai CLI độc lập và phiên MCP thực trong client chưa được nghiệm thu trọn vẹn.

## 6. Điều bắt buộc ở hợp đồng tool

- Công bố capabilities, schema/version, thao tác thực sự hỗ trợ; không hứa hành động chưa có.
- stdout JSON sạch; log stderr; trạng thái/exit code/job state nhất quán.
- Lỗi có code, đường dẫn field, scene_id/shot_id nếu liên quan, next_action.
- validate không gọi provider. estimate phân biệt dự toán với tiền thật, “không biết” với 0.
- Job dài có ID duy nhất, trạng thái bền vững, owner, retry/recovery; chạy lại không nhân đôi yêu cầu đang chạy.
- Khóa liên tiến trình bao trọn đọc–kiểm tra phiên bản–ghi; ghi nguyên tử. CLI/MCP/UI phải tuân thủ cùng quy tắc.
- Cache đúng các dependency thực dùng; asset bị mất/hỏng không được báo thành công hoặc tự gọi API phát sinh phí.
- Preview trả ảnh theo sự kiện, contact sheet, clip thấp phân giải và đường dẫn artifacts.
- Render theo snapshot được duyệt; thay nội dung/asset làm mất hiệu lực đúng phần liên quan.
- AI mới phải dùng được từ tài liệu + brief + đường dẫn dự án, không phụ thuộc trí nhớ của phiên xây tool.

## 7. Phạm vi trả phí và giới hạn hiện tại

Chặng 1: **0 ảnh mới và 0 lượt giọng trả phí**; dùng lại dữ liệu/asset được phép. Token của agent nghiên cứu/coding là khoản khác, không được báo tổng hệ thống bằng 0 nếu không đo được.

Không suy diễn ngân sách Sample A cũ thành quyền chi tiêu không giới hạn. Không tự thay nhà cung cấp, gửi Telegram hay publish video chỉ vì đang chuyển ngữ cảnh. Đường kết nối có sẵn không đồng nghĩa có ủy quyền gửi mọi nội dung ra ngoài.

Trạng thái thu hồi API key từng bị dán vào chat chưa có xác nhận. Gói này không chứa key; không in .env hay credential ra log.

## 8. Hướng dài hạn chưa được coi là xong

- Nghiên cứu SEO/xu hướng/cạnh tranh có dữ liệu, nguồn, ngày truy cập; thiếu dữ liệu phải nói rõ. Chỉ số Google không tự tương đương nhu cầu YouTube.
- Provider router: kế hoạch đề xuất thử FreeLLMAPI qua adapter cho việc nhẹ, giữ agy/fallback chất lượng; chưa có bằng chứng tích hợp/benchmark ở snapshot này. 9Router chưa là phụ thuộc bắt buộc.
- Telegram: xem bản video đúng phiên bản, callback đúng người/chat, duyệt/góp ý; chống duyệt nhầm bản cũ và gửi trùng khi retry.
- Chặng 2 chất lượng: tư thế, hướng nhìn, tương tác, điểm tiếp xúc, trạng thái vật, che khuất.
- Chặng 3 chất lượng: nhịp dựng, âm thanh nhiều lớp, giọng thật khi được duyệt, kiểm chứng trên nội dung khác nhau.

