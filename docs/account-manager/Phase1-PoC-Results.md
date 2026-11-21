# Phase 1 — Proof of Concept: kết quả đo thực tế
Ngày: 2026-11-17 · Instance thử nghiệm: **#7 MFarm07** (`emulator-5568`) · Instance #0 không bị đụng tới.
Mọi số liệu dưới đây là **[ĐO]**; log gốc ở `poc/logs/`, script ở `poc/slot.sh`, `poc/ident.sh`, `poc/switch_test.sh`.

## 0. An toàn
| Bước | Kết quả |
|---|---|
| Backup toàn VM `#7` → `backups/MFarm07-pre-poc.ldbk` | 6.57 GB, 34.6 s |
| Bật root mode (`ldconsole modify --index 7 --root 1`) + boot | `su` OK, boot ~25 s |

## 1. Bố cục dữ liệu game (đã đo bằng root)
| Thành phần | Đường dẫn | Kích thước | Dùng chung? |
|---|---|---|---|
| APK (3 split) + oat | `/data/app/<pkg>-*/` | 983 MB | ✔ dùng chung |
| Internal CE data | `/data/user/0/<pkg>` | 7.2 MB (`files` 6.6 MB, prefs 80 KB, db 180 KB) | ✘ theo tài khoản |
| Internal DE data | `/data/user_de/0/<pkg>` | 32 KB | ✘ |
| External | `/data/media/0/Android/data/<pkg>` | 24 MB (21 MB là `global-metadata.dat`) | phần lớn giống nhau giữa các slot |
| OBB | — | không dùng | — |

**Trạng thái đăng nhập nằm hoàn toàn trong `shared_prefs/<pkg>.v2.playerprefs.xml`**: `JOY_ACCOUNT_ID`, `JOY_ACCOUNT_UNAME`, **`JOY_ACCOUNT_PASSWORD`**, `account_uuid`, `game_uid`, `device_uid`, `bindType`, `googleName`.
→ Slot backup **chứa thông tin xác thực** ⇒ phải mã hóa khi lưu (DPAPI/AES), không bao giờ log giá trị.

## 2. Option A — Multi-User
| Kiểm tra | Kết quả |
|---|---|
| `pm create-user poc_acc2` | OK → user 10 |
| `pm install-existing --user 10` | OK, **cùng codePath**, APK **không bị copy**; `/data` chỉ tăng ~3 MB |
| `am switch-user 10` | lệnh 0.35 s, user 10 RUNNING_UNLOCKED sau **14.4 s**; LDPlayer hiển thị đúng |
| Về user 0 / `stop-user -w 10` | 0.08 s / 2.8 s |
| **Mở game ở user 10** | ❌ **Game tự thoát** sau ~2 s: `LicenseClient` (Google Play Licensing) → `System.exit(0)` vì user 10 chưa có Google account sở hữu game |
| Giới hạn | `pm get-max-users` = 4 |

Hướng hợp lệ duy nhất: đăng nhập Google account trong user 10 và "cài" game qua Play Store (Play sẽ dùng lại APK). **Không bypass license check.** Dù làm được, A vẫn bị trần 4 tài khoản → chỉ là phương án phụ.

## 3. Option B — Managed Profile
Không thử nghiệm thêm: cùng trần 4 user + chỉ 1 profile/user + cùng vấn đề license → loại (như Phase 0).

## 4. Option C — Snapshot/Restore dữ liệu app (root mode)
### 4.1 Tài khoản khách có gắn thiết bị không?
`pm clear` → mở game → game tự tạo **tài khoản khách mới** (`JOY_ACCOUNT_ID`, `account_uuid`, `device_uid` đều khác).
⇒ Danh tính **không** gắn ANDROID_ID; nó nằm trong dữ liệu app. Hệ quả kép:
- ✔ Option C khả thi kể cả với tài khoản khách.
- ⚠ **Mất slot = mất vĩnh viễn tài khoản khách** (nếu chưa liên kết Google/Facebook/JOY). Backup slot là dữ liệu sống còn.

