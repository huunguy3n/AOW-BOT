# ADR-0011: Tân thủ: hàm quyết định thuần + kiểm tra offline bằng bản ghi

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-11-17
- **Liên quan:** `bot/modules/tutorial.py`, `tools/record.py`, `tools/replay_tutorial.py`, `tools/run_tutorial.py`, `docs/bot/01-tan-thu-phan-tich.md`

## Bối cảnh
Tân thủ dài (~100 thao tác, ~8 phút), nhiều màn có hoạt ảnh, chỉ chơi được một lần mỗi tài khoản mới → rất tốn để thử trực tiếp.

## Quyết định
- **Ghi mẫu:** `tools/record.py` chỉ đọc `getevent` + `screencap` khi người chơi làm mẫu → `logs/rec/<ts>_<tên>/` (events.jsonl, ảnh trước/sau mỗi thao tác).
- **Quyết định thuần:** `tutorial.decide(vision, img, idle, state) → (action, x, y, lý do)` chỉ đọc ảnh, không chạm thiết bị; vòng lặp theo thứ tự ưu tiên (trong trận → thắng/thua → popup/hội thoại → bảng Chương → nút đã biết → V-marker/bàn tay → chờ/chạm thanh nhiệm vụ).
- **Kiểm tra offline:** `tools/replay_tutorial.py` chạy `decide()` trên từng ảnh "trước" của bản ghi và so với thao tác thật (OK / ALT / DIFF).
- **Chạy thử thật:** `tools/run_tutorial.py --idx N` lưu trace từng bước vào `logs/live/`.

## Hệ quả
- Tốt: lặp nhanh trên dữ liệu thật, không tốn tài khoản; mẫu này áp dụng được cho module khác (mainquest, campaign).
- Xấu: bản ghi chỉ phủ một đường đi; các nhánh hiếm (thua, kẹt) chỉ phát hiện khi chạy thật (`logs/shots/*tutorial_stuck|lose|maxsteps*`).
