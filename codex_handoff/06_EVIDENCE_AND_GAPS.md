# Chỉ mục bằng chứng và phần còn thiếu

## Repo và thư mục PC

- Root lịch sử: D:\AnimationFactory
- Repo: https://github.com/khoa070104/AnimationFactory.git
- Commit baseline review: 677a84b8479d89f2647cb60e11b93718bc004ecc.
- Tag đã thấy: chang0-baseline, chang1-done. Tên tag không phải quyết định nghiệm thu của reviewer.
- Repo không thay thế asset/voice/output cục bộ đã được bỏ qua Git.
- Không có quyền truy cập tự động từ phiên ChatGPT này sang ổ D: của PC.

Điểm vào repo (đã tồn tại tại commit review):
- README.md
- phase2/ACCEPTANCE_CHANG1.md
- phase2/PLAN_CHANG1.md
- phase2/CHANG1_BANG_NANG_LUC.md
- phase2/HUONG_DAN_AF.md
- phase2/evidence/chang1/
- phase2/examples/story_label.json
- phase2/examples/explain_process.json
- phase2/tools/af.py, af_core.py, sbstore.py, shots.py
- phase2/tools/export_remotion.py, build_remotion.py, layout.py
- phase2/remotion/ và phase2/remotion/tests/
- phase2/assets_mcp/
- phase2/tests/

Một số file/tên dự án lịch sử:
- tools/voice.py; phase2/tools/agy_jobs.py, prepare.py, approve.py, voice_project.py, produce.py.
- phase2/projects/video1_luong
- phase2/projects/video2_quy_khan_cap
- phase2/projects/ui_demo
- phase2/projects/sample_a_thuc_don_tuan/GOI_DUYET_SAMPLE_A.md
- AnimationFactory_Phase1_Evidence.zip
- AnimationFactory_Phase2_Acceptance.zip
- ACCEPTANCE_PHASE2_ADDENDUM.md
Đường dẫn chính xác của các file lịch sử phải đối chiếu PC, không tạo file mới chỉ vì tìm ở một vị trí chưa thấy.

## CLI đã được tài liệu hóa ở commit review

Chạy bằng Python, không giả định đã có executable tên af trong PATH:
    python phase2/tools/af.py capabilities
    python phase2/tools/af.py project_get --project NAME --what all
    python phase2/tools/af.py validate --project NAME
    python phase2/tools/af.py estimate --project NAME
    python phase2/tools/af.py artifacts --project NAME

Mutation/render (chỉ chạy trong việc đã được giao):
    python phase2/tools/af.py project_put --project NAME --storyboard-file F.json --expect-hash H
    python phase2/tools/af.py preview --project NAME
    python phase2/tools/af.py render --project NAME --draft
    python phase2/tools/af.py jobs --project NAME --job-id ID

Contract af/1; một số đường chưa thực hiện đúng contract như review đã nêu. Không có lệnh tự approve trong af ở bản đã đọc. Các form phê duyệt/API phía UI phải giữ vai trò chủ dự án.

Capabilities kèm --project quan trọng để biết tài sản thực tế dự án. Capabilities không kèm project có thể chỉ thấy nhân vật thư viện.

MCP: animation-factory-assets; trước đây đăng ký trong .mcp.json tại D:\AnimationFactory và D:\Documents\Workplace. Kiểm tra cấu hình thực tế và quyền client; không sao chép credential sang gói này.

## Video Chặng 1

Tên file đã nhận:
- demo_chang1_story_v2_draft.mp4
- demo_chang1_story_v3_draft.mp4
- demo_chang1_story_v4_draft.mp4
- demo_chang1_story_v5_draft.mp4
- demo_chang1_story_v6_draft.mp4
- demo_chang1_story_v7_draft.mp4

Thông số review: khoảng 17,045667 s, 1920×1080, H.264, 30 fps, AAC 48 kHz. v7 là bản giọng nháp gần im lặng.

SHA256 dùng nhận diện, không phải chữ ký xác thực:
- v2: 326bec846492a3e12776cafae3357168633c28e5090acf96874bbe86fd0e8f53
- v3: fe5ff5a15dc52e9aed96ea7670797565fdc82df2c2c084acfb3d46a745df9d0c
- v4 và v5: f9dc9bdc37842f47b3d1854acf965dfa9026751c848a2e73efa9108e9aa659e7
- v6 và v7: f0f076b61e1fe13a72b90ac7893038426c2d697199d60344df0596edbd4338fb

