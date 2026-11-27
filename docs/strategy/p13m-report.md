# P13m — "Nhảy" điều kiện nhà chính, mở rộng lãnh thổ, phiến quân leo cấp

Ngày 27/11/2026. Yêu cầu chủ dự án t106u, t107u. **Chưa chạy bot sống**: mọi kết luận kiểm trên 6 ảnh chủ dự án (`tests/fixtures/p13m/`) và test offline.

Ảnh của chủ dự án là bản cắt cùng bề ngang khoảng 540 px. Tọa độ dưới đây ghi theo ảnh cắt; với bảng phiến quân và ảnh mũi tên, test còn đặt ảnh vào khung 540×960 (bảng ở (1,138), ảnh mũi tên ở (150,250)).

## 1. Nâng nhà chính thiếu điều kiện

**Nguyên nhân.** `build.upgrade_here` lấy nút "Nhảy" bằng `v.find`, tức nút khớp mẫu cao nhất. Trên `hq_prereq_nhay.png` ba dòng khớp 0,999 / 0,999 / 0,997, nên tia sáng trên nút chỉ cần làm lệch một phần nghìn là bot nhảy sang dòng 2 hoặc 3.

**Sửa.** `build.first_jump`: trong các nút khớp mẫu "Nhảy" cùng cột (ngưỡng phụ 0,72), lấy nút trên cùng. Giữ nguyên đệ quy `upgrade_here` (`max_depth` 4). Nâng xong thì `upgrade.hq_chain` / lượt ghé sau mở lại nhà chính và kiểm lại bảng (đã có sẵn).

**Dòng tài nguyên.** Không bấm "Nhận càng nhiều". Khi công trình điều kiện đã đủ (không còn "Nhảy"), bot bấm "Tăng cấp", popup "Thiếu tài nguyên" hiện ra và đi luồng `bot/resources.py` sẵn có (chỉ "Dùng đạo cụ" trái).

| Điểm | Tọa độ |
|---|---|
| Bấm: "Nhảy" của Sở Công Nghệ | **(468, 162)** |
| Không bấm: "Nhảy" dòng 2, 3 | (468, 211), (468, 260) |
| Không bấm: "Nhận càng nhiều" | khung (424–511, 294–327) |
| Không bấm: "Tăng cấp ngay" 5473 kim cương | khung (82–243, 365–418) |
| "Tăng cấp" (chỉ khi hết dòng "Nhảy") | (387, 378) |

## 2. Mở rộng lãnh thổ: phiến quân trên ô đỏ trong thành

**Nguyên nhân.** Bước `expand` chỉ tìm icon ổ khóa mở trên viền thành. Tutorial/follow bấm `find_beam` = (273, 378), tức dưới chân con quái.

**Sửa.**
- `guide_tile.find_rebel`: ô đỏ có cột sáng cam và ô xanh lam (lính mình) bên cạnh → điểm bấm là thân con quái, cao hơn tâm ô 0,15 bề ngang ô. Chỉ nhận khi đang ở thành phố (nút bản đồ hoặc icon búa).
- `expand.fight_rebel`: bấm → bảng "Phiến quân" thì kiểm cấp / lực chiến; màn đội hình thì tối ưu đội hình và **chỉ đánh khi dự đoán "Thắng toàn diện"**. Cú bấm không đổi màn, không dự đoán thắng hoặc thua → danh sách đen tọa độ hết lượt ghé.
- Gắn vào `expand` (quét viền thành), `mainquest` (trước và sau khi chạm thanh nhiệm vụ; không cần quân đoàn), `tutorial` / follow / cảm nhận hướng dẫn giữa các bước.
- Log: `mo rong lanh tho: danh phien quan o`.
- Trong `tutorial.decide` luật này gộp vào luật ô đỏ cũ nên vẫn giữ giới hạn 6 lần bấm một ô. Ba khung tân thủ cũ (xe đầu lâu, cột sáng bị xe che) cũng đi đường mới: điểm bấm (274, 456) thay cho (276, 461), và (166, 363) thay cho (160, 389), đều trên thân xe theo ảnh.

| Điểm | Tọa độ |
|---|---|
| Bấm: hông con phiến quân, trong khung đỏ (201–345, 245–431) | **(276, 350)** |
| Tâm ô đỏ | (276, 366) |
| Không bấm: lính mình trên ô xanh | khung (165–232, 335–450) |

## 3. Phiến quân mở khóa tuần tự

**Nguyên nhân.**
- `npc_search` bấm "Tìm kiếm" rồi bấm điểm cố định giữa màn `TARGET` (272, 445). Đường thanh nhiệm vụ cũng vậy.
- Nút "Tấn công" trên `rebel_lv2_tancong.png` lớn hơn mẫu 6 % (đúng tỉ lệ chỉ khớp 0,61) nên bảng bị coi là không có gì.
- Màn quân đoàn có `gather/btn_march` được "Xuất chinh" mà không kiểm dự đoán thắng.

