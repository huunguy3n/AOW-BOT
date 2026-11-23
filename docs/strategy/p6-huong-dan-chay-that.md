# P6-5 — Hướng dẫn chạy thật cho chủ dự án (P1 → P6, mục tiêu 24 giờ)

Tài liệu này dành cho **chủ dự án** khi đã duyệt chạy thật. Bot/agent không tự chạy: mọi bước dưới đây do chủ dự án bấm.
Tiêu chí P6 (logs/pm-audit-1.txt): **bước không lỗi ≥ 95 %**, **0 kim cương tiêu ngoài khiên**, **không lúc nào quá 2 máy**.

## 0. Trước khi bắt đầu

1. Sao lưu: `.ldbk` + slot tài khoản **≥ 2 bản trên E: và D:** (CLAUDE.md quy tắc 1–2). Không chạy khi chưa có.
2. Kiểm mã: `python -m pytest -q` (952+ test xanh), `python main.py --check` (ảnh mẫu còn thiếu chỉ làm bỏ thao tác, không lỗi).
3. Cấu hình an toàn (xem trên web → Tùy chọn):
   - `ldplayer.max_running: 2`, `schedule.parallel: 2` (mã cắt cứng về 2 kể cả khi ghi lớn hơn — `aowbot.domain.rollout`).
   - Công tắc chung **Agent: TẮT** (`agent.enabled: false`, mặc định).
   - `defense.gem_cap_daily: 2000`; `warday.mode: auto`; `warday.buy_gems: true` (ngày chiến tranh mua không giới hạn — quyết định 23/11).
4. Mở web: `python main.py --web` → http://localhost:8080 (chạy riêng một cửa sổ để web không tắt theo runner).

## 1. Thứ tự kiểm chứng (mỗi giai đoạn: 1 lượt cố định + 1 lượt kiểm lại)

Mỗi giai đoạn chạy trên **1–2 máy**, đọc số đo rồi mới sang giai đoạn sau. Lệnh mẫu cho máy #1:

| Giai đoạn | Chạy | Xem gì (`python tools/report_ro.py --since "<giờ bắt đầu>" --inst 1`) |
|---|---|---|
| P1 điều kiện + giãn chu kỳ | `python main.py --once --only 1` | dòng "lan ghe smart vo ich" giảm; `heal/campaign/warday/mainquest` không chạy khi không có việc |
| P2 hàng chờ, nghiên cứu, huấn luyện | `python main.py --modules research,train --once --only 1` | "hang cho ranh" (%); log không còn "thieu anh mau research/btn_research"; nghiên cứu bắt đầu thật (kiểm lại) |
| P3 thu thập | `python main.py --modules gather --once --only 1` | "hanh quan day" %, `gather_ev`: Hủy oan (own_dialog) = 0 |
| P4 nhiệm vụ / follow | `python tools/follow_stats.py --since <ngày>` | follow kẹt giảm; nhà chính/ngày tăng |
| P5 tình báo / phản quân / hồi phục | `python main.py --once --only 1` | "tinh bao unknown" %, "chien dau" rebels có kết quả |
| P6 agent (chỉ khi đã duyệt) | xem mục 3 | báo cáo 24 giờ mục 4 |

Không chạy 2 phiên `main.py` cùng lúc (mỗi phiên có thể bật 2 máy → 4 máy).

## 2. Lịch tuần sự kiện (từ 23/11)

- **Thứ 7 (theo giờ reset `warday.reset_hour_utc`)** = ngày chiến tranh: bot mở cửa sổ sớm 2 giờ, dùng Hiệp ước hòa bình (miễn phí) trước giờ G, rồi giữ khiên liên tục (vật phẩm trước, hết thì mua kim cương không giới hạn), đóng cửa sổ muộn 30 phút. Cấm thu thập trong cửa sổ.
  - Lịch sai / sự kiện đổi ngày: web → Tùy chọn → "CÔNG TẮC TAY ngày chiến tranh" = **BẬT** (giữ khiên ngay hôm nay) hoặc **TẮT** (chỉ khi chắc chắn không có chiến tranh). Xong ngày thì trả về **Tự động**.
  - Để giữ khiên 24 giờ, máy phải được ghé đúng lúc gia hạn → trong ngày chiến tranh nên **giữ runner chạy liên tục**; mỗi máy chỉ được bật khi tới lượt (tối đa 2 máy), nên số máy giữ khiên được bị giới hạn bởi thời gian mỗi lượt ghé.
