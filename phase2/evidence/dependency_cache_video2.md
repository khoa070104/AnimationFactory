# Bằng chứng cache và phụ thuộc (chạy trên bản sao)

Dự án nguồn: `video2_quy_khan_cap`, 9 cảnh, thời điểm 2026-10-18 18:25

| Tình huống | Chứng minh | Kết quả | Đạt |
|---|---|---|---|
| 0. baseline build of the copy | reference run | rendered 9/9, reused 0 | ✔ |
| 1. rerun, nothing changed | cache hit for every scene | rendered -; reused 9/9; API calls 0 | ✔ |
| 2. add an asset no scene uses | dependency tracking: unrelated asset | rendered - | ✔ |
| 3. edit the AI asset piggy_ai used by scene s06 | dependency tracking: used asset | rendered ['s06'] | ✔ |
| 4. move the character in scene s03 (layout only) | per-scene data dependency; no voice call | rendered ['s03']; API calls 0 | ✔ |
| 5. edit the wording of scene s02 (dry run) | approval gate + minimal recomputation | gate before re-approval: REFUSED; after: 1 scene to generate (123 chars, ~89 credits), 8 unchanged; API calls 0 | ✔ |
| 6. edit the shared action 'shrug' in the motion library | a shared-component change rebuilds exactly the scenes that use it | scenes using it: ['s01', 's02']; rebuilt: ['s01', 's02'] | ✔ |
| 7. edit the shared character rig | a rig change rebuilds every scene | rebuilt 9/9 | ✔ |
