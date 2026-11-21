# Kiểm kê tài khoản trên 9 instance
Ngày: 2026-11-17 · Phương pháp: backup `.ldbk` từng máy → bật root tạm → boot → **chỉ đọc** prefs của game (in hash 10 ký tự, không in giá trị) → tắt → trả root về như cũ. **Không mở game.**
Dữ liệu gốc: `poc/logs/inventory.csv`, `poc/logs/inventory_global.csv`, `poc/logs/inventory_dirs.txt`.

## 1. Có 2 bản game khác nhau
| Bản | Package | Version | Cài lúc | Instance |
|---|---|---|---|---|
| Việt Nam | `com.ageofwarpath.globalwarzone.vn` | 2.5.16 | 2026-11-16 | #0, #1, #7, #8 |
| Global | `com.ageofwarpath.globalwarzone` | 3.6.0 | 2026-05-30 | #2, #3, #4, #5, #6 |

Bot hiện tại (`config.yaml` → `game_package`) dùng bản `.vn`.

## 2. Danh tính tài khoản (hash)
| Instance | Bản | JOY_ACCOUNT_ID | account_uuid | game_uid | Prefs sửa lần cuối | Nhóm |
|---|---|---|---|---|---|---|
| #0 MFarm00 | vn | 3efa16a001 | 374c221b7d | 54c1e8c977 | 2026-11-17 21:16 | **VN-1** |
| #1 MFarm01 | vn | c17651d4d1 | 36725aad82 | 00fea3e4f2 | 2026-11-17 01:50 | **VN-2** |
| #7 MFarm07 | vn | c17651d4d1 | 36725aad82 | 00fea3e4f2 | (PoC) | VN-2 (trùng #1) |
| #8 MFarm08 | vn | c17651d4d1 | 36725aad82 | 00fea3e4f2 | (PoC) | VN-2 (trùng #1) |
| #2 bn1/MFarm02 | global | f7c55cd5a9 | 996ceffaab | c61ec91601 | 2026-06-15 20:39 | **GL-1** |
| #6 bn2/MFarm06 | global | f7c55cd5a9 | 996ceffaab | c61ec91601 | 2026-06-15 20:39 | GL-1 (trùng #2) |
| #3 rose/MFarm03 | global | 36c97360fc | 969ea0c904 | f4b9345441 | 2026-05-30 23:06 | **GL-2** |
| #4 buonngu/MFarm04 | global | 36c97360fc | 969ea0c904 | f4b9345441 | 2026-05-30 23:06 | GL-2 (trùng #3) |
| #5 caydai/MFarm05 | global | 36c97360fc | 969ea0c904 | f4b9345441 | 2026-05-30 23:06 | GL-2 (trùng #3) |

**Theo dữ liệu đăng nhập lưu trên máy, 9 instance chỉ có 4 danh tính khác nhau:** VN-1, VN-2, GL-1, GL-2.
Các instance trong cùng nhóm có prefs giống hệt nhau, kể cả thời gian sửa đến từng phút. Đây là dấu hiệu instance được nhân bản sau khi đăng nhập.

⚠ **Chưa thể kết luận đây là số tài khoản thật.** Trên #2–#6, prefs không được sửa kể từ tháng 5–6, dù mỗi máy chiếm 11–21 GB. Có hai khả năng:
- (a) các máy bản Global không còn được dùng kể từ khi chuyển sang bản `.vn`; hoặc
- (b) game cho đăng nhập tài khoản khác ngay trong game (tên/mật khẩu JOY) mà không ghi vào các key này.
Cần bạn xác nhận.

## 3. Định danh thiết bị
- **ANDROID_ID giống nhau trên cả 9 instance** (`168e005665`), tức là tất cả đều nhân bản từ một máy gốc.
- Model, serial, MAC, IMEI khác nhau theo cấu hình LDPlayer từng máy.
- Hệ quả tốt: gom về 1 instance thì ANDROID_ID **không đổi**, đúng điều kiện đã test thành công ở #7 → #8.

## 4. Kích thước dữ liệu theo tài khoản
| Bản | Internal | External | Ghi chú |
|---|---|---|---|
| vn | 7.2–7.7 MB | 24 MB | |
| global | ~18 MB (10.7 MB là `code_cache`, có thể bỏ) | 20.9 MB (`il2cpp`) | |

→ Dung lượng 11–21 GB mỗi máy **không đến từ dữ liệu tài khoản**. Nó đến từ vmdk phình (chỉ tăng, không co), APK lặp lại và dữ liệu hệ thống.

## 5. Trạng thái sau kiểm kê
- Root: #0–#6 đã trả về `false` như cũ; #7, #8 vẫn `true` (instance thử nghiệm).
- Tất cả instance đã tắt.
- Backup `.ldbk` mới cho cả 9 máy: `E:\AOW-BOT\backups\*-inventory.ldbk` (tổng ~128 GB), cộng 2 bản `*-pre-poc.ldbk`.
