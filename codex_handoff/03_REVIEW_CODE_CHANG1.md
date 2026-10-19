# Review nguồn Chặng 1 — baseline chưa nghiệm thu

Repository: https://github.com/khoa070104/AnimationFactory
Commit đã review: 677a84b8479d89f2647cb60e11b93718bc004ecc
Không khẳng định các lỗi dưới đây còn tồn tại ở một commit mới chưa kiểm.

## Phạm vi bằng chứng

Review trước đã đọc mã, contact sheet và chạy:
- python -m unittest discover -s phase2/tests -p test_shots.py -v — 5 test đạt.
- node --test phase2/remotion/tests/*.test.mjs — 22 test đạt.
- Ca tái hiện cô lập cho các lỗi dưới đây, không gọi provider.

Chưa chạy lại toàn bộ 166 test Python; chưa render lại hai video từ đầu. Clone thiếu file bắt buộc, môi trường review Linux không có bộ Craft Windows. Ca mock/AST/stub chỉ chứng minh hành vi đã nêu, không phải render end-to-end.

## R1 — clone sạch không khởi động CLI

Lệnh:
    python phase2/tools/af.py capabilities

Kết quả: FileNotFoundError do thiếu phase2/style/tokens.json.
.gitignore có **/*token* nên loại nhầm file design token. p2_svg.py đọc file này khi import; CLI chết trước khi kiểm cấu hình máy.

Nguồn:
- https://github.com/khoa070104/AnimationFactory/blob/677a84b8479d89f2647cb60e11b93718bc004ecc/.gitignore#L6
- https://github.com/khoa070104/AnimationFactory/blob/677a84b8479d89f2647cb60e11b93718bc004ecc/phase2/tools/p2_svg.py#L5

Sửa chung:
- Đưa design token cần thiết vào Git, thu hẹp ignore credential.
- Tài liệu rõ dependency/bước bootstrap; capabilities không nên chết vì tài sản tùy chọn của backend khác.

Nghiệm thu: từ clone mới, cài đúng dependency theo tài liệu, capabilities trả JSON hợp lệ; không “vá tay” từ working tree cũ để che lỗi đóng gói.

## R2 — hai CLI có thể ghi đè hoặc dựng trùng

project_put kiểm expect_hash trước lưu nhưng không khóa bao trọn check–write.
sbstore.save đọc/validate/tăng version/ghi trực tiếp không là một transaction nguyên tử.

Ca hai process thật, đồng bộ ở validator giả:
- Hai kết quả đều ok.
- Cả hai tăng version 1 →2.
- Chỉ còn thay đổi của một process; thay đổi còn lại mất.

_spawn kiểm job đang chạy rồi ghi đăng ký không nguyên tử. Job ID dựa thời gian đến giây.
Ca worker giả (không render/provider):
- Hai yêu cầu đồng thời → hai lần khởi chạy.
- Cùng job_id → còn một file job, không phản ánh hai process.

Nguồn:
- https://github.com/khoa070104/AnimationFactory/blob/677a84b8479d89f2647cb60e11b93718bc004ecc/phase2/tools/af_core.py#L131
- https://github.com/khoa070104/AnimationFactory/blob/677a84b8479d89f2647cb60e11b93718bc004ecc/phase2/tools/sbstore.py#L38
- https://github.com/khoa070104/AnimationFactory/blob/677a84b8479d89f2647cb60e11b93718bc004ecc/phase2/tools/af_core.py#L230

Sửa chung:
- Khóa liên tiến trình theo dự án, cùng quy tắc cho CLI/MCP/UI và writer liên quan.
- Check expected revision/hash + commit version/file trong cùng khóa; file tạm + thay nguyên tử.
- ID duy nhất, đăng ký job nguyên tử, khởi chạy gắn đúng bản đăng ký; recovery khi spawn thất bại.
- Preview đồng bộ cũng phải tuân thủ khóa/quy tắc snapshot, không là cửa đi vòng.

Nghiệm thu:
- Hai writer cùng expected hash: đúng một thành công, còn lại conflict rõ; không mất dữ liệu.
- Hai yêu cầu render trùng cùng lúc: một job hoạt động, lần kia trả job đang có hoặc trạng thái busy đúng hợp đồng.
- Không dùng chỉ thread test để chứng minh khóa liên process.
- Không kết luận “đã có khóa agy” nên lớp project/render tự an toàn: đây là hai đường khác nhau.

## R3 — validator bỏ lọt thời gian shot và kiểu focus

Ca đã kiểm ở pure functions:
- Cue “late” ở 4 s đứng trước “early” ở 1 s không bị chặn → khoảng [4,1].
- end < start vẫn qua, sinh key camera sai thứ tự.
- end là cụm không có trong lời qua validator rồi resolver lỗi.
- ease dài quá khoảng tới shot sau làm key camera chồng/sai thứ tự.
- focus: [x,y] được validator nhận nhưng resolver xử lý như key, TypeError.
- Thời gian metadata dùng cho hide không tôn trọng end trong một số đường.

