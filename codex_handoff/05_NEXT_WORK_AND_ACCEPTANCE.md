# Việc tiếp theo và điều kiện nghiệm thu

## A. Hành động đầu tiên của Codex PC: đối chiếu, chưa tự sửa

Yêu cầu hiện tại là nhận ngữ cảnh. Đọc gói, kiểm tra chỉ đọc:
1. Đúng thư mục dự án, hướng dẫn AGENTS.md đang áp dụng.
2. Git HEAD, branch, status, remote; có thay đổi chưa commit của người dùng không. Không reset/clean/stash tự động.
3. So HEAD với 677a84b; xác định sáu lỗi R1–R6 đã được ai sửa chưa.
4. Tìm các tài liệu/asset/video thật trên PC; tên file không đủ chứng minh đúng bản, dùng hash/metadata nếu cần.
5. Kiểm CLI/dependency/login theo nhu cầu; không đọc ra giá trị secret.
6. Báo ngắn: đã hiểu gì, trạng thái nào có bằng chứng, thiếu gì thật sự ảnh hưởng việc kế tiếp.

Không hỏi lại mục tiêu Remotion hay tool vs sample đã chốt. Không mở đầu bằng đề xuất kiến trúc mới. Không tự chạy provider chỉ để kiểm kết nối nếu chưa được giao.

## B. Khi nhận lệnh tiếp tục Chặng 1

Ưu tiên:
1. R1 đóng gói clone sạch.
2. R2 khóa transaction/project/job và R4 status QA: tránh mất dữ liệu, dựng trùng và success giả.
3. R3 validate shot + R6 hợp đồng lỗi.
4. R5 visibility world/screen theo thời gian thực.
5. Hoàn tất P1 ảnh theo sự kiện và P2 progressive reveal trong đúng phạm vi đã hứa, hoặc ghi quyết định đổi scope.
6. Áp dụng góp ý visual V1–V5 ở phần chung.
7. Chạy lại hai sample hiện có, nghiệm thu từ phiên mới; không sản xuất video dài mới.

Đây là thứ tự đề xuất. Nếu dependency khác, ghi lý do đổi; tránh sửa rộng không liên quan.

## C. Nguyên tắc triển khai

- Đọc implementation trước, tận dụng cái có; không viết lại hệ job/approval/cache/UI.
- Không thay đổi tiêu chí để biến fail thành pass.
- Test phải đánh trúng lỗi, có bằng chứng đỏ-trước khi có thể tái hiện an toàn; không bắt mọi bug lịch sử phải có log đỏ nếu code cũ không còn chạy được.
- Test process thật cho lock; worker/provider giả cho phần không cần chi phí. Mô tả rõ mock hay real.
- Khi đủ bằng chứng, dừng mở rộng test tùy ý và hoàn tất bàn giao.
- Một writer lõi theo kế hoạch. Nếu dùng nhiều agent, chỉ trong quyền hiện có và môi trường cô lập phù hợp; không mặc định chạy agent song song.
- Lưu version/commit để rollback; không đè thay đổi của người dùng. Không push/publish chỉ vì repo public.
- Không hỏi lại quyền cho thao tác sửa/test đảo ngược nằm trong việc đã được giao.

## D. Bộ bằng chứng tối thiểu để chốt Chặng 1

| Mục | Bằng chứng đạt |
|---|---|
| Clone sạch | CLI khởi động theo tài liệu; không chép file ngầm từ máy tác giả |
| Ghi đồng thời | Hai process cùng revision không làm mất thay đổi; conflict có cấu trúc |
| Job | Yêu cầu trùng không spawn hai worker; ID/state/owner nhất quán |
| Shot | Cue/end/order/ease/focus sai bị chặn trước render, lỗi định vị đúng |
| QA | Fail phản ánh đúng qua CLI, worker và adapter; vẫn xem được draft để sửa |
| Visibility | screen không ẩn nhầm, world đúng policy và khoảng thời gian |
| JSON | Đầu vào hỏng vẫn lỗi JSON sạch; exit code và cost schema ổn định |
| Preview | Contact sheet + clip + ảnh trước/lúc/sau sự kiện có đường dẫn |
| Đồ họa | So sánh/highlight và vẽ dần theo data, không chỉ pop ảnh |
| Visual | Hai sample xem được, góp ý camera/callout/subtitle có bằng chứng |
| Tổng quát | Đổi actor position/nhãn/câu bằng data; không sửa renderer riêng sample |
| Cache/cost | Chạy lại không đổi tái dùng đúng; không provider ngoài phạm vi |
| Phiên mới | Agent mới chỉ có docs/brief/project tự validate→preview→sửa data→render |
| Client thứ hai/MCP | Thử thật khi đủ quyền; nếu bị chặn ghi CHƯA KIỂM CHỨNG, không gọi là đạt |

Khóa tiêu chí “0 ảnh mới, 0 paid TTS” cho Chặng 1. Nếu cơ chế gọi provider có bất ngờ, dừng đúng chỗ và báo nguyên nhân, không tự tăng ngân sách.

## E. Báo cáo cuối đợt

- Commit/dirty state, phần code chung thay đổi.
- Bảng R1–R6, P1–P3, V1–V6: fixed / deferred theo scope / unverified; link bằng chứng.
- Test chạy thật, môi trường, giới hạn.
- MP4 của hai sample, contact sheet, project/storyboard data, artifact hashes.
- Số lượt provider/credit biết được; unknown nếu không đo.
- Việc cần người dùng duyệt và bước kế tiếp.
Không dùng tổng số test làm kết luận chất lượng duy nhất.

## F. Sau khi Chặng 1 đủ điều kiện

Chặng 2 chất lượng:
- Asset nhìn đúng góc/pose, biểu cảm/hướng nhìn.
- Ngồi/với/chạm/cầm/đặt theo mục đích cần thiết.
- Điểm tiếp xúc và trạng thái vật, che khuất foreground/background.
- Biểu diễn khả năng trong capabilities để AI không hứa quá renderer.
- Sample mới để chứng minh tái sử dụng, chỉ sinh ảnh/giọng trong ngân sách được duyệt.

Chặng 3 chất lượng:
- Voice timing thật, nhịp nhấn/nghỉ/chuyển shot, nhiều lớp audio.
- Hai đoạn khác nội dung khoảng 20–35 s theo bản kế hoạch chất lượng.
- Hoàn thiện vòng preview–review và Telegram khi kết nối được.
Nghiên cứu SEO/router/Telegram trong Master Plan vẫn là backlog sản phẩm; đối chiếu mã mới để không xây trùng.