- **Thứ 2** = ngày thu thập: gather chạy đầu lượt, không để dành quân đoàn cho phản quân.

## 3. Bật agent (chỉ sau khi duyệt P6)

1. Web → máy (vd #1) → ô "Chế độ" = **Agent**. Máy hiện nhãn "agent: chờ công tắc" (chưa chạy agent).
2. Xem thử không chạm game: `python -m aowbot plan 1`, `python -m aowbot shadow all` (báo cáo: [p6-shadow-q4.md](p6-shadow-q4.md)).
3. Tab "Học & Agent" → nút **Công tắc chung: TẮT — bấm để bật** → xác nhận. Nhãn đổi thành "agent".
4. Bắt đầu với **1 máy** (#1), 24 giờ, rồi mới thêm máy.

## 4. Chạy 24 giờ và đọc báo cáo

```bash
python main.py --web                     # cửa sổ 1: web
# bấm "Bắt đầu vòng auto" trên web, để chạy 24 giờ
python tools/report_ro.py --24h          # sau 24 giờ (chỉ đọc data/memory.db)
python tools/report_ro.py --24h --json > logs/p6-24h.json
```

Phần đầu báo cáo `-- P6 tong hop --`:

| Dòng | Đạt khi |
|---|---|
| `buoc khong loi: X %` | ≥ 95 % (lỗi = `err`/`stuck`; `warn`/`miss` không tính). Dòng "buoc loi nhieu" chỉ bước cần xem ảnh `logs/shots/` |
| `kim cuong theo nguon {...}; ngoai khien N` | N = 0. Chỉ có `shield` (bị tấn công, trần 2000/ngày) và `shield_war` (ngày chiến tranh) |
| `CAN XEM: kim cuong giam ma so khong ghi` | Không có. Nếu có: mở log máy đó, tìm `KIM CUONG`/`MUA khien`; có thể do OCR đọc sai số kim cương |
| `may chay cung luc toi da N` | N ≤ 2, "qua tran 0.0 s" |
| `P1-P5: ...` | hàng chờ rảnh %, hành quân đầy %, follow kẹt, nhà chính/ngày, tình báo unknown %, phản quân có kết quả |

Log cần tìm (`logs/bot-YYYYMMDD.log`): `KIM CUONG:` (mỗi lần tiêu), `MUA khien`, `NGAY CHIEN TRANH: KHONG BAT DUOC KHIEN`, `Hop thoai thoat game dang mo`, `Watchdog`.

## 5. Dừng khẩn cấp

| Tình huống | Làm |
|---|---|
| Agent làm sai | Web → "Công tắc chung" → TẮT (mọi máy về lịch chung từ lần ghé sau) |
| Dừng mọi thứ ngay | Web → nút **Dừng** trên đầu trang (dừng sau bước đang chạy), rồi `D:\LDPlayer\LDPlayer9\ldconsole.exe quitall` |
| Kim cương bị tiêu lạ | Tắt `defense.shield_buy_gems` và `warday.buy_gems` trên web, dừng runner, gửi báo cáo `--24h` + log |
| Quá 2 máy chạy | Dừng runner; kiểm không có phiên `main.py` thứ hai (Trình quản lý tác vụ → python.exe) |
| Tài khoản có dấu hiệu lạ | **Không** `pm clear` / gỡ app; tắt máy, khôi phục theo ADR-0010 từ bản sao đã verify |