### 4.2 Snapshot / restore
| Thao tác | Kết quả |
|---|---|
| Snapshot (tar giữ uid/gid + manifest SHA-256 56 file) | 31.6 MB thô, **10.7 MB gzip**, 1.9–2.5 s |
| Restore (kèm tự snapshot rollback trước khi ghi) | **5.9–7.0 s**, checksum khớp 100%, owner `10065:10065`/`20065` và SELinux `app_data_file:s0:c65,c256,c512,c768` đúng |
| `am start -W` sau restore | 0.8–1.2 s (chưa tính game load ~vài chục giây) |
| License check sau restore | `License check succeeded` |
| 26/56 file giống hệt nhau giữa 2 slot (gồm file 21 MB) | dedupe theo hash → slot thực tế chỉ vài MB |

### 4.3 Test chuyển đổi A↔B
| Lượt | Kết quả |
|---|---|
| Lần 1 (script chưa khóa package), 6 lần chuyển | 3 đúng, 2 sai danh tính, 1 checksum fail → **rollback tự động thành công** |
| Lần 2 (script đã gia cố), **10 lần chuyển** | **10/10 PASS**, danh tính đúng, game vào thẳng trong game |

**Nguyên nhân lỗi lần 1 (log `ActivityManager`):** có nguồn khác mở game trong lúc đang ghi dữ liệu: một lần bấm icon trên launcher lúc 22:01:19, một script cũ còn sót, và Android tự khởi động lại `firebase MessageForwardingService`. Tiến trình game mới giữ SharedPreferences cũ trong RAM rồi ghi đè lên dữ liệu vừa restore. Đây chính là kịch bản "corruption" phải chống.
**Cách khắc phục đã kiểm chứng:**
1. `pm disable-user` trong suốt thời gian ghi, nên launcher, FCM, alarm và job đều không mở được game.
2. Kiểm tra mọi tiến trình theo **uid** của app, không chỉ theo tên.
3. Verify manifest SHA-256 sau khi ghi; sai thì rollback.
4. `pm enable` chỉ sau khi verify OK.

## 5. Kết luận PoC
| Metric | Mục tiêu | Option C (đo) |
|---|---|---|
| Số tài khoản | 10–30+ | không giới hạn kỹ thuật (mỗi slot ~11 MB gzip trước dedupe) |
| APK duplication | tối thiểu | 0 (1 bản 983 MB) |
| Isolation | 100% | 10/10 lần chuyển đúng danh tính |
| Switching (restore) | nhanh | ~6–7 s + thời gian game load |
| Corruption | 0 | 1 lần phát hiện ở script v1, rollback thành công; v2 = 0/10 |
| Instances | 1 | 1 |

**Đề xuất: chọn Option C (root mode của LDPlayer) làm cơ chế chính.** Option A chỉ giữ làm phương án phụ (≤4, cần Google account mỗi user).

## 6. Ràng buộc từ chủ dự án (2026-11-17)
**Mọi tài khoản đều là tài khoản local theo thiết bị (khách), không liên kết Google/Facebook, và sẽ không thêm tài khoản liên kết.** Xóa dữ liệu app là mất tài khoản vĩnh viễn. Hệ quả cho thiết kế:
- Slot = **bản duy nhất** của tài khoản. Không có thao tác nào được phép xóa slot cuối cùng hoặc chạy `pm clear` mà chưa có slot đã verify.
- Mỗi slot phải có ≥2 bản sao trên 2 ổ đĩa, kiểm tra checksum định kỳ, mã hóa khi lưu.
- Trước khi ghi đè, luôn lưu lại dữ liệu đang có trên máy (auto-rollback). Bản rollback chỉ được dọn khi slot đích đã verify và bản trước đó đã có ≥2 bản sao.
- Tài khoản gốc của #7 (`guestA` = `base7` + 40 s chơi) đã được trả lại vào #7 và sao lưu ở `backups/accounts/MFarm07-original` (E:) và `D:\AOW-account-backups\MFarm07-original`.

