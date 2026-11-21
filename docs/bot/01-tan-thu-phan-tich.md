# Phân tích bản ghi tân thủ — MFarm06
Bản ghi: `logs/rec/20261117_232742_khoi_tao_tan_thu/` (99 thao tác, 8.2 phút, 23:27:42–23:35:56, bản `.vn` 2.5.16).
Ảnh tổng hợp: `.../sheets/s01–s09.png` (ảnh "trước" của mỗi thao tác, vòng đỏ = điểm chạm, mũi tên vàng = vuốt).

## 1. Trình tự tân thủ quan sát được
| # | Giai đoạn | Thao tác | Màn hình |
|---|---|---|---|
| 1 | Mở đầu | #1 | "Bắt đầu trò chơi" (290,814) |
| 2 | Trận chạy đường 1 | #2–5 | gợi ý `« »` vuốt ngang; đi qua cổng xanh `+N`, tránh cổng đỏ `-N`; giữ ngón tay suốt trận |
| 3 | Kết quả thắng | #6–7 | "Thắng toàn diện" → nút **Đóng** |
| 4 | Thành phố, mũi tên V | #8 | chạm vòng tròn dưới chữ V |
| 5 | Trận chạy đường 2 (thua 1 lần) | #9–25 | "Thất bại nặng nề" → **Bắt đầu lại** (#14–16, bấm 3 lần); nhiệm vụ "Tiêu diệt 80 quân nổi loạn" |
| 6 | Thắng → mở khóa lính | #26–29 | Đóng → hội thoại "Sĩ quan phụ tá" → thẻ **CONGRATULATIONS** "Lính quân dịch" (chạm góc trên phải) |
| 7 | Thành phố → nhận Tank | #30–34 | V-marker → hội thoại → **CONGRATULATIONS** "Tank Gấu Xám" → V-marker |
| 8 | Trận 3 | #35–37 | chạy đường → Thắng → Đóng |
| 9 | Dựng căn cứ | #38–46 | vuốt bản đồ, V-marker trên bãi phế tích; hội thoại "Tổng thư ký"; **Mở khóa kiến trúc mới** "Nhà máy phát điện"; thanh nhiệm vụ góc trái dưới |
| 10 | **Nhiệm vụ Chương 1** | #47–59 | bảng "Chương 1: Trùng kiến lãnh thổ (x/4)": **Nhận** từng dòng → popup "Chúc mừng nhận được" (chạm ra ngoài) → **Đến** → Xưởng kiến trúc → **Nâng cấp** (miễn phí) → Nhận thưởng chương |
| 11 | Trận boss gấu | #60–74 | hội thoại → màn đỏ "Ho! Ha!" → **Tấn công** (397,830) → **Chiến đấu** (281,912) ở màn đội hình → chạy đường + "CẢNH BÁO!" (né theo hình số 8) → Thắng → Đóng (vị trí 924) |
| 12 | Cảnh phim | #75–82 | ảnh truyện tranh, hội thoại liên tiếp → chạm để qua |
| 13 | Dọn phế tích | #77–99 | biểu tượng **bàn tay xanh** trên đống đổ nát → chạm; hộp quà trên bản đồ; nhiệm vụ "Dọn dẹp khu phế tích 1/2/3"; một trận nữa (#88–92, giữ lâu để di chuyển robot) |

Kết thúc bản ghi: đang ở nhiệm vụ "Dọn dẹp khu phế tích 3". Tân thủ **có thể chưa hết hẳn**: game tiếp tục dẫn bằng thanh nhiệm vụ.

