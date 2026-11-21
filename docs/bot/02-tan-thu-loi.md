# N2 — Phân tích lỗi tân thủ (#5) và chuyển giao sang nhiệm vụ chính
Ngày: 2026-11-18 · Kế hoạch: [ke-hoach-hoan-thien-bot.md](../product/ke-hoach-hoan-thien-bot.md) · Trước đó: [01-tan-thu-phan-tich.md](01-tan-thu-phan-tich.md)

## 1. 8 ảnh lỗi cũ (`logs/shots/*tutorial_*`, 2026-11-17 23:56 → 11-18 01:10)
Chạy lại `decide()` **hiện tại** trên từng ảnh (đã chép vào `tests/fixtures/tutorial/`):

| # | Ảnh | Màn hình | Nguyên nhân lúc đó | Hiện tại |
|---|---|---|---|---|
| 1–3 | `*_lose` | "Thất bại nặng nề" | **Lái quân thua** 5 lần liên tiếp → dừng (`max_retry`) | Bấm "Bắt đầu lại" đúng; chất lượng lái quân vẫn là rủi ro (xem §4) |
| 4 | `001529_stuck` | Bảng Chương 2 (0/5) | Chưa bấm "Đến" | ✅ "bang chuong -> Den" |
| 5 | `002831_stuck` | Popup **trả phí** "Gift bag of first purchase" | Không đóng được | ✅ chỉ bấm X (`common/btn_x_offer`), không bấm nút giá |
| 6 | `003724_lose` | Thua, có chữ V chỉ "Hoàn thành nhiệm vụ…" (nút Đóng/Bắt đầu lại bị khóa) | Bấm nút bị khóa | ✅ theo chữ V |
| 7 | `010559_maxsteps` | Kéo "Mỏ quặng" vào ô xanh, dấu chân đỏ | Không kéo | ✅ kéo dấu chân đỏ tới ô trống |
| 8 | `011006_stuck` | Màn "Mỏ quặng", nút "Xây dựng ngay — Miễn phí" | Chạm lệch theo chữ V | ✅ bấm nút Miễn phí |

**Kết luận [ĐO]:** 6/8 điểm kẹt đã được sửa trong các lượt chạy thử đêm 17–18/11 (code sửa lúc 01:20); 3 ảnh thua là do lái quân, không phải do nhận diện.

## 2. Điểm kẹt mới nhất: hết hướng dẫn nhưng bot không biết
Trace cuối `logs/live/20261118_012116_tutorial_i5`: tài khoản đã tới **Chương 5 "Thực nghiệm tác chiến"**, không còn chữ V. Bot lặp: chạm thanh nhiệm vụ → "Đến" → menu công trình (Chi tiết / Tăng cấp) → **chờ** → … mãi mãi (điều kiện kết thúc cũ bị reset mỗi lần bấm "Đến").

**Sửa** (`bot/modules/tutorial.py`):
- `decide()`: menu công trình ở thành phố (`build/btn_upgrade_icon`) mà **không có chữ V** trong 2 khung liên tiếp → `done` (chữ V nhấp nháy có thể lọt 1 khung).
- `finish()`: ghi `tutorial_done` vào `state.json`, **tắt bước `tutorial` cho máy đó** (`settings.json`), thoát về thành phố. Lượt sau `mainquest` / `quests` (đã biết bấm "Tăng cấp" qua `bot/build.py`) làm tiếp.
- Đường kết thúc cũ (chạm thanh nhiệm vụ >3 lần không có hướng dẫn) cũng đi qua `finish()`.

## 3. Tình huống mới gặp khi mở #5 (21:23)
Căn cứ bị đánh khi offline: *"Độ bền của Xưởng kiến trúc đã giảm xuống 0… Xây dựng lại"* — nút duy nhất, miễn phí, game tự dời căn cứ.
- Cắt ảnh mẫu `common/btn_rebuild`, thêm vào `Ctx.POPUP_CLOSERS` (mọi lượt chạy) và `decide()` (tân thủ).
- Hệ quả: tài khoản mới **bị tấn công thật** → ảnh mẫu `defense/alert_attack` (phòng thủ) càng cần sớm.

## 4. Kiểm chứng
| Kiểm tra | Kết quả |
|---|---|
| `python tools/check_tutorial.py` (12 ca hồi quy từ ảnh kẹt thật) | **[ĐO] 12/12 đúng** |
| `python tools/replay_tutorial.py` (bản ghi người chơi 99 thao tác) | **[ĐO] 92/99** — không đổi so với trước khi sửa; không có `done` nhầm |
| Chạy thật #5: `python tools/run_tutorial.py --idx 5` | **[ĐO]** 7 bước: Chương → Đến → menu → `done` → "xong tân thủ" (`logs/live/20261118_212504_tutorial_i5`) |
| `mainquest` + `quests` trên #5 sau chuyển giao (4 lượt, 21:25–21:39) | **[ĐO]** sau 3 bản sửa ở §4b: **bắt đầu nâng cấp Xưởng kiến trúc lv2→3** thành công; dừng ở bảng Chương 5 (xem §5) |
| Tân thủ từ đầu trên tài khoản **mới** | **[CHƯA ĐO]** — cần chủ dự án tạo tài khoản mới (N5) |

