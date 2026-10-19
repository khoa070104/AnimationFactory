# AnimationFactory — bàn giao ngữ cảnh cho Codex trên PC

Bản tổng hợp: 20/10/2026 theo ngày ghi trên tài liệu giao việc; phiên làm việc có thể hiển thị 19/10 theo UTC.
Mã nguồn được review gần nhất: `677a84b8479d89f2647cb60e11b93718bc004ecc`.
Repository: https://github.com/khoa070104/AnimationFactory.git

## Dùng gói này

1. Giải nén để có thư mục `D:\AnimationFactory\codex_handoff`.
2. Mở chính dự án `D:\AnimationFactory` trong Codex trên PC.
3. Dán nội dung `START_PROMPT.txt` vào một phiên mới.
4. Codex đọc các tài liệu dưới đây, rồi đối chiếu với mã và file thật trên PC. Không phải tải lại hay xây lại dự án chỉ vì đổi AI.
5. Sau khi Codex báo đã hiểu và chỉ ra chênh lệch, giao công việc tiếp theo dựa trên trạng thái thực tế.

Gói này chỉ chuyển ngữ cảnh; không sửa mã, không đăng ký MCP, không cấp quyền chi tiêu và không tự chạy pipeline.

## Thứ tự đọc bắt buộc khi bắt đầu

- `CURRENT_STATUS.md`: checkpoint mới nhất; kiểm ngày và đối chiếu Git.
- `01_CONTEXT_CURRENT.md`: mục tiêu, nguyên tắc và kiến trúc hiện hành.
- `02_HISTORY_DECISIONS.md`: tiến trình, điều đã đổi, điều không được làm lại.
- `03_REVIEW_CODE_CHANG1.md`: sáu nhóm lỗi tại commit đã review và cách nghiệm thu.
- `04_REVIEW_VIDEO_CHANG1.md`: góp ý hình ảnh có mốc thời gian và giới hạn đánh giá.
- `05_NEXT_WORK_AND_ACCEPTANCE.md`: thứ tự xử lý sau khi nhận việc.
- `06_EVIDENCE_AND_GAPS.md`: đường dẫn, bằng chứng, phần chưa có.
- Hai tài liệu trong `archive/`: đọc phần liên quan khi cần chi tiết dài hạn; không áp dụng mù quáng kế hoạch cũ.

`AGENTS_SNIPPET.txt` là đoạn đề xuất để hợp nhất vào AGENTS.md hiện có, nếu người dùng muốn Codex luôn nhớ các quy tắc cốt lõi. Không ghi đè AGENTS.md sẵn có. Không cần nhét toàn bộ lịch sử vào AGENTS.md.

## Cách hiểu độ tin cậy

- **Yêu cầu người dùng**: mục tiêu/ràng buộc đã nêu trong cuộc chat.
- **Claude báo cáo**: kết quả do agent triển khai báo lại; cần xem bằng chứng tại đúng phiên bản.
- **Review đã ghi nhận**: kiểm tra mã/ca thử/khung hình đã thực hiện trong phiên review trước. Không đồng nghĩa mọi thứ ở HEAD hiện tại đã được kiểm.
- **Đề xuất/chưa chứng minh**: hướng phát triển hoặc phần chưa có bằng chứng đầy đủ.

Số lượng test tăng theo từng bản là các mốc lịch sử; không cộng chúng lại. “Test xanh”, tên tag “done”, ảnh chụp hoặc thông báo của agent không thay thế nghiệm thu sản phẩm.

## Giới hạn của việc chuyển ngữ cảnh

Đây là bản bàn giao có cấu trúc, không phải bản xuất nguyên văn toàn bộ cuộc chat. Gói giữ mục tiêu, quyết định, công việc, lỗi, bằng chứng và câu hỏi còn mở; không chứa mọi câu trao đổi.

Phần giải đề Java/CSD201 được loại khỏi nội dung bàn giao theo yêu cầu người dùng quay lại AnimationFactory.

Không đóng gói mã nguồn, file .env, khóa API, video hay toàn bộ log. Mã lấy từ repo/working tree; video và asset cần có ở PC hoặc được gửi thêm. Các đường dẫn Library/Claude trong lịch sử không mặc nhiên truy cập được từ Codex PC.

Nếu cần lưu từng câu và mọi file đính kèm, giữ thêm bản xuất cuộc chat gốc. Không có cơ chế nào chỉ bằng một bản tóm tắt có thể bảo đảm giữ nguyên mọi chi tiết.

## Thứ tự ưu tiên khi thông tin mâu thuẫn

Chỉ đạo mới nhất của người dùng → dữ liệu/mã/log tại phiên bản đang làm → bản trạng thái hiện hành được đối chiếu → lịch sử và kế hoạch cũ. Một báo cáo mới không tự bác bỏ một lỗi cũ: cần bằng chứng lỗi đã hết.

Hai hệ “Phase 1–3” và “Chặng 1–3” nói về hai giai đoạn phát triển khác nhau. Chặng 1 hiện tại là hợp đồng điều khiển + shot/camera/bố cục, không phải dựng lại Phase 1.

## Sau mỗi phiên Codex

Cập nhật ngắn: commit/working tree, đã sửa gì, test thật nào chạy, file đầu ra, chi phí biết được, phê duyệt còn chờ, bước kế tiếp. Giữ nguyên báo cáo review cũ làm bằng chứng lịch sử, ghi rõ lỗi nào đã đóng tại commit nào.

Nguồn hướng dẫn AGENTS.md: https://developers.openai.com/codex/guides/agents-md
Codex có cơ chế đọc AGENTS.md theo phạm vi thư mục. Nên dùng file này cho quy tắc ngắn và chỉ dẫn đọc tài liệu; không coi nó là nơi tự động nạp không giới hạn mọi tài liệu được liên kết.