Ảnh đính kèm:
- image(20261019-191157).png: contact sheet trước/sau explainer.
- image(20261019-191205).png: contact sheet trước/sau story.

Báo cáo triển khai nêu explainer 16,8 s; chưa có MP4 explainer trong bộ file đã review. Khi chuyển PC, cần tìm file thật hoặc người dùng/Claude gửi link; đừng coi ảnh liên hệ là video đã xem.

Gói handoff không bao gồm các video này. Chỉ mục giúp tìm đúng bản trên PC hoặc tải từ Release được cung cấp sau.

## Video tham chiếu và Sample A

1. Video nhà ga “Người đợi chuyến cuối”
- Tên đính kèm: a19bbe11-9d6b-4eb6-89eb-db7911a7b1b2.mp4.
- Khoảng 60,116 s; 640×360, 30 fps.
- Mốc học cách kể: 18–26 s chiếc vé/nhân vật, 38–46 s hình ở cửa sổ, 51–60 s kết.
- Tông tối, đường viền rõ, chuyển động hạn chế nhưng lộ thông tin có chủ đích.

2. “Thiếu ngủ ảnh hưởng thế nào-.mp4”
- Khoảng 476,244 s; 1920×1080, 24 fps.
- 00:41–00:47 thao tác và phản hồi; 02:06–02:14 đồ thị/nhấn vùng; 04:30–04:36 so sánh mặt; 07:14–07:26 ẩn dụ “nợ ngủ”; 07:28–07:32 giường/não/pin.
- Học ngôn ngữ hình ảnh, không xác nhận nội dung y khoa hay quyền tái dùng tài sản.

3. sample_a_thuc_don_tuan_v17_preview.mp4
- Khoảng 92,630667 s, 1080p30.
- Có audio không im lặng; chưa có kết luận nghe tự nhiên hoặc xác nhận toàn bộ từng lời tại review này.

## Tài liệu gốc đi kèm

archive/AnimationFactory_Master_Plan.md
- Phiên bản 2, 18/10/2026; bản kế hoạch sau báo cáo Phase 3.
- Giữ nguyên nội dung nguồn. Craft-main trong văn bản đã bị quyết định Remotion-main thay thế.
- Giữ yêu cầu dài hạn về asset policy, research, router, Telegram, approvals.

archive/AnimationFactory_Tool_Cho_AI_CLI_KeHoach_NangCap.txt
- Bản giao việc v1, 20/10/2026.
- Nền của lộ trình chất lượng Chặng 1–3, chi tiết chín tiêu chí.
- Là kế hoạch, không bằng chứng mọi tính năng đã có.

Hai bản đã được đọc từ tài liệu lưu của cuộc chat và sao chép vào gói. Các kế hoạch chỉ được nhắc tên nhưng không tìm thấy bản nội dung không được giả vờ khôi phục nguyên văn.

## Phần chưa có hoặc chưa chứng minh

- HEAD/working tree hiện tại trên PC so với commit review.
- Bằng chứng đóng R1–R6 ở bản mới.
- Toàn bộ log 166 test trong môi trường reviewer; chưa có full render tái lập của reviewer.
- MP4 explainer và tiếng thật được người xem nghe duyệt.
- CLI thứ hai điều phối end-to-end và MCP qua phiên client thật tại trạng thái mới.
- Nguồn ảnh/tài sản và project cục bộ đầy đủ sau clone.
- Tích hợp FreeLLMAPI/9Router hiện có hay chưa; config giá và mô hình thực.
- Telegram gửi/duyệt đúng phiên bản trong vận hành thật.
- Research thực có số liệu SEO/trend/competition hay chỉ LLM phỏng đoán.
- Quyền/điều kiện giấy phép Remotion áp dụng cho người dùng khi đưa vào khai thác.
- Thu hồi key cũ và trạng thái đăng nhập hiện tại.

Những điểm này là việc kiểm tra theo nhu cầu, không phải yêu cầu dừng mọi công việc hoặc hỏi người dùng cả danh sách ngay đầu phiên.