## 4b. Lỗi phát hiện khi chạy `mainquest`/`quests` trên #5 — đã sửa
| Lượt | Hiện tượng | Nguyên nhân | Sửa |
|---|---|---|---|
| 1 | `mainquest_unknown` | Hội thoại "Tổng thư ký: Cần thỏa mãn điều kiện tiền đề mới" che màn Tăng cấp | `Ctx.skip_dialogs()`; gọi trong `build.upgrade_here` (sau icon Tăng cấp, sau "Nhảy") và `mainquest.step` |
| 2 | OCR ra số rác, "không thấy thanh nhiệm vụ" | **Game đã tự thoát** về màn hình chính Android, bot vẫn thao tác tiếp | `Device.app_alive()` (pidof) trước **mỗi bước**; game không chạy → mở lại, đếm `game_restarts` |
| 3 | `build_blocked` | Nâng cấp **đã bắt đầu** nhưng hội thoại "…hãy tăng tốc hoàn thành!" hiện sau đó → bị coi là thất bại | `skip_dialogs()` ngay sau khi bấm "Tăng cấp" |

Ảnh đã chép vào `tests/fixtures/tutorial/` (`dialog_prereq.png`, `dialog_after_upgrade.png`, `rebuild_popup.png`).

## 5. Còn lại cho N3–N5
- **Bảng Chương sau tân thủ** (Chương 5: "Tăng 1 Tướng lên cấp 9", "Dọn dẹp khu phế tích 24"): thanh nhiệm vụ giờ mở bảng Chương, `mainquest` chưa xử lý bảng này, `quests` bấm "Đến" nhưng không nhận ra màn đích (tướng / phế tích) → `none`. Các thao tác này **đã có trong `tutorial.decide()`** (tăng cấp tướng, bàn tay xanh, cột sáng) → N4: tách thành hàm dùng chung cho `quests`.
- **Lái quân** (3/8 ảnh lỗi): chưa đo tỉ lệ thắng trận chạy đường; cần tài khoản mới để có lại các trận đầu.
- Rủi ro của quy tắc `done`: nếu chữ V bị che ≥2 khung liên tiếp khi đang ở menu công trình, bot tắt tân thủ quá sớm. Giảm thiểu: `mainquest` vẫn đi theo thanh nhiệm vụ; có thể bật lại `tutorial` trên web.
- Ảnh mẫu `tutorial/zone_green` không còn được dùng (đã thay bằng nhận diện màu) — bỏ khỏi danh sách cần cắt.

## 6. Bảng Chương sau tân thủ (làm tiếp 2026-11-18 tối, #5)
**Cách làm:** dùng lại `tutorial.decide()` ở chế độ **`follow`** (`tutorial.follow(ctx)`) cho các dòng Chương mà "Đến" không dẫn tới màn nâng cấp (tướng, dọn phế tích, xây mới…). `quests` (tab Chương) và `mainquest` (khi không nhận ra màn) gọi `follow`; dừng khi về thành phố đứng yên. Tùy chọn `quests.follow` / `quests.follow_steps` (web: "Chương: làm cả việc không phải xây").

Khác với tân thủ, chế độ `follow`:
- **Không làm gì ở màn Chiêu mộ** (kể cả khi chữ V chỉ vào) → quay ra; chiêu mộ chỉ do `notify` quyết định.
- **Không đánh khi màn đội hình không dự đoán "Thắng toàn diện"** (sau khi đã bấm tự xếp) → trả `weak`, giống `mainquest`/`campaign`.
- Thua 1 trận là dừng (`max_retry=0`), không "Bắt đầu lại".

**Sửa thêm:** `quests` nhận thưởng dòng đã xong + thưởng chương (nút sáng) trước khi bấm "Đến"; đánh số lại dòng sau khi nhận; hết thợ xây vẫn làm tiếp các dòng khác. `mainquest`: thanh nhiệm vụ mở bảng Chương → nhường `quests`. Tướng hết nút "Tăng cấp" → quay lại.

**Chạy thật #5 (5 lượt, 21:42–22:00) [ĐO]:**
| Lượt | Kết quả |
|---|---|
| 1 | `mainquest`: "Nhảy" sang điều kiện → **bắt đầu nâng cấp** (lv2→3). `quests`: tướng Lính quân dịch **lv8→9** (xong dòng "Tăng 1 Tướng lên cấp 9"), nhận thưởng 1 dòng. Kẹt ở màn chi tiết tướng → đã sửa |
| 2 | ⚠ **Sự cố:** chữ V dẫn vào Chiêu mộ cao cấp, bot bấm **"Chiêu mộ 10 lần" → tiêu 10 phiếu** (24→14). Kim cương **không đổi (2010)**. Cùng hành vi `notify` vẫn làm khi nút có chấm đỏ, nhưng không qua quy tắc của `notify` → đã chặn |
| 3 | "Dọn dẹp phế tích" → đánh phản quân, **thua 3 trận** (không dự đoán thắng) → đã sửa |
| 4 | Đúng như mong đợi: `mainquest` tạm dừng (lực chiến 111.906 < 117.501), `quests` xếp đội hình → `weak` → không đánh |

**Trạng thái Chương 5 của #5:** 3/5 — còn "Tăng Xưởng kiến trúc đến cấp 3" (đang nâng cấp, chờ xong) và "Dọn dẹp khu phế tích 24" (17/24, cần lực chiến cao hơn). Không còn việc tự động làm được ngay → đúng hành vi.

**Kiểm chứng offline:** `tools/check_tutorial.py` **16/16**, `replay_tutorial.py` 92/99 (không đổi).

**Rủi ro còn lại:** `follow` đi theo chữ V của game; đã chặn Chiêu mộ và trận không chắc thắng, nhưng chữ V có thể dẫn vào màn khác có tiêu tài nguyên (cửa hàng, tăng tốc…). `decide()` chưa bao giờ bấm nút có giá kim cương, nhưng chưa có danh sách chặn tổng quát theo màn hình.
