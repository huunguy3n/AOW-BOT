# P13g — FillState, #0 không về thành phố, lỗi `observe` rỗng, tìm mỏ thu thập (26/11/2026)

Nhánh `p13g` (tách từ `p7-live-fixes` @ `dc0ce47`). **Chưa chạy thật trên máy nào** (không bật LDPlayer / ADB, không chạy gather live). Kết luận dựa trên log, ảnh lưu của cây chính (chỉ đọc), bản sao `memory.db`, và test offline.

## P13g-1 `module 'aowbot.domain.builders' has no attribute 'FillState'`

- **Nguyên nhân:** lần start 09:17:45 thừa hưởng `PYTHONPATH` trỏ worktree P13e cũ, nên `aowbot` được nạp từ đó. Class `FillState` trong `p7-live-fixes` không thiếu. `bot/__init__.py` thêm `src/` vào **cuối** `sys.path`, nên `PYTHONPATH` (và cả bản cài editable `E:\AOW-BOT`) luôn thắng.
- **Sửa:** `bot/__init__.py` đặt `src/` của chính repo lên đầu; `run.bat` xóa `PYTHONPATH` (trong `setlocal`); `main.py` ghi "Ma dang chay / aowbot" và cảnh báo nếu lệch.
- **Rà lời gọi:** `bot/runner.py` (`FILL_STEPS`, `FillState`) và `bot/scheduler.py` (`effective_max`) đều tồn tại; có test quét mọi `builders_dom.*`.

## P13g-2a #0 `goto(city) ... man cuoi unknown` rồi bỏ lượt

- **Nguyên nhân:** #0 đang chạy **720×1280**, không phải 540×960. Cả 71 ảnh `unknown` ngày 26/11 của #0 đều 720×1280; các máy khác 540×960; `leidian0.config` ghi độ phân giải 1280×720. Ảnh chụp cuối còn 540×960 lúc ~01:44, ảnh 720×1280 đầu tiên lúc 07:52. Không rõ ai/cái gì đổi cấu hình.
- Hệ quả: không ảnh mẫu nào khớp → bot bấm Back trên thành phố → hộp thoại "Rời trò chơi?" → chạm "Hủy" theo tọa độ 540×960 nên trượt → lặp.
- Thử offline: thu 71 ảnh về 540×960 → 70 ảnh nhận ra (thành phố / popup / hộp thoại thoát). Ảnh còn lại là màn nạp game 99% (10:02, ngay sau timeout ADB).
- **Sửa:**
  - `bot/device.py`: khung dọc cùng tỉ lệ khác 540×960 → thu nhỏ; tap/swipe nhân lại tọa độ; cảnh báo. `steer` / `touch` / `stream` / `human` dùng cùng hệ số.
  - Nhận màn nạp game (`common/splash_logo`) → đợi, không bấm Back. Trên 4585 ảnh lưu chỉ khớp màn nạp.
  - `bot/runner.py`: 2 bước liên tiếp không về được thành phố → đóng popup + `goto` (đã gồm Back / nút quay lại / bản đồ → thành phố); không được thì khởi động lại game (không xóa dữ liệu); chỉ bỏ lượt khi cứu không được. `nav.rescue_max` = 1. Không thêm bước "ra bản đồ rồi vào lại" riêng.
- **Chưa kiểm:** cảm ứng `sendevent` ở 720×1280 (giả định trục thô tỉ lệ theo độ phân giải) — chỉ ảnh hưởng trận lái quân, kéo công trình và bộ ghi thao tác tay. Nếu giả định sai, bộ ghi thao tác tay có thể coi chạm của bot là của người và tạm dừng bot.
- **Việc của chủ dự án:** đặt lại #0 trong LDPlayer thành 540×960, DPI 240. Bản sửa chỉ là lớp đỡ.

## P13g-2b #1 `Loi o buoc observe:` trống

