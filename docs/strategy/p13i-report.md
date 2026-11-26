# P13i — bong bóng cờ lê và cổng ghi cấp nhà chính (26/11/2026)

Nhánh `p13i` (tách từ `p7-live-fixes` @ `bb250e3`, đã có P13h). **Chưa chạy thật**: không bật máy, không gọi `adb.exe` / `ldconsole.exe`. Kiểm bằng test, ảnh chủ dự án gửi, và đọc ảnh / log đã lưu của cây chính (chỉ đọc).

## ⚠ Cần chủ dự án xem: cấp thật của #2/#3 có thể là 6, không phải 7

Đề bài nêu #2/#3 đọc đúng cấp 7 lúc 15:14 / 15:17 rồi bị ghi đè thành 6. Phần "bị ghi đè không qua kiểm tra" đúng. Phần "7 là đúng" thì log không ủng hộ:

- Màn nâng cấp nhà chính báo cấp **6** cả trước và sau lần đọc 7: #2 lúc 12:53, 16:33, 19:30; #3 lúc 13:36, 16:47, 19:44 (`Thieu dieu kien (cap 6) -> Nhay`). Lần 16:32 của #2 mở đúng nhà chính (huy hiệu khớp 0,99).
- `screen_level` đọc được 81/89 màn nhà chính đã lưu (8 màn còn lại trả rỗng); mỗi kiểu màn khác nhau soi bằng mắt đều đúng số (gồm một màn cấp 7, một màn cấp 6).
- Bộ đọc avatar từng cho "7" sai: ảnh bảng Chỉ huy của #2 lúc 25/11 20:46 ghi cấp **5**, trong khi bot đang lưu 7 và hạ về 5 lúc 21:00. P13d-4 cũng sinh ra vì một lần "7" sai (#5).

Không có ảnh bảng Chỉ huy lúc 15:14 nên chưa kết luận được. Với luật mới, nếu #2/#3 đang lưu 7 mà màn nâng cấp tiếp tục báo 6 thì sau **2 lần** sẽ hạ xuống 6 kèm WARNING (đúng luật đề bài cho phép). Hiện state đang lưu 6 và bản này không tự đổi lại 7. **Nhờ mở game #2/#3 xem cấp thật.** Nếu là 7 thì `screen_level` đọc sai trên máy đó và cần ảnh màn nâng cấp để sửa.

Luật +1 từ một lần đọc (giữ nguyên theo P13d) chính là đường mà một số "7" sai có thể lọt vào. Nếu kết quả kiểm là 6, nên cân nhắc đòi 2 lần đọc cả khi tăng từ bảng avatar.

## 1. Bong bóng cờ lê

Nhận diện (`bot/wrench.py`, hàm thuần). Template `templates/build/wrench_bubble.png` 36×36 cắt sát vòng tròn tại (74..109, 265..300) của ảnh chủ gửi, không có điểm đỏ nào của khung khoanh tay. Tâm bong bóng đo được là **(92, 283)**; y≈255 trong đề bài ứng với mép trên khung đỏ.

Ứng viên là mảnh màu kem, phải qua cả bốn lớp:

| Lớp | Ngưỡng |
|---|---|
| Hình giống cờ lê ở một trong các góc −30°…+5° (bong bóng lắc) | ≥ 0,82 |
| Vòng vàng quanh biểu tượng | ≥ 45 % điểm trên vòng |
| Lòng đĩa tối mờ, không chói | ≥ 70 % điểm |
| Khớp template đã xoay đúng góc, tỉ lệ 0,8–1,42 | ≥ 0,46 |

Đo trên 29.993 khung 540×960 đã lưu (17–26/11): 180 khung có kết quả, 46 vị trí khác nhau soi bằng mắt đều là cờ lê thật, **không thấy khớp nhầm**; ~7 ms/khung. Chỉ dùng template thì không đủ: bong bóng trong mờ và camera thu nhỏ làm điểm khớp xuống 0,45–0,55. Vệt đạn trong trận là thứ gần khớp nhầm nhất (hình tới 0,81).

Giới hạn: bong bóng bị lớp khác che (mũi tên xanh hướng dẫn, bảng "0%", hạt sáng) có thể bị bỏ sót. Mọi bong bóng thật trong kho ảnh đều nằm trên cùng một kiểu công trình ở đỉnh có đèn đỏ, nên **chưa kiểm được bong bóng trên nhà khác**.

