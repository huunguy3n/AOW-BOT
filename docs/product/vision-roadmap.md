# Định hướng sản phẩm & lộ trình — AOW-BOT
Cập nhật: 2026-11-18

## 1. Tầm nhìn
**Một máy Windows, một instance LDPlayer, nhiều tài khoản Age of Warpath tự farm 24/7, an toàn tuyệt đối với dữ liệu tài khoản và không tiêu kim cương.**

Người dùng chỉ mở web quản lý: xem tài nguyên, lực chiến, hành quân của từng tài khoản; bật/tắt tính năng; can thiệp khi bot báo kẹt. Mọi việc lặp lại (nhận quà, nghiên cứu, huấn luyện, gửi quân, nhiệm vụ, tân thủ cho tài khoản mới) do bot làm.

## 2. Nguyên tắc định hướng (không thương lượng)
| # | Nguyên tắc | ADR |
|---|---|---|
| 1 | **Không bao giờ mất tài khoản.** Dữ liệu app = tài khoản; ≥2 bản sao / 2 ổ, rollback trước mọi ghi đè | [0010](../adr/0010-an-toan-tai-khoan-khach.md) |
| 2 | **Không tiêu kim cương, không đi đường trả phí** (trừ khiên, có trần) | [0008](../adr/0008-chinh-sach-kim-cuong.md) |
| 3 | **Chỉ nhìn và chạm như người chơi** — không hack bộ nhớ, gói tin, license | [0001](../adr/0001-dieu-khien-qua-adb-va-nhan-dien-anh.md) |
| 4 | **Hỏng một bước không hỏng cả lượt**; kẹt thì lưu ảnh và báo, không đoán bừa | [0004](../adr/0004-pipeline-module-co-lap-loi.md) |
| 5 | **Quyết định dựa trên số đo**, làm theo phase, chủ dự án duyệt | [0012](../adr/0012-lam-viec-theo-giai-doan.md) |

## 3. Hiện trạng (2026-11-18)

### Bot farm
| Tính năng | Trạng thái |
|---|---|
| Web quản lý, đọc tài nguyên / hành quân, OCR | ✅ xong |
| Nhận quà (thư, điểm danh, VIP, rương, quà nổi), nhặt tài nguyên thành phố | ✅ xong |
| Nghiên cứu nhánh thu thập, huấn luyện T3 theo nhu cầu gửi quân | ✅ xong |
| Gửi quân đi mỏ (ưu tiên loại/cấp, kiểm tra trữ lượng ≥ tải trọng) | ✅ xong |
| Nhiệm vụ Chương/Chính → xây nâng cấp (nhà chính ≤ lv22), liên minh (vàng, trợ giúp) | ✅ xong |
| Nhiệm vụ chính + chiến dịch (đánh khi dự đoán thắng) + chấm đỏ | ✅ xong |
| Lái quân trận chạy đường (sendevent) | ✅ xong, đang tinh chỉnh |
| Tân thủ (`tutorial`) | 🟡 đang làm — đã chạy thử 27 lượt trên #5, còn kẹt/thua/max_steps ở vài điểm |
| Phòng thủ (khiên khi bị tấn công) | 🟡 code xong, **thiếu ảnh mẫu** `defense/alert_attack.png` |
| Tập kết Phản quân Cơ giáp | 🟡 code xong, **thiếu ảnh mẫu** `rebels/rally_mech.png`, `btn_join.png` |
| Một số ảnh mẫu tình huống hiếm (`ally/btn_help_all`, `daily/claim_1`, `daily/chapter_claim`) | 🟡 chờ tình huống xuất hiện để cắt |

### Account Manager
| Phase | Nội dung | Trạng thái |
|---|---|---|
| 0 | Khảo sát khả thi (read-only), so sánh Option A/B/C/D | ✅ xong |
| 1 | PoC trên #7: Option A thất bại (license), Option C 10/10; chuyển chéo #7→#8 | ✅ xong |
| 1b | Kiểm kê danh tính 9 instance: 4 danh tính, 2 bản game | ✅ xong |
| 2+ | Xem lộ trình bên dưới | ⏸ chờ chủ dự án duyệt |

## 4. Lộ trình

