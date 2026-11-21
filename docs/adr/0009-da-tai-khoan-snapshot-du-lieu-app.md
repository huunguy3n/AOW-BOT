# ADR-0009: Đa tài khoản bằng snapshot/restore dữ liệu app (Option C)

- **Trạng thái:** Chấp nhận (PoC xong; chưa triển khai lên instance chính)
- **Ngày:** 2026-11-17
- **Liên quan:** `docs/account-manager/*`, `poc/slot.sh`, `poc/ident.sh`, `poc/switch_test.sh`, ADR-0010

## Bối cảnh
9 instance chiếm ≈121 GB (vmdk chỉ phình), APK ~0.87–0.98 GB lặp lại mỗi máy. Mục tiêu: 10–30+ tài khoản trên **1 instance, 1 APK**.

Kết quả đo ([Phase 0](../account-manager/Phase0-Technical-Feasibility-Report.md), [Phase 1](../account-manager/Phase1-PoC-Results.md)):
- Trạng thái đăng nhập nằm hoàn toàn trong `shared_prefs/<pkg>.v2.playerprefs.xml`; danh tính **không** gắn ANDROID_ID.
- Slot: ~31.6 MB thô / 10.7 MB gzip; snapshot ~2 s, restore 6–7 s; license check vẫn OK.
- 10/10 lần chuyển đúng danh tính sau khi gia cố; chuyển chéo #7→#8 (khác model/serial/MAC/IMEI) OK.

## Quyết định
Dùng **Option C2**: bật root mode chính thức của LDPlayer, snapshot/restore **nguyên trạng bit-for-bit** 3 thư mục `/data/user/0/<pkg>`, `/data/user_de/0/<pkg>`, `/data/media/0/Android/data/<pkg>` bằng `tar` giữ uid/gid, `restorecon`, manifest SHA-256. Quy trình ghi bắt buộc:
1. `pm disable-user` package (chặn launcher/FCM/alarm mở game) → `am force-stop` → chờ hết tiến trình **theo uid**.
2. Snapshot rollback dữ liệu đang có.
3. Ghi slot đích → chown/restorecon → verify manifest.
4. OK → `pm enable`, mở game, kiểm tra danh tính. Sai → rollback tự động.

## Phương án đã cân nhắc
- **A — Android multi-user:** APK dùng chung, cô lập bởi OS; nhưng trần 4 user và game tự thoát ở user phụ do Google Play `LicenseClient`. Không bypass license → chỉ là phương án phụ.
- **B — Managed profile:** 1 profile/user, cùng trần 4, cần DPC riêng. Loại.
- **C1 — `adb backup/restore`:** không cần root nhưng phải bấm xác nhận, deprecated, có thể bỏ sót file. Loại.
- **D — Manager Windows:** không phải cơ chế cô lập mà là lớp điều phối bắt buộc trên C.

## Hệ quả
- Tốt: không giới hạn kỹ thuật số tài khoản; 0 APK lặp; tích hợp được vào runner để lặp theo tài khoản.
- Xấu: cần root mode trên instance chạy thật; slot chứa thông tin xác thực → phải mã hóa khi lưu; ANDROID_ID khác nhau giữa instance nguồn/đích **chưa kiểm chứng**; tài khoản chơi lâu (cache lớn) chưa đo.
- Kiểm kê cho thấy 9 instance chỉ có **4 danh tính** (VN-1, VN-2, GL-1, GL-2) và 2 bản game (VN 2.5.16, Global 3.6.0) → gom phải theo danh tính, không theo instance.