Nguồn:
https://github.com/khoa070104/AnimationFactory/blob/677a84b8479d89f2647cb60e11b93718bc004ecc/phase2/tools/shots.py#L28

Sửa chung:
- Kiểm cấu trúc, kiểu, giá trị hữu hạn trước.
- Sau resolve cue → giây, kiểm tất cả start/end, duration cảnh, thứ tự, overlap/gap.
- Chính sách ease và gap phải rõ; không âm thầm bỏ end sai.
- Focus theo tọa độ hoặc target object phải có schema và resolver tương ứng.
- Lỗi có scene_id/shot_id/field, không chỉ chuỗi thông báo.

Nghiệm thu: các ca trên fail đúng lỗi trước render; shot hợp lệ qua; scene không có shots vẫn giữ tương thích ngược. Phát hiện cue thiếu không được tạo giọng trả phí để “thử cho biết”.

## R4 — QA fail nhưng preview/job báo success

build_remotion.build() có thể trả False, nhưng preview vẫn:
    {"status":"ok","checks_passed":false}

CLI có thể exit 0; worker ghi succeeded. AI điều phối sẽ tưởng video đạt.

Nguồn:
https://github.com/khoa070104/AnimationFactory/blob/677a84b8479d89f2647cb60e11b93718bc004ecc/phase2/tools/af_core.py#L285

Sửa: chuẩn hóa needs_changes/error, exit code và job state tương ứng; trả danh sách QA lỗi và next_action. Có thể giữ artifact nháp để xem vấn đề.

Nghiệm thu: cùng ca QA fail phải phản ánh thống nhất qua core, CLI, worker, MCP. Test đường thành công và thất bại, không chỉ assert trường checks_passed.

## R5 — focus isolation tự ẩn nội dung cần giữ

Đường export gán hide cho nội dung trúng vùng camera nhưng không xét space:screen.
Ca chạy đúng khối export với dữ liệu tổng hợp:
- Nhãn screen vẫn nhận hide.
- Shot end ở giây 1, shot sau ở 4; camera đã về rộng nhưng nhãn bị ẩn đến 4.

Nguồn:
https://github.com/khoa070104/AnimationFactory/blob/677a84b8479d89f2647cb60e11b93718bc004ecc/phase2/tools/export_remotion.py#L142

Sửa:
- Giữ semantics world/screen.
- Ẩn trong thời gian thực của shot.
- Cho data mô tả visibility có chủ đích; không làm nhân vật/vật biến mất để chữa bố cục một cách ngầm định.

Nghiệm thu: nhãn screen ổn định, nội dung world ẩn/hiện đúng policy và đúng start/end; clip/ảnh mốc ở trước–trong–sau khoảng ẩn.

## R6 — đầu vào sai phá hợp đồng JSON

Ca:
    python phase2/tools/af.py call validate --json '{broken'
Ném JSONDecodeError, stdout không là lỗi JSON chuẩn.

Tên dự án New-Video: lớp ngoài nhận nhưng lớp tạo dự án chỉ nhận quy tắc khác, ValueError lọt ra ngoài.

Hàm suy vị trí lỗi từ regex giả định scene ID bắt đầu bằng s. Scene intro mất scene_id, shot_id, code cụ thể.

paid_calls_this_run có đường là số, có đường là object.

Nguồn:
- https://github.com/khoa070104/AnimationFactory/blob/677a84b8479d89f2647cb60e11b93718bc004ecc/phase2/tools/af.py#L63
- https://github.com/khoa070104/AnimationFactory/blob/677a84b8479d89f2647cb60e11b93718bc004ecc/phase2/tools/af_core.py#L57

Sửa:
- Chuẩn hóa parse/file/input exceptions ở boundary CLI/MCP.
- Một quy tắc project ID, validate trước mutation.
- Validator trả lỗi cấu trúc từ đầu; không parse regex từ prose để tạo identity.
- Một schema cho số lượt trả phí/chi phí; unknown riêng, không nhầm 0.

Nghiệm thu: JSON hỏng, file mất, project name sai, scene intro + shot lỗi đều cho JSON hợp lệ, exit/status đúng và không mutation ngoài ý muốn.

## Ba hạng mục còn thiếu so với kế hoạch

P1. Preview đang chụp giữa mỗi shot, chưa có ảnh trước–lúc–sau sự kiện.
P2. compare/highlight có; chưa chứng minh đường/thanh vẽ dần theo dữ liệu. Pop một ảnh chart không tương đương progressive reveal.
P3. CLI thứ hai và MCP trong client thật chưa nghiệm thu. Test JSON-RPC trực tiếp/subagent độc lập không thay thế kiểm nối qua client.

Không thêm hạng mục lớn mới chỉ để làm đẹp checklist. Nếu một mục được đổi phạm vi, phải ghi quyết định rõ, không âm thầm đánh dấu xong.

