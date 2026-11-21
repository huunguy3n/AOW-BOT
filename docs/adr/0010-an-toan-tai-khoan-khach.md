# ADR-0010: Tài khoản khách = dữ liệu app: quy tắc bảo toàn

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-11-17
- **Liên quan:** ADR-0009, `backups/`, `poc/slot.sh`

## Bối cảnh
Chủ dự án xác nhận (2026-11-17): mọi tài khoản là **tài khoản khách cục bộ**, không liên kết Google/Facebook và sẽ không liên kết. PoC chứng minh `pm clear` tạo tài khoản khách **mới**. ⇒ Mất dữ liệu app = mất tài khoản vĩnh viễn, không có cách khôi phục từ server.

## Quyết định
1. **Cấm** `pm clear`, gỡ app, xóa slot, ghi đè dữ liệu app trên tài khoản thật nếu chưa có snapshot **đã verify, ≥2 bản sao trên 2 ổ** (E:\AOW-BOT\backups và D:\AOW-account-backups).
2. Mọi thao tác ghi đè luôn tạo **rollback** trước. Bản rollback chỉ được dọn khi slot đích đã verify **và** bản trước đó đã có ≥2 bản sao.
3. Không bao giờ xóa slot cuối cùng của một danh tính.
4. Trước thao tác rủi ro trên cả VM: `ldconsole backup` → `.ldbk`.
5. Khi gom về 1 instance: tài khoản vẫn giữ nguyên trên instance cũ cho tới khi đã chạy ổn định trên instance mới.
6. Không log/in giá trị `JOY_ACCOUNT_*`, `account_uuid`, `device_uid` — chỉ hash 10 ký tự. Slot lưu trữ phải mã hóa (DPAPI/AES) khi đưa vào sản phẩm.
7. Thử nghiệm chỉ trên instance đã thống nhất (#7, #8) và với tài khoản khách bỏ đi; hỏi trước khi đụng instance khác.

## Hệ quả
- Tốt: không có đường nào mất tài khoản do bot/công cụ.
- Xấu: tốn dung lượng (đã ~128 GB `.ldbk` + slot); thao tác chậm hơn vì verify/rollback.
- Việc phải làm: chính sách giữ N rollback gần nhất; kiểm tra checksum định kỳ các bản sao.
