# N6 — Nhận vật phẩm: khảo sát & ảnh mẫu (#5)
Ngày: 2026-11-18 · Kế hoạch: [ke-hoach-hoan-thien-bot.md](../product/ke-hoach-hoan-thien-bot.md) · Trước đó: [02-tan-thu-loi.md](02-tan-thu-loi.md)

## 1. Khảo sát các nguồn quà trên thành phố (#5, tài khoản mới, Xưởng kiến trúc cấp 3)
| Biểu tượng | Nội dung | Kết luận |
|---|---|---|
| **Quà** ($, chấm đỏ) | Toàn gói trả phí (Thẻ tháng, Thẻ tuần ₫125000…) | Không đụng tới. Chấm đỏ là quảng cáo |
| **Phúc lợi** (TT phúc lợi) | Chúc phúc tân thủ, **Điểm danh 30 ngày**, Dưỡng Tướng, Bậc thầy chiến đấu, Thưởng online, **Quà đăng nhập**… | `notify.welfare` đã xử lý (nút "Nhận"). **Thiếu:** ô quà có viền xanh phát sáng, không có nút → đã thêm (§2) |
| **Buổi lễ** (Celebration) | Ngày 1–5 × 3 mục con (Đăng nhập / Tăng cấp Xưởng / Khiêu chiến Chiến dịch), nút "Nhận" | **Chưa có bước nào xử lý** → tuyến mới `celebration` (§2) |
| Rương vật tư chiến tranh | Nút "Miễn phí" bị **khóa** (phải mua gói ₫25000 trước) | Không có gì nhận được → bỏ tuyến `free_chest` |
| Nạp đầu, Công nhân | Trả phí | Không đụng tới |
| Hộp quà cạnh Tổng thư ký | Quà theo giờ (đếm ngược 2 h) | Chưa tới giờ → **chưa cắt được** `rewards/city/claim_1` |
| VIP → Rương Ngày VIP 0 | "Nhận" chỉ mở bảng **Kích hoạt VIP** (dùng vật phẩm VIP 24h hoặc mua Thẻ tháng) | Trước đây bot bấm, bảng hiện rồi bị đóng, nhưng vẫn **ghi là đã nhận** → đã sửa (§2) |

## 2. Thay đổi
| Việc | File |
|---|---|
| Ô quà phát sáng (cột "Miễn phí" của Quà đăng nhập / Chúc phúc tân thủ): nhận diện viền xanh ngọc theo màu, chạm thẳng vào ô | `bot/badges.py` `glow_tiles()`, `bot/modules/notify.py` `claim_content()` |
| Tuyến **`celebration`** (Buổi lễ): ảnh mẫu `open_1`, `claim_1`; **hai hàng tab lồng nhau theo chấm đỏ** (`rewards.dot_tabs.celebration` dạng danh sách các hàng) | `bot/modules/rewards.py` `dot_strips()`, `config.yaml`, `templates/rewards/celebration/` |
| Bỏ `signin`, `free_chest` khỏi `rewards.routes` (lý do ở §1) | `config.yaml` |
| Vòng nhận quà (`Ctx.claim_loop`, dùng chung `rewards`/`daily`/`notify`): bấm "Nhận" mà hiện **bảng khác có nút X** (không phải bảng thưởng) → đóng, đánh dấu nút, **không tính, không bấm lại**, không chọn gì trong bảng | `bot/ctx.py` |
| Hộp thoại "Mạng ngoại lệ" lúc vào game → "Thử lại" (`common/btn_net_retry`) | `bot/ctx.py` `POPUP_CLOSERS` |
| Thống kê: ảnh mẫu **tùy chọn** (`Vision.has()`, `btn_reward_close`, `btn_help`, `btn_free`) không còn làm bước bị ghi "thiếu ảnh mẫu" | `bot/vision.py`, `bot/ctx.py` |

## 3. Kết quả chạy thật trên #5 [ĐO]
| Lượt | Nhận được |
|---|---|
| Thử riêng `notify.hub` | TT phúc lợi **18 lần**; thêm ô phát sáng **2** (Quà đăng nhập ngày 1–2, đã có dấu tích) |
| Thử riêng tuyến `celebration` | **6 lần**, mọi chấm đỏ của Buổi lễ biến mất ("Đã nhận") |
| `--modules rewards,notify,daily` (22:19) | thư 1, VIP 1 (sai — xem §1), phúc lợi 8, hoạt động 0, tướng 8, chiêu mộ 10 lần bằng phiếu |
| Lượt sau khi sửa (22:28) | VIP **0** (bảng Kích hoạt VIP được đóng, không chọn gì), không còn gì để nhận |

- Kim cương **2010 → 2210** (nhận từ quà), không tiêu.
- Lực chiến **111.906 → 122.577** (tướng + quà) → vượt mốc 117.501, `mainquest` hết tạm dừng.
- `python main.py --check`: **thiếu 29/155** (trước 33).