- **Nguyên nhân:** ADB hỏng lúc quét chấm đỏ cuối lượt (`reddots.run(final=True)`); khối `except` gọi `ctx.ensure_city()`, hàm này ném `ScreencapError` lần nữa, lỗi bị gán cho bước `observe`. Nội dung lỗi nằm ở traceback phía dưới. Máy được cứu nhưng `observe` không chạy lại.
- **Sửa:** dòng đầu là `Loi o buoc <bước>: <Loại>: <nội dung>` (cả `last_error`); việc phụ cuối lượt lỗi không lan sang `observe`; máy treo thì cứu **trước** rồi mới chạy `observe`.

## P13g-3 "Lấy metal xong bấm Tìm vẫn ra mỏ cũ"

- **Nguyên nhân chính (log #1 07:28→07:31 và 09:40→09:43):** bước phản quân học "ô Cấp nhảy 5" của Cơ giáp, lưu vào `ctx.level_step`; thu thập **cùng lượt ghé** dùng luôn → "buoc 5 -> dung cap 5 thay cho 3 / 2 / 1". Mọi lần Tìm ra mỏ cấp 5 (ảnh chạm lưu trong trí nhớ cho thấy huy hiệu cấp 5).
- **Hậu quả thêm:** bảng dung tích tính theo cấp *muốn* tìm, nên quân đoàn tải 80692 được gửi tới mỏ tính là 80000 nhưng thực ra là mỏ cấp 5. Lần Tìm sau ra cùng mỏ → hộp thoại "Chỉ huy trưởng khác…" (bot bấm Hủy).
- **Sửa (`bot/modules/gather.py`, `bot/gather_rules.py`):**
  1. Tab mỏ tài nguyên luôn bước 1; buộc đọc lại ô "Cấp" trước khi Tìm (khác cấp → không Tìm). Không đọc được cấp → không dùng bảng dung tích, phải đọc được trữ lượng.
  2. Số đọc dưới mỏ bằng đúng dung tích một cấp cao hơn → tính theo số lớn đó.
  3. Đọc tọa độ "X/Y" của mỏ vừa tìm (OCR đúng trên 10/10 ảnh bản đồ đã thử). Trùng ô đã gửi trong 8 giờ → không bấm gì trên mỏ, hạ cấp; trùng 2 lần trong 1 loại → loại ưu tiên kế tiếp.
  4. Mỗi loại dò từ `max_level` (8) xuống. **Bỏ trí nhớ `gather_top`** (quyết định 21/11 cho bắt đầu thấp hơn) theo yêu cầu 26/11. Vẫn bỏ qua không mở bản đồ những cấp biết chắc quá tải mọi quân đoàn (luật tải trọng).
- Thứ tự loại lấy theo cấu hình: máy đang dùng `metal, food, alloy, oil` (`data/settings.json`), không đổi. Gather cuối lượt, ngày thứ Hai, mỏ liên minh không đổi.
- **Chưa chạy gather live.** Chưa thấy ảnh bảng mỏ khi đội mình đã tới và đang thu thập; việc nhận ra dựa vào tọa độ, không dựa vào nội dung bảng. Nếu OCR tọa độ hỏng thì chỉ còn luật cũ (cùng loại/cấp + thời gian đi khi đội còn đang đi).

## Cổng kiểm tra

- `python -m pytest -q`: 1497 pass, 105 skip. `ruff check`, `mypy`, ruff cho mã cũ (E9,F63,F7,F82), `lint-imports`: sạch. `main.py --check`: còn 16/260 ảnh mẫu thiếu.
- Để chạy test ảnh trong worktree đã chép `tests/fixtures/` và `data/owner-feedback/` từ cây chính (đều bị gitignore). Không chép thì 3 test `test_p13b_cham_do_khong_doi` hỏng cả trên `dc0ce47` chưa sửa.
- Ảnh `tests/fixtures/p13g/` chỉ có trên máy này.

## Khi đưa vào chạy

Vòng auto đang chạy ở `E:\AOW-BOT` vẫn là mã cũ; cần gộp nhánh và khởi động lại thì bản sửa mới có tác dụng. Lượt thu thập đầu tiên nên xem log: các dòng `O Cap`, `da co quan doan cua minh`, `Man hinh may la`.

Chưa xem: #0 "ADB khong ket noi duoc" nhiều lần từ 02:24 đến 07:13.