### Giai đoạn gần (ổn định bot)
1. **Hoàn thiện tân thủ** — xử lý các điểm kẹt trong `logs/shots/*tutorial_*`, bổ sung ảnh mẫu còn thiếu, đạt chạy hết tân thủ không cần người can thiệp trên tài khoản mới; sau đó tự chuyển sang `mainquest`.
2. **Cắt ảnh mẫu còn thiếu** cho phòng thủ và Phản quân ngay khi tình huống xuất hiện (`python tools/snap.py shot … / cut …`).
3. **Độ tin cậy vòng lặp** — thống kê lỗi theo bước trên web; tự phát hiện "đứng yên quá lâu" và khởi động lại game.
4. **Bản Global (3.6.0)** — quyết định giữ hay bỏ các instance #2–#6 (bot hiện chỉ cấu hình bản `.vn`).

### Giai đoạn giữa (Account Manager → sản phẩm)
Mỗi bước cần chủ dự án duyệt trước (ADR-0012).

| Phase | Nội dung | Tiêu chí xong |
|---|---|---|
| 2 | **Slot store an toàn**: mã hóa slot (DPAPI/AES), 2 bản sao E:/D:, kiểm tra checksum định kỳ, dedupe theo hash file, chính sách giữ N rollback, journal để khôi phục sau crash | Script/thư viện qua test 10–30 slot trên #7, không mất slot nào |
| 3 | **Test ANDROID_ID khác nhau** và tài khoản chơi lâu (cache lớn); đo kích thước slot thật | Có số đo; chuyển được tài khoản thật sang instance khác ANDROID_ID |
| 4 | **Tích hợp runner**: vòng lặp theo **tài khoản** thay vì instance (đổi slot giữa các lượt), cấu hình/trạng thái khóa theo tài khoản (ADR-0002, ADR-0005 cần ADR mới) | 1 instance chạy hết các tài khoản test trong 1 vòng |
| 5 | **Gom tài khoản thật** theo danh tính (VN-1, VN-2, GL-1, GL-2…), từng tài khoản một; giữ instance cũ tới khi ổn định | Mọi danh tính chạy trên 1 instance ≥ N ngày, rồi mới thu hồi instance cũ |
| 6 | **Thu hồi dung lượng**: xóa/compact instance cũ (chỉ sau khi có `.ldbk` + slot 2 bản sao) | Dung lượng giảm từ ≈121 GB về ~1 instance + N slot |

### Giai đoạn xa (ý tưởng, chưa cam kết)
- Web: trang quản lý slot (danh sách tài khoản, lần chạy cuối, snapshot, khôi phục 1 chạm).
- Lịch chạy theo tài khoản (ưu tiên tài khoản có hành quân sắp về, sự kiện có giờ).
- Thông báo ra ngoài khi bị tấn công / kẹt (chỉ khi chủ dự án muốn; mặc định không gửi dữ liệu ra ngoài).
- Tái dùng mô hình "ghi mẫu → hàm quyết định thuần → replay offline" (ADR-0011) cho sự kiện mới.

## 5. Ngoài phạm vi (không làm)
- Can thiệp bộ nhớ, gói tin, APK, license check, anti-cheat.
- Tự tiêu kim cương / mua gói / nạp thẻ.
- Chat, tương tác xã hội thay người chơi.
- Liên kết tài khoản Google/Facebook (chủ dự án đã quyết định không liên kết).
- Mở web quản lý ra Internet.

## 6. Câu hỏi mở
| Câu hỏi | Ảnh hưởng |
|---|---|
| Có đăng nhập tài khoản khác ngay trong game (JOY) không, hay mỗi instance chỉ 1 tài khoản? | Số tài khoản thật cần gom |
| Instance bản Global #2–#6 còn dùng không? | Có cần hỗ trợ 2 package / 2 bộ ảnh mẫu |
| `config.yaml` đã bỏ #1, #7, #8 khỏi `instances` (2026-11-17) — #7/#8 còn giữ làm máy test? | Phạm vi PoC Phase 2 |
| Bật root mode trên instance chính có chấp nhận được không? | Điều kiện tiên quyết Phase 4–5 |
| Số tài khoản mục tiêu (10? 30?) | Dung lượng, thời gian 1 vòng |

## 7. Chỉ số theo dõi
- Tỉ lệ lượt chạy không lỗi theo bước (`last_error` trong `data/state.json`).
- Thời gian 1 vòng / số tài khoản.
- Số lần đổi slot thành công / rollback (Account Manager) — mục tiêu **0 lần mất dữ liệu**.
- Tân thủ: tỉ lệ hoàn thành không can thiệp.
- Kim cương tiêu / ngày / tài khoản (chỉ cho khiên, ≤ `gem_cap_daily`).