## 4. Còn lại
- `rewards/city/claim_1`: chờ hộp quà theo giờ cạnh Tổng thư ký đến hạn (tình huống phải xuất hiện).
- `common/btn_free`, `btn_help`, `btn_reward_close`, `msg_insufficient`: chưa gặp trong lúc khảo sát (cần tăng tốc miễn phí <5 phút, có liên minh, thiếu tài nguyên) → cắt khi gặp.
- **Quyết định (chủ dự án, 2026-11-18):** **không** dùng vật phẩm "VIP 24 tiếng" để kích hoạt VIP. Rương Ngày VIP chỉ nhận khi VIP đã được kích hoạt sẵn; bảng "Kích hoạt VIP" luôn được đóng, không chọn gì.
- Chưa chạy lại trên #0 (tài khoản cũ) — giao diện quà có thể khác theo cấp/VIP.

## 5. N7 — chạy nhiều lượt trên #0 + #5, đi hết chấm đỏ (2026-11-18 tối)
Lượt 1 tự động (#0 + #5, 22:32–22:44) chạy ổn: #0 nhận thư 1, Buổi lễ 7, phúc lợi 20, tình báo 3, NV 1; #5 phúc lợi 6. Sau đó chủ dự án chỉ ra các chấm đỏ bot **chưa bấm** → dừng vòng tự động, sửa từng chỗ trên #5:

| Chấm đỏ | Vấn đề | Sửa |
|---|---|---|
| Chiêu mộ → nút **"Miễn phí"** | Bot chỉ biết "Chiêu mộ 1 lần"/"10 lần" → bỏ sót lượt miễn phí trong ngày | Ảnh mẫu `recruit/btn_free`, ưu tiên khi nút có màu. **Đo:** nhận 2 lượt (cao cấp + thường) |
| Tướng → nút **nâng sao** (mũi tên xanh cạnh hàng sao) | Bot chỉ bấm "Tăng cấp" | `hero_detail()`: nút sao có chấm đỏ → "Tăng sao" có chấm đỏ → bấm, đóng màn thành công. **Đo:** 6 lần tăng sao |
| Tướng → icon **sách** (Câu chuyện) | Chưa xử lý | `hero_story()`: tab I–IV có chấm đỏ → chạm **hộp vàng** góc tranh → 20 kim cương/lần. **Đo:** 3 lần |
| Danh sách tướng | Chỉ vào tướng có mũi tên xanh | Vào lần lượt mọi thẻ có chấm đỏ |
| Phúc lợi → **Điểm danh 30 ngày** | Ô có chữ "Nhận" xanh + viền vàng, không có nút | `badges.nhan_tiles()` (đo trên ảnh chủ dự án gửi) → bảng "Phần thưởng hằng ngày" → **chỉ** "Nhận Phần Thưởng Cơ Bản", không bao giờ "Nâng cấp VIP" |
| Hoạt động → icon **lịch** | Chấm đỏ "mục mới" | Mở lịch tuần rồi đóng → hết chấm |
| Sự kiện cột phải: **Sứ mệnh** (bảng ghép hình) | Chưa có bước nào | `notify.events()`: ô có chấm đỏ → bảng nhiệm vụ → "Nhận" (`event/btn_popup_claim`) → X. **Đo:** 3 × 10 kim cương |
| Sự kiện cột phải: **Người mới — Điểm danh 7 ngày** | Như trên, nhưng ô nhận ngay khi chạm, thưởng là **tướng** (hoạt ảnh mở khóa + "Xác nhận") | Chờ `common/btn_confirm_hero` (thêm vào bộ đóng popup chung). **Đo:** nhận Tank Ảo Ảnh |
| **Hộp quà nổi trên công trình** (`rewards/city`) | Bong bóng trong suốt → ảnh mẫu không khớp khi đổi nền | `badges.city_bubbles()` theo màu + hình hộp quà (loại bong bóng tài liệu, drone, **tăng tốc**, xe "Thu thập"). Quét 60+ ảnh cũ: chỉ trúng hộp quà. **Đo:** nhận 2 hộp |
| Tuyến quà chỉ mở khi icon có chấm đỏ | Mở bảng vô ích mỗi lượt | `rewards.require_dot` (mặc định bật) |

**Lượt kiểm chứng cuối trên #5 (22:59–23:02) [ĐO]:** không lỗi; các tuyến không có chấm đỏ được bỏ qua; chiêu mộ miễn phí 1, tăng sao 2. Kim cương **2210 → 2800** (+590, toàn bộ từ quà; không tiêu). Lực chiến **122.577 → 207.723**.

**Chấm đỏ còn lại trên #5 (cố ý / chưa rõ):** "Quà" (gói trả phí, không đụng), nút búa (xây — việc của `quests`/`build`), "Hoạt động" 2 (đã vào, không tab nào có chấm đỏ, chưa rõ nguồn → cần ảnh khi gặp lại).

Ảnh hồi quy: `tests/fixtures/rewards/` (điểm danh 30 ngày, bong bóng quà, bong bóng tăng tốc không phải quà).
