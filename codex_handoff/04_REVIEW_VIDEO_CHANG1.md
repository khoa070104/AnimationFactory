# Review hình ảnh Chặng 1

## Phạm vi đã xem

Đã có sáu file demo_chang1_story_v2/v3/v4/v5/v6/v7_draft.mp4 và hai contact sheet story/explainer.
Story MP4 khoảng 17,046 s, 1920×1080, 30 fps; v7 có audio gần im lặng. Không coi là đã kiểm giọng thật.

Review trước dùng chuỗi khung hình theo thời gian:
- Khoảng 30 khung phân bố từ đầu đến cuối.
- Khung dày hơn ở entry, pan sang Linh, cut sang Tuấn.
- So sánh một số khung cùng mốc giữa v2/v3/v4/v7.
Đây là kiểm tra khung/chuỗi thời gian, không lời xác nhận đã nghe và xem phát liên tục mọi bản.

v4 và v5 trùng byte; v6 và v7 trùng byte theo SHA256. Đổi tên file không chứng minh sửa video.
Chưa nhận MP4 explainer trong bộ này; contact sheet không đủ đánh giá nhịp chuyển động của explainer.

## Điểm đã thể hiện được

- Có toàn cảnh → chi tiết quan trọng → phản ứng từng người → trở lại rộng.
- Nhận diện nhân vật nhất quán.
- Chữ nhìn chung đọc được.
- Phụ đề giữ ở lớp màn hình khi camera đổi.

Những điểm này cho thấy shot/camera đang hữu ích. Chưa đủ để đóng các lỗi điều khiển/validation/concurrency của review nguồn.

## Góp ý cụ thể trên story v7

### V1 — 02,8–06,2 s: nhãn không rõ thuộc chiếc túi

Kịch bản nhắc nhãn trên túi, nhưng hình là một tấm thẻ lớn lơ lửng ở tường. Người xem khó hiểu quan hệ vật–nhãn.

Yêu cầu tool:
- Phân biệt nhãn gắn với vật và graphic callout giải thích.
- Nếu chưa có binding vật lý, callout cần đường chỉ/quan hệ hình ảnh rõ.
- Tương tác/binding vật thật có thể thuộc Chặng 2; không làm một asset-specific hack chỉ cho chiếc túi này.

### V2 — cùng khoảng: dấu tick xanh lệch ý nghĩa

Cảnh nói nhầm túi nhưng tick xanh thường gợi đúng/đã hoàn thành.
Tool cần ngữ nghĩa icon/trạng thái từ data: neutral/notice/correct/error hoặc không icon. Không mặc định tick xanh cho mọi nhãn.

### V3 — khoảng 06,15–06,65 s: đường camera đi qua vùng ít thông tin

Nhãn biến mất; camera đi qua tường/cốc/đèn trước khi phản ứng Linh vào vị trí rõ, trong khi phụ đề đã nói đến phản ứng.
Tool cần cho chọn cut hoặc di chuyển camera có chủ đích. Điểm đến phải có mặt đúng beat cần xem; không mặc định mọi shot đều tween qua một đường dài.

Nghiệm thu bằng mốc trước/lúc/sau cue và clip; không chỉ ảnh cuối chuyển động.

### V4 — khoảng 06,85–09,1 s: framing phản ứng còn yếu

Headroom nhiều; bàn/đèn cạnh tranh với mặt.
Camera shot phản ứng cần face/head box + khoảng nhìn, không chỉ bbox toàn thân. Thay vị trí/kích thước nhân vật bằng dữ liệu vẫn phải dựng đúng.

### V5 — khoảng 13,8 s: phụ đề bỏ một từ cuối

Cụm “hàng xóm” bị tách, riêng “xóm.” ở đoạn sau.
Cần chia theo cụm nghĩa, cân lại cụm cuối và cảnh báo từ lẻ quá ngắn, có cho phép ngoại lệ khi người viết chủ ý nhấn.
Không sửa bằng hard-code riêng câu hiện tại.

### V6 — hướng nhìn/tư thế chưa thể hiện đầy đủ lời kể

Lời “quay sang nhìn Tuấn” chưa được nhìn thấy rõ; mặt phần lớn vẫn hướng trước.
Đây là năng lực gaze/pose thuộc Chặng 2. Planner phải biết giới hạn hiện có, tránh viết hành động mà renderer chưa thể hiện được hoặc phải báo thiếu asset/pose.

## Phạm vi sửa phù hợp Chặng 1

Tập trung V1 theo dạng callout rõ nghĩa, V2, V3, V4, V5 trong phần dùng chung.
V6 và tương tác vật lý phức tạp chuyển Chặng 2 có ghi rõ.
Không thêm lip-sync, nhạc, giọng trả phí hay ảnh mới để chốt Chặng 1.

Ca chống “vá sample”:
- Đổi vị trí hai nhân vật bằng dữ liệu.
- Đổi chiều dài nhãn và một câu phụ đề.
- Chạy lại, camera/callout/text vẫn đúng.
- Mã dùng chung không có nhánh theo project_id/scene_id/tên Tuấn hoặc Linh để ép output.

## Cách gửi video cho lần review sau

Gửi MP4 mới nhất của mỗi sample, gắn commit/tag và storyboard hash; nếu cần so sánh thì thêm một bản before.
Có thể dùng GitHub Release hoặc đính kèm. Không cần đưa mọi bản nháp gần giống nhau vào Git.
Ghi rõ silent draft hay giọng thật, thời lượng/FPS và các mốc cần kiểm.

