# P13j — Tình báo bấm hụt sau "Đi" và chạy lại khi hết quân đoàn (26/11/2026)

Nhánh `p13j`, tách từ `p7-live-fixes` @ 1f52af2. Chỉ kiểm bằng ảnh và test, **chưa chạy trên máy thật**.

## 1. Vì sao bấm hụt

Sau "Đi", nếu chưa thấy "Tấn công" / "Tiếp tế" / "Tập kết", `intel_mission` dùng logic ghim **bản đồ thế giới**:
tìm `intel/marker_fight`, ghim tím/vàng, rồi ba tọa độ cứng (268,405), (268,438), (265,365). Trong thành phố,
dựng lại khung từ ảnh 1 (khung = crop + (−5, +230), khớp bốn icon HUD) cho thấy không ghim nào khớp, và cả ba tọa độ
rơi vào **người lính** của mình trên ô xanh lam. Xe tăng ở khoảng (363,492).

Luật `follow` cũng không giúp ở ảnh 1: `decide()` trả "chờ", vì `find_beam` chỉ tìm cột **cam** và ô **đỏ**. Ở ảnh 2
(đặt cùng góc máy với ảnh 1) `find_hand_beam` cũ bấm đúng hòm; chỗ hụt ở ảnh đó nằm ở đường `intel_mission`.

## 2. Nhận ô xanh và bàn tay (`bot/guide_tile.py`)

- **Ô sáng:** mặt nạ HSV H 33–85, S ≥ 120, V ≥ 150; khớp viền hình thoi nhiều tỉ lệ (ngang 110–210 px), lấy điểm
  của nửa yếu hơn để một cụm xanh lệch một bên không đủ. Ô xanh lam của lính (H 94–116) nằm ngoài dải.
- **Không có tay:** phải có cột sáng hẹp ≥ 50 hàng phía trên ô **và** đang ở thành phố.
- **Có tay:** mẫu mới `templates/intel/point_hand.png` (cắt từ ảnh 2; `hand_green`, `hand_green2` chỉ khớp 0,62),
  khớp 0,8–1,2 lần với mặt nạ phần tay. Bấm tâm ô ngay dưới đầu ngón; không thấy ô thì bấm dưới đầu ngón 85 px.
- **Điểm bấm trên hai ảnh chủ** (tọa độ crop): ảnh 1 (365,268), khung đỏ x 343–394, y 235–292; ảnh 2 (220,244),
  khung đỏ x 175–258, y 218–275. Xóa nét đỏ (inpaint) thì điểm bấm lệch không quá 8 px.
- **Sau khi bấm:** chờ nút / bảng hiện ra, hoặc hướng dẫn mất / dời đi 2 khung liền. Không đổi → danh sách đen tọa độ
  (`TapGuard.ban`, vùng ±30 px, hết lượt ghé). Đổi rồi lại hiện đúng chỗ sau 2 lần bấm → cũng cấm.
- **Đường nối:** `intel_mission` gọi `follow_city` trước logic bản đồ. Đang ở thành phố mà không thấy hướng dẫn →
  **không** bấm tọa độ bản đồ nữa, trả `unknown_target`. Không ở thành phố và không có hướng dẫn → logic cũ giữ nguyên.
  `tutorial.decide` (chỉ chế độ follow) và `guide_visible` của runner dùng cùng bộ nhận và cùng danh sách đen.
  Kết quả mới `guided`: đã bấm theo hướng dẫn, hết hướng dẫn mà không có bảng nào → sang ghim kế, không tính là xong.

## 3. Hết quân đoàn rảnh

Log #1 lượt 20:05 có `no_march` bốn lần (20:11:48, 20:14:03, 20:16:51, 20:17:26): `IR.STOP` chỉ thoát một vòng
`intel()`, còn chấm đỏ và bước `intel` gọi lại. Nay `no_march` đặt `ctx.intel_stop` cho cả lượt ghé:

- `notify.intel()` trả 0 ngay (không chụp, không chọn ghim, không "Đi", không quét lại) — chặn mọi đường gọi;
- `intel.run()` không về thành phố; `notify.run` không mở icon; chấm đỏ Tình báo bị bỏ qua và không tính là còn sót;
- runner không "làm theo hướng dẫn" ngay sau bước `intel` đã dừng.

Chỉ `no_march` kích hoạt. Bot **không** dừng sớm khi "Hành quân" vừa đầy (5/5), vì hộp tiếp tế không tốn quân đoàn,
nên vẫn có thể thử thêm một ghim trước khi nhận `no_march`.

## 4. Test

`tests/legacy/test_p13j_intel_guide.py`: 27 test, dùng đúng hai ảnh chủ (`tests/fixtures/p13j/`, thêm bằng
`git add -f`). Crop không có thanh nút dưới nên test dán mẫu `common/btn_to_world` vào đúng chỗ; vị trí khung của ảnh 2
không biết, nên test đặt ở ba chỗ.

| Cổng | Kết quả |
|---|---|
| `pytest` trong worktree | 1491 pass, 197 skip, **3 fail** ở `test_p13b_cham_do_khong_doi.py` |
| `pytest` trên bản sao tạm có `tests/fixtures` + `data/owner-feedback` của cây chính | 1591 pass, 112 skip, 0 fail |
| `tools/check_tutorial.py` (bản sao tạm) | 34/34, kết quả giống HEAD |
| `ruff` (cả hai lệnh), `mypy`, `lint-imports` | sạch |
| `main.py --check` | thiếu 16/262 ảnh mẫu, như trước |

Ba test fail trong worktree cũng fail trên bản HEAD sạch: chúng cần ảnh `data/owner-feedback/p13/quan_quan_tuan_bam_sai.png`
không có trong git.

## 5. Chưa làm / chưa chắc

- Chưa chạy live: hoạt ảnh tay nhấp nhô, cách nhận "màn đã đổi" (khoảng 5 giây sau khi bấm) chỉ kiểm bằng ảnh giả lập
  luồng. Nếu game phản ứng chậm hơn, chỗ bấm đúng có thể bị cấm đến hết lượt ghé.
- Mẫu bàn tay chỉ cắt từ một ảnh (khớp thêm được một khung tân thủ cũ). Ngưỡng cột sáng 50 hàng khá sát: ảnh 2 đạt
  62, chế độ xây dựng đạt tối đa 47 (đã loại riêng bằng nút X).
- **Ô đỏ trong thành phố** (`logs/inv/intel_unknown_target/20261126-i6.png`: lính ở ô lam, địch ở ô đỏ) chưa xử lý:
  `find_beam` không nhận khung này. Khác trước ở chỗ bot không còn bấm tọa độ cứng vào lính.
- Nhiều ảnh `intel_unknown_target` là popup "Phiến quân Lv.N"; ba ảnh có nút "Tấn công" tôi đo thì `intel/btn_attack`
  chỉ khớp 0,52–0,59. Chưa điều tra, nên làm ở việc sau.
