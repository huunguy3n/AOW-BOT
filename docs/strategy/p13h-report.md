# P13h — kiểm / sửa cấu hình LDPlayer trước khi bật máy (26/11/2026)

Nhánh `p13h` (tách từ `p7-live-fixes` @ `18dbf72`). **Chưa chạy thật**: không gọi `ldconsole.exe` / `adb.exe`, không bật tắt máy nào. Chỉ đọc file cấu hình và log của cây chính; kiểm bằng test với file cấu hình giả và `ldconsole` giả.

## Vấn đề

Máy #0 bị LDPlayer trả về mặc định: `leidian0.config` đang lưu 1280×720 (máy 1–6 là 540×960), DPI 240, `adbDebug` từng bị tắt (hiện đã = 1).

## Nguyên nhân: chưa xác định

Phỏng đoán đang dùng: máy bị tắt khi file cấu hình đang ghi, LDPlayer trả về mặc định. Log ngày 26/11 **không chứng minh** điều này:

- Mã bot không có `ldconsole modify` (trước P13h), `quitall`, `reboot`, `taskkill` hay kill tiến trình giả lập. `proc.kill()` trong `human.py` / `stream.py` chỉ dừng tiến trình `adb` phía máy tính.
- Lần ghé #0 cuối còn tốt kết thúc bình thường lúc 01:53:14, không có cảnh báo tắt máy. Lần ghé kế (02:24:52) ADB đã không trả lời, và tiếp tục như vậy tới 07:18. Suy ra cấu hình nhiều khả năng đổi trong khoảng 01:53–02:27; trong khoảng 01:53–02:24 log không có thao tác nào của bot trên #0.
- Điểm yếu thấy được: `quit` cũ coi là đã tắt ngay khi cột "Android đã chạy" của `list2` về 0. Lúc 01:53 nó trả về gần như tức thì (máy kế được xếp lịch 5 s sau, đúng bằng `sleep(5)` cuối lượt), nên không biết tiến trình máy đã thoát hay chưa.

## Đã làm

- `bot/ldconfig.py` (mới), `LDConsole.check_display` (`bot/device.py`), gọi ngay trước `ldconsole launch`:
  - Sai độ phân giải / DPI / `adbDebug` → log WARNING kèm giá trị cũ của đúng 3 khóa đó.
  - Máy tắt hẳn: `ldconsole modify --index N --resolution 540,960,240`; `adbDebug` ghi bằng cách thay tại chỗ trong văn bản gốc (mọi byte khác giữ nguyên), kiểm lại JSON chỉ khác đúng khóa này, ghi file tạm rồi thay thế.
  - Máy đang chạy / đang tắt dở / không rõ trạng thái: không modify, không ghi, **không tự tắt máy**; sửa ở lần bật sau.
  - File ghi dở / hỏng: không đụng. File đang được ghi: chờ yên `config_settle_s` (5 s). Kiểm tra lỗi không chặn việc bật máy.
- `quit`: chờ tắt **hẳn** (cả PID trong `list2` thoát), vẫn thử 2 lần; không kill tiến trình. Luồng cứu máy treo (quit + launch, không xóa dữ liệu) giữ nguyên.
- Cấu hình: `ldplayer.fix_display`, `resolution`, `dpi`, `config_settle_s`, `config_dir` (tùy chọn). Riêng từng máy: `data/settings.json` → `instances.N.ldplayer.resolution` / `dpi` (runner, `--capture`, `tools/snap.py`).

## Cổng kiểm tra

- `python -m pytest -q`: 1518 pass, 112 skip (28 test mới trong `tests/legacy/test_p13h_ldconfig.py`).
- `ruff check`, ruff cho mã cũ (E9,F63,F7,F82), `mypy`, `lint-imports`: sạch. `main.py --check`: 16/260 ảnh mẫu thiếu (như trước).
- Đã chép `tests/fixtures/` và `data/owner-feedback/` (gitignore) từ cây chính để chạy test ảnh; không chép thì 3 test `test_p13b_cham_do_khong_doi` hỏng cả trên mã chưa sửa.

## Chưa kiểm — xem ở lượt chạy thật đầu tiên

1. Ý nghĩa cột 6, 7 của `list2` (PID, = -1 khi tắt) lấy theo định dạng LDPlayer đã công bố, **chưa đối chiếu trên máy này**. Nếu sai: mỗi lần tắt có dòng `Android da tat nhung tien trinh may chua thoat` (tắt chậm thêm khoảng 50 s) và cấu hình sai không được sửa (`May chua tat han`). Kiểm nhanh khi có máy tắt: `ldconsole list2`.
2. `ldconsole modify` có ghi file ngay và có giữ nguyên các khóa khác hay không. Bot đọc lại sau khi sửa; còn sai thì log ERROR.
3. LDPlayer có nhận `adbDebug` ghi tay hay không.
4. Nếu LDPlayer tự trả về mặc định **ngay lúc bật** (sau bước kiểm) thì lượt đó vẫn chạy cấu hình sai; lần bật sau mới sửa.

Bản sửa chỉ có tác dụng sau khi gộp nhánh vào cây đang chạy và khởi động lại bot.