**Sửa** (mở rộng `mainquest.npc_search`, dùng chung cho `arrow` và `rebels`):
1. `npc_popup`: `attack` / `search` / `rally`; nút "Tấn công" thử thêm tỉ lệ 1,06 và 0,95 trong vùng nút.
2. Bảng "Tìm kiếm": đọc N bằng OCR, nhớ theo máy (`memory.db` và `state.json`: `npc_max_level`, Cơ giáp: `mech_max_level`), log `phien quan: toi da cap N -> tim kiem`.
3. `tap_rebel`: bấm vật thật dưới mũi tên xanh (`world_target.pick`, lệch ngang tối đa 70 px). Sau thanh nhiệm vụ mà không có mũi tên: chỉ bấm sprite có nhãn "Phiến quân" quanh giữa màn. Không còn cú bấm điểm giữa màn ở luồng phiến quân.
4. Tối đa 4 vòng. Dừng khi: nút "Tìm kiếm" không đóng bảng; không thấy sprite; cùng cấp N quay lại lần thứ ba (tức đã bấm "Tìm kiếm" 2 lần). Sprite bấm không ra bảng → danh sách đen.
5. `npc_engage`: cả hai kiểu màn quân đoàn đều phải "Thắng toàn diện".
6. `rebels.popup_target`: bảng Cơ giáp chỉ có "Tìm kiếm" → leo cấp tới "Tập kết tấn công". Chốt nhà chính < 15 không đổi.

| Ảnh | Kết quả |
|---|---|
| `rebel_max_lv2_timkiem` | `search`, nút "Tìm kiếm" **(262, 610)** (khung 540×960: (263, 748)); OCR **N = 2** |
| `rebel_arrow_lv2` | mũi tên (124, 56); bấm con cấp 2 **(128, 133)** (khung: (278, 383)); không bấm nhãn, không bấm con cấp 6 |
| `rebel_lv2_tancong` | `attack`, nút "Tấn công" **(264, 600)** (khung: (265, 738)) |
| `rebel_quest_lv3` | bản đồ, không có bảng; sprite có nhãn gần nhất (262, 258), không rơi vào căn cứ (LSS)MF001 |

## 4. Luật an toàn

Không đổi so với P13l:
- Không bấm menu căn cứ người chơi (Trinh sát / Tấn công / Tập kết / Tin tức); ngoại lệ duy nhất là cướp xe tinh thể. `tap_rebel` đi qua `Ctx.tap` nên vẫn qua hàng rào `map_menu`, và `world_target` loại căn cứ trước khi bấm.
- Không kim cương, không "Tăng cấp ngay", không "Mua"; thể lực / VIP chỉ "Dùng".
- Nhà chính < 15 không tham gia / không mở tập kết Cơ giáp từ mũi tên.
- Farm 1 thợ, chỉ #1 có 2; thợ rảnh thì xây trước.
- Không đụng IMEI / model, không ghi dữ liệu app.

## 5. Chưa kiểm / rủi ro

- Chưa có khung hình nào cho màn hiện ra **sau khi bấm con quái trong thành**. Code xử lý màn đội hình, nút "Tấn công", bảng "Phiến quân"; màn khác giao cho follow.
- Hai điểm bấm đổi trên khung tân thủ cũ mới kiểm bằng ảnh, chưa kiểm trên máy. Cú bấm không ăn thì tọa độ vào danh sách đen.
- Cổng dự đoán thắng áp cả khi đang tân thủ (chỉ khi thành phố đã có nút bản đồ hoặc icon búa). Nếu màn đội hình của trận này không hiện "Thắng toàn diện", tân thủ sẽ tạm dừng theo cơ chế `weak_wait`.
- Cổng dự đoán thắng mới trên màn quân đoàn cũ: nếu chữ xanh không đọc được thì bỏ trận (an toàn, nhưng mất lượt).
- `mainquest.npc_max_ratio` (0,3) vẫn giữ: phiến quân cấp 2 "Đề xuất 10.000" cần lực chiến khoảng 33.000 mới đánh. Máy yếu hơn sẽ bỏ và lùi 2 giờ.
- Mỗi lượt ghé vẫn gửi 1 đội rồi đợi về, nên leo từ cấp 2 lên cấp 3 cần ít nhất 2 trận.
- Bảng tài nguyên: giả định bấm "Tăng cấp" khi chỉ thiếu tài nguyên sẽ ra popup "Thiếu tài nguyên" (như P13l); chưa có ảnh từ đúng bảng này. Không ra popup thì kết quả là `blocked` kèm ảnh `build_blocked`.
- Sau "Nhảy", bot vẫn dựa vào game mở menu công trình đích (hành vi cũ).

## 6. Kiểm tra

- `pytest` trong worktree: 1624 qua, 197 bỏ qua (thiếu ảnh chỉ có ở máy chính).
- `pytest` trên bản sao tạm có thêm `tests/fixtures`, `data/owner-feedback` và ảnh log được test gọi tới (chỉ đọc thư mục chính): **1790 qua, 43 bỏ qua**. Lần chạy này bắt được hồi quy trên 3 khung tân thủ của bản sửa đầu (đã sửa).
- `ruff check .` và bộ luật mã cũ: sạch. `mypy`: sạch (73 file). `lint-imports`: 8/8.
- `main.py --check`: thiếu 15/273 (không đổi).
- Test mới `tests/legacy/test_p13m_nhay_expand_rebel.py`, ảnh ở `tests/fixtures/p13m/`.
- Sửa test cũ `test_p12_rebels_search`: bỏ khẳng định "bấm giữa màn sau Tìm kiếm".
- Chép `data/owner-feedback/p13/quan_quan_tuan_bam_sai.png` từ worktree p13l (thư mục `data/` không vào git).