## 7. Test chuyển tài khoản sang instance khác (#7 → #8)
| Bước | Kết quả [ĐO] |
|---|---|
| Backup `#8` → `backups/MFarm08-pre-poc.ldbk` | 6.58 GB, 38 s; bật root, boot OK |
| **Phát hiện:** tài khoản game trên #8 **trùng với tài khoản gốc của #7** (cùng `JOY_ACCOUNT_ID`, `account_uuid`, `device_uid`, cùng ANDROID_ID bên trong Android) | #8 là bản sao ổ dữ liệu của #7; 42/56 file giống hệt |
| Định danh thiết bị #7 vs #8 | model, serial, MAC, IMEI **khác**; ANDROID_ID **giống** |
| Snapshot tài khoản gốc #8 (`orig8`) + 2 bản sao (E:, D:) | OK, checksum khớp |
| Restore `guestB` (tạo trên #7) lên #8 | restore 19.8 s (lần đầu, có tạo rollback), verify khớp |
| Mở game trên #8 | `License check succeeded`, đúng `JOY_ACCOUNT_ID`/`account_uuid` của B, **`game_uid` không đổi**, vào thẳng game, không có màn đăng nhập |
| Trả tài khoản gốc về #8 | verify khớp, game chạy đúng tài khoản gốc |

**Kết luận:** tài khoản khách mang được sang instance có model, serial, MAC và IMEI khác mà không bị đăng xuất hay bị tạo tài khoản mới.
**Giới hạn của test:** ANDROID_ID của #7 và #8 giống nhau nên **chưa kiểm chứng được trường hợp ANDROID_ID khác**. `guestB` mới ở màn hướng dẫn, nên chỉ chứng minh được phiên đăng nhập, chưa chứng minh tài khoản có tiến trình chơi lâu. Khi gom tài khoản thật về 1 instance, mỗi tài khoản phải giữ slot gốc (2 bản sao) và vẫn còn trên instance cũ cho đến khi đã chạy ổn định trên instance mới.

**Công cụ:** `slot.sh` đã thêm bước đổi uid/gid khi appId của app ở instance nguồn và đích khác nhau. Lần test này cả hai đều là 10065, nên bước đổi uid chưa được chạy thật.

## 7b. Còn mở
- Tài khoản có ANDROID_ID khác: các instance #0–#6 có thể có ANDROID_ID riêng; cần đo khi gom.
- Có thể còn instance khác cũng là bản sao (cùng một tài khoản). Cần kiểm kê danh tính tài khoản trên cả 9 instance trước khi gom, để không đếm trùng hoặc ghi đè nhầm.
- Kích thước slot của tài khoản chơi lâu (cache asset có thể lớn hơn).
- Chưa test với 10–30 slot và chưa test chuyển đổi khi game đang trong trận hoặc đang ghi dở.
- Cách thức áp dụng lên instance chính (#0), vì cần bật root ở đó.

## 8. Trạng thái hiện tại của #7 (cần dọn hoặc giữ)
- Root mode: **bật**. Screen timeout: đặt vô hạn.
- User 10 `poc_acc2`: còn tồn tại (đã stop).
- Dữ liệu game: **đã trả về tài khoản gốc `guestA`** (verify khớp). `guestB` là tài khoản khách bỏ đi, chỉ để test. `base7`/`guestA`/`guestB` + 21 slot `_rollback_*` nằm trong `poc/slots` (804 MB). Cần chính sách giữ N rollback gần nhất.
- #8: root mode **bật**, screen timeout vô hạn, đang chạy, dữ liệu game = tài khoản gốc (`orig8`, verify khớp). Backup VM: `backups/MFarm08-pre-poc.ldbk`.
- Có thể đưa toàn bộ #7 về trạng thái trước PoC: `ldconsole restore --index 7 --file backups/MFarm07-pre-poc.ldbk`.