Luồng (`bot/modules/upgrade.py`):

- `wrench_upgrades`: còn thợ rảnh theo `build.max_builders` của máy → bấm bong bóng → `build.upgrade_here` (chỉ "Tăng cấp" / "Nhảy" / nút "Miễn phí"; không thêm nút nào mới).
- Gắn đầu tiên ở `upgrade.run`, giữa các công trình của `hq_chain`, trong lúc lướt thành của `upgrade_resource`, và đầu `construct.run` (khi `modules.upgrade` bật). Nhánh fill của runner chạy `upgrade` trước nên đi qua đường này, không phải sửa runner.
- Ưu tiên nhà chính: bong bóng ngay trên huy hiệu nhà chính. Huy hiệu hiếm khi khớp (trên ảnh chủ gửi chỉ 0,35–0,51), nên khi không thấy thì `upgrade.run` đưa camera về nhà chính một lần (thế giới → thành phố) và coi giữa màn là nhà chính. **Chi phí:** thêm một chuyến ~vài giây, và `goto_hq` sau đó có thể đi thêm chuyến nữa.
- Bấm mà không ra menu / màn nâng cấp (`none`) → tọa độ vào danh sách đen của lần ghé ngay (`tapguard`). Ra màn nhưng không nâng được → không bấm lại trong cùng lượt gọi, 2 lần thì vào danh sách đen; tối đa 3 lần bấm hỏng mỗi lượt gọi.
- Tắt được bằng `build.wrench: false`.

Chưa biết trên máy thật: bấm bong bóng mở thẳng màn nâng cấp hay mở menu công trình (`upgrade_here` xử lý cả hai).

## 2. Không ghi giảm `hq_level` từ một lần đọc

Cổng duy nhất `bot/hqlevel.py` (`record`). `judge_hq` / `note_hq` chuyển sang đây, `observe` vẫn giữ tên cũ.

- Chưa biết / bằng / +1: ghi như P13d. Nhảy >1: cần 2 lần đọc có nhãn trong cùng một đợt.
- Giảm: cần ≥ 2 lần đọc khớp nhau từ màn chi tiết (bảng avatar có nhãn, hoặc màn nâng cấp có `title_hq`), trong một đợt hoặc hai lần mở màn cách nhau ≤ 24 giờ (fact `hq_low_pending`). Một lần đọc cao hơn hoặc khác giá trị chen vào thì đếm lại. Ghi thì log `WARNING ... HA cap` kèm máy, cấp cũ, cấp mới, nguồn.
- "Cấp đang lưu" = số lớn hơn giữa `state.json` và `memory.db`.
- Các chỗ ghi đã đi qua cổng: `observe.read_hq`, `build.upgrade_here`. Lần ghi `cap` khi `hq_cap` ở `upgrade.hq_chain` **đã bỏ** (một lần đọc nhầm 33 sẽ khóa cấp 30 vĩnh viễn; giá trị đọc được đã qua cổng trong `upgrade_here`). `Runner.facts_to_copy` không còn chép giá trị thấp hơn từ state sang trí nhớ.

## Cổng kiểm tra

- `python -m pytest -q`: 1482 pass, 182 skip (skip vì ảnh fixture / ảnh chủ gửi chỉ có trên cây chính); trong đó 46 test mới của P13i (45 trong 2 file mới, 1 thêm vào `test_p13d_hq_read.py`).
- `ruff check`, ruff cho mã cũ (E9,F63,F7,F82), `mypy`, `lint-imports`: sạch. `main.py --check`: 16/261 ảnh mẫu thiếu (16 như trước).
- Worktree sạch: 3 test trong `test_p13b_cham_do_khong_doi.py` (có từ trước) cần `data/owner-feedback/p13/` chép từ cây chính; test P13i chỉ dùng file đã commit (`tests/fixtures/p13i/wrench_city.png`, `git add -f`).

File: `bot/wrench.py`, `bot/hqlevel.py`, `templates/build/wrench_bubble.png` (mới); `bot/modules/upgrade.py`, `bot/modules/construct.py`, `bot/modules/observe.py`, `bot/build.py`, `bot/runner.py`, `config.yaml`, `src/aowbot/perception/eval/names.py`, `CLAUDE.md`; `tests/legacy/test_p13i_wrench.py`, `tests/legacy/test_p13i_hq_gate.py`, `tests/legacy/test_p13d_hq_read.py`.