## 2. Danh mục phần tử giao diện và cách xử lý
| Phần tử | Nhận diện | Hành động | Toạ độ ghi được (540×960) |
|---|---|---|---|
| Bắt đầu trò chơi | ảnh mẫu nút vàng | chạm | (290,814) |
| **V-marker vàng** | ảnh mẫu chữ V (animate, ngưỡng ~0.75) | chạm **tâm V + (0, +53)** (đo trên 9 khung: dy 47–61) | — |
| Bàn tay xanh (kéo/dọn) | ảnh mẫu bàn tay | chạm vào đống đổ nát ngay dưới | (87,764) (291–359, 501–503) |
| Hội thoại nhân vật | khung dưới có tên + ▽ | chạm bất kỳ chỗ trống | nhiều vị trí (y 470–720) |
| CONGRATULATIONS (mở khóa) | chữ "CONGRATULATIONS" | chạm góc trên phải | (496–504, 32–34) |
| Thắng toàn diện | tiêu đề vàng | nút **Đóng** | y 747–757 (trận thường), y 905–924 (trận có bảng sát thương) |
| Thất bại nặng nề | tiêu đề xám | **Bắt đầu lại** | (270,750) |
| Chúc mừng nhận được | popup phần thưởng | chạm ngoài popup | (274,716–770) |
| Bảng Chương N | tiêu đề "Chương" | **Nhận** (x≈440–470) trước, rồi **Đến** | (442–469, 274–501), thưởng chương (447,741) |
| Nâng cấp công trình | nút "Nâng cấp" (miễn phí lúc đầu) | chạm | (361,921) |
| Màn đỏ thách đấu | nút đỏ **Tấn công** | chạm | (397,830) |
| Màn đội hình | nút **Chiến đấu** | chạm | (281–313, 912–921) |
| Cảnh phim | ảnh toàn màn, có chữ phụ đề | chạm giữa | (273–283,596) |
| Trận chạy đường | HUD trận (`campaign/battle_hud`) | **giữ ngón tay** + trượt ngang (đã có `bot/steer.py`) | vuốt dài 2–25 s |

## 3. Đối chiếu với bot hiện tại
| Thành phần | Hiện trạng | Cần làm |
|---|---|---|
| `bot/modules/tutorial.py` | có logic (V-marker, nút, kéo, né) | **`templates/tutorial/` trống** → không nhận ra gì; offset V đang +45 → sửa +53; thêm xử lý: hội thoại, CONGRATULATIONS, Thất bại → Bắt đầu lại, bàn tay xanh, bảng Chương, cảnh phim |
| `bot/steer.py` | lái quân bằng sendevent giữ ngón tay | dùng lại cho trận chạy đường tân thủ |
| `templates/campaign/` | có `battle_hud`, `res_win`, `res_lose`, `btn_retry`, `btn_done`, `btn_fight`, `btn_attack` | kiểm tra lại ảnh mẫu có khớp màn tân thủ không (cùng giao diện) |
| `templates/common/` | `tap_to_close`, `tap_to_continue`, `msg_reward`, `btn_close`... | dùng lại cho popup thưởng |
| `config.yaml` | `game_package: ...vn`, `instances: [0..8]` | sửa còn 6 instance hiện có (0, 2–6) |

## 4. Ảnh mẫu cần cắt từ bản ghi (`templates/tutorial/`)
| Tên | Khung nguồn | Ghi chú |
|---|---|---|
| `marker_v` | #44 bbox (231,331)–(307,399) | đã thử: khớp 0.75–1.0 trên 7/9 khung |
| `btn_start_game` | #1 quanh (290,814) | |
| `res_win` / `btn_close_win` | #6, #73 | 2 vị trí nút Đóng |
| `res_lose` / `btn_restart` | #14 | |
| `dialog_box` | #28, #40, #60 | khung tên nhân vật + ▽ |
| `congrats` | #29, #33 | chữ CONGRATULATIONS |
| `hand_green` | #77, #93 | |
| `chapter_title`, `btn_claim`, `btn_go` | #47, #53 | |
| `btn_attack_red` | #64 | |
| `btn_fight` | #68 | |
| `btn_upgrade` | #56 | |
| `unlock_building` | #45 | "Mở khóa kiến trúc mới" |
| `reward_popup` | #48, #84 | "Chúc mừng nhận được" |

## 5. Đề xuất thuật toán tân thủ (vòng lặp theo ưu tiên)
1. Đang trong trận (`battle_hud`) → `steer` (giữ ngón tay, né cổng đỏ / CẢNH BÁO).
2. Thắng → Đóng · Thua → Bắt đầu lại (giới hạn N lần, rồi báo lỗi).
3. CONGRATULATIONS → chạm góc trên phải · popup thưởng → chạm ngoài · hội thoại / cảnh phim → chạm vùng giữa.
4. Bảng Chương → Nhận hết → Đến.
5. Nút đã biết (Tấn công, Chiến đấu, Nâng cấp, Bắt đầu trò chơi).
6. V-marker → chạm tâm V + (0,53) · bàn tay xanh → chạm dưới bàn tay.
7. Không thấy gì → chờ; nếu đang ở thành phố và đứng yên quá lâu → chạm thanh nhiệm vụ góc trái dưới (≈ (113,812)); vẫn không có gì → coi như hết tân thủ, chuyển sang `mainquest`.

Mỗi bước ghi log + ảnh khi kẹt (`logs/shots/`) để so lại với bản ghi mẫu.
