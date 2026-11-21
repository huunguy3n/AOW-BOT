# Phase 0 — Technical Feasibility Report
**LDPlayer Multi-Account Manager · Age of Warpath: Global Warzone (VN)**
Ngày khảo sát: 2026-11-17 · Phương pháp: chỉ chạy lệnh ADB **read-only** trên instance 0 (đang chạy game). Không tạo user, không đổi cấu hình, không đụng dữ liệu game.

Quy ước: **[ĐO]** = số liệu đo thực tế trong phiên này. **[CHƯA ĐO]** = cần PoC/root để đo, không được dùng như số thật. **[LÝ THUYẾT]** = hành vi theo mã nguồn AOSP 9, cần kiểm chứng trên LDPlayer.

---

## 1. Kết quả khảo sát môi trường

### 1.1 LDPlayer / host
| Hạng mục | Giá trị | Nguồn |
|---|---|---|
| LDPlayer path | `D:\LDPlayer\LDPlayer9\` (adb.exe, ldconsole.exe) | [ĐO] |
| Số instance hiện có | 9 (index 0–8, MFarm00–08) | [ĐO] `ldconsole list2` |
| Instance đang chạy | #0 MFarm00 — ADB `emulator-5554` = `127.0.0.1:5555` (cùng 1 máy) | [ĐO] |
| Cấu hình #0 | 4 CPU, 4096 MB RAM, 540×960 @240dpi, **rootMode=false**, adbDebug=1 | [ĐO] `leidian0.config` |
| Hệ thống dùng chung | `system.vmdk` 1.74 GB (dùng chung mọi instance) | [ĐO] |

**Dung lượng thực tế 9 instance (data.vmdk + sdcard.vmdk):**

| VM | GB | VM | GB | VM | GB |
|---|---|---|---|---|---|
| leidian0 | 16.14 | leidian3 | 21.36 | leidian6 | 11.72 |
| leidian1 | 6.60 | leidian4 | 20.29 | leidian7 | 6.57 |
| leidian2 | 16.20 | leidian5 | 15.85 | leidian8 | 6.58 |

**Tổng ≈ 121.3 GB** [ĐO]. Lưu ý: bên trong #0 chỉ dùng 6.0 GB `/data` nhưng `data.vmdk` = 15.29 GB → vmdk động **chỉ phình, không tự co** [ĐO + đặc tính VirtualBox]. Đây là một nguồn lãng phí lớn ngoài việc trùng APK.

### 1.2 Android
| Hạng mục | Giá trị | Nguồn |
|---|---|---|
| Android / SDK | 9 / 28, build `user/release-keys`, `ro.debuggable=0` | [ĐO] |
| ABI | x86_64 (+ARM translation) | [ĐO] |
| Root | **Không** (`su` không tồn tại; LDPlayer rootMode=false) | [ĐO] |
| `pm get-max-users` | **4** (`fw.max_users` không đặt → dùng giá trị trong framework res) | [ĐO] |
| Switchable users | `Supports switchable users: true` | [ĐO] `dumpsys user` |
| Features | `managed_users`, `device_admin`, `backup` đều có | [ĐO] |
| Lệnh có sẵn | `pm create-user [--profileOf] [--managed]`, `pm remove-user`, `pm install-existing`, `am switch-user/start-user/stop-user` | [ĐO] `pm help`, `am help` |
| Backup Manager | đang **disabled**; có `LocalTransport` | [ĐO] `bmgr` |
| RAM khách | MemTotal 3.85 GB, MemAvailable ~2.6 GB khi game chạy | [ĐO] |

### 1.3 Game package
| Hạng mục | Giá trị | Nguồn |
|---|---|---|
| Package | `com.ageofwarpath.globalwarzone.vn` v2.5.16 (516) | [ĐO] |
| targetSdk / minSdk | 35 / 26 | [ĐO] |
| Flags | `ALLOW_BACKUP`, `ALLOW_CLEAR_USER_DATA` | [ĐO] |
| Installer | Google Play (`com.android.vending`) | [ĐO] |
| APK (split) | base 24.5 MB + **UnityDataAssetPack 796.9 MB** + config.x86_64 44.8 MB = **≈ 866 MB** | [ĐO] |
| OBB | Không dùng (thư mục rỗng) | [ĐO] |
| External data | `/sdcard/Android/data/<pkg>/files` = 24 MB (`AssetBundles/1000516`, `il2cpp/Metadata`) | [ĐO] |
| Internal data | `/data/user/0/<pkg>` — **[CHƯA ĐO]** (cần root) | — |
| SDK nhận diện | `com.ltsdk.union` (SDK đăng nhập/nhà phát hành), Firebase, Facebook, Adjust, Helpshift, Amazon | [ĐO] tên component |
| Quyền liên quan định danh | READ_PHONE_STATE, AD_ID (granted), ACCESS_WIFI_STATE | [ĐO] |
| Google account trên máy | 2 tài khoản `com.google` | [ĐO] |

### 1.4 Hệ quả quan trọng
1. **APK ~866 MB là phần dùng chung được** — mỗi instance hiện đang lặp lại phần này. Dữ liệu khác nhau thực sự theo tài khoản (internal data + 24 MB external) phải đo ở PoC.
2. **Giới hạn 4 user** là rào cản cứng của Option A nếu không thay đổi `fw.max_users` (cần root).
3. **Không có root** → không đọc/sao chép được `/data/user/0/<pkg>` trực tiếp. Có 2 con đường: bật root của LDPlayer (công tắc chính thức trong Settings) hoặc `adb backup` (game cho phép `ALLOW_BACKUP`).
4. **Câu hỏi then chốt chưa biết:** SDK `ltsdk.union` lưu phiên đăng nhập ở đâu và có gắn với ANDROID_ID / Google account / Advertising ID hay không. Câu trả lời quyết định Option C có dùng được hay không.

---

## 2. Phân tích từng phương án

### Option A — Android Multi-User
**Cơ chế:** mỗi tài khoản game = 1 Android user. `pm install-existing --user N <pkg>` bật package đã cài cho user N **không copy APK** — code dùng chung `/data/app/<pkg>-*/`, mỗi user chỉ có `/data/user/N/<pkg>` và `/storage/emulated/N/Android/data/<pkg>` riêng [LÝ THUYẾT — AOSP PackageManagerService].

| Tiêu chí | Đánh giá |
|---|---|
| Hỗ trợ trên máy này | Có lệnh + feature [ĐO]; chưa tạo thử user [CHƯA ĐO] |
| Isolation | 100% bởi hệ điều hành: data, keystore, AccountManager (Google account riêng), SSAID/ANDROID_ID riêng theo user |
| APK duplication | 0 (dùng chung) [LÝ THUYẾT] |
| Số tài khoản | **Tối đa 4** (Owner + 3) [ĐO]. Vượt 4 cần `setprop fw.max_users` = root, mất khi reboot nếu không ghi build.prop |
| Switching | `am switch-user N` + `am start` game. Thời gian **[CHƯA ĐO]**; user nền có thể `stop-user` để giải phóng RAM |
| Rủi ro LDPlayer | Launcher/IME/render của LDPlayer có thể không tương thích user phụ; chưa biết GMS/Play Services hoạt động ở user phụ → **phải PoC** |
| Không đụng dữ liệu game | ✔ — không đọc/ghi file của game |

**Kết luận sơ bộ:** sạch nhất về bảo mật và tính toàn vẹn, nhưng **không đáp ứng 10–30 tài khoản** nếu không root. Hợp làm phương án dự phòng hoặc kết hợp (4 user × N slot dữ liệu).

### Option B — Managed Profile (Work Profile)
| Tiêu chí | Đánh giá |
|---|---|
| Tạo profile | `pm create-user --profileOf 0 --managed` có trong `pm help` [ĐO] |
| Giới hạn | AOSP 9 chỉ cho **1 managed profile / user cha** và profile tính vào trần 4 user [LÝ THUYẾT] → tối đa 2 bản game trong cùng user Owner |
| DPC | Cần app Device Policy Controller làm profile owner (`dpm set-profile-owner`) để quản lý — thêm 1 app phải tự viết |
| Switching | Không "chuyển" — profile chạy song song, app hiện badge; không có cơ chế chọn tài khoản nhanh |

**Kết luận: KHÔNG khả thi** cho 10+ tài khoản. Loại bỏ, không đưa vào PoC (trừ khi bạn muốn xác minh giới hạn 1 profile).

### Option C — Application Data Isolation (1 APK, nhiều bộ dữ liệu)
**Cơ chế:** khi game đã dừng hẳn (`am force-stop`), chụp nguyên trạng toàn bộ dữ liệu app của tài khoản hiện tại → lưu vào kho slot → khôi phục nguyên trạng slot của tài khoản đích → mở game. **Không sửa nội dung file**, chỉ snapshot/restore bit-for-bit.

Hai cách hiện thực, không cần bypass bảo mật:

| Cách | C1: `adb backup` / `adb restore` | C2: Root mode của LDPlayer + `tar` |
|---|---|---|
| Cần root | Không | Có (công tắc chính thức trong LDPlayer Settings) |
| Điều kiện | `ALLOW_BACKUP` ✔ [ĐO]; nhưng app có thể khai báo `fullBackupContent` loại trừ file → **phải kiểm tra manifest** | Không phụ thuộc manifest |
| Thao tác | Phải bấm xác nhận trên màn hình mỗi lần backup/restore | Hoàn toàn tự động |
| Độ tin cậy | Thấp hơn: đã bị Google deprecated, restore đôi khi bỏ sót `no_backup/`, `cache/`, không giữ SELinux label tùy app | Cao: giữ uid/gid/SELinux context (`restorecon`), kiểm tra checksum được |
| Tốc độ | [CHƯA ĐO] | [CHƯA ĐO] — phụ thuộc kích thước internal data |

**Điểm chặn có thể làm Option C thất bại (phải PoC trước):**
1. **Định danh thiết bị:** ANDROID_ID (SSAID) trên Android 9 cố định theo (user, chữ ký app) — mọi slot dùng chung 1 ANDROID_ID. Nếu tài khoản **khách (guest)** được server gắn với device ID → mọi slot sẽ đăng nhập về cùng 1 tài khoản → **C không dùng được cho guest**. Tài khoản gắn Google/Facebook/tài khoản nhà phát hành thường lưu token trong data app → có khả năng hoạt động.
2. **Google Sign-In nằm trong GMS**, không nằm trong data game: game có thể tự chọn lại Google account cuối cùng. Cần kiểm tra luồng đăng nhập thực tế.
3. **Android Keystore:** nếu SDK mã hóa token bằng khóa trong Keystore, khóa vẫn nằm trong hệ thống (cùng user, cùng uid) nên restore cùng máy vẫn giải mã được [LÝ THUYẾT] — nhưng không mang slot sang instance khác được.
4. **Chính sách nhà phát hành:** chuyển đổi bằng snapshot dữ liệu không sửa token, không can thiệp anti-cheat; tuy vậy điều khoản dịch vụ của game có thể có quy định về nhiều tài khoản — bạn cần tự đánh giá.

**Kết luận sơ bộ:** đây là phương án duy nhất có thể đạt **10–30+ tài khoản / 1 instance / 1 APK** — **với điều kiện** PoC chứng minh phiên đăng nhập nằm trong data app.

### Option D — Custom Account Switching Manager (Windows)
Không phải một cơ chế cô lập mà là **lớp điều phối** ngồi trên A hoặc C: quản lý metadata (SQLite), gọi ADB/ldconsole, force-stop → snapshot → restore → launch → kiểm tra, log, rollback. Bắt buộc phải có, bất kể chọn A hay C.

---

## 3. So sánh 4 kiến trúc

| Metric | A Multi-User | B Managed Profile | C Data Isolation | D Manager |
|---|---|---|---|---|
| Số tài khoản | ≤4 (không root) | ≤2 | 10–30+ (giới hạn bởi dung lượng) | phụ thuộc A/C |
| APK duplication | 0 | 0 | 0 | — |
| Asset duplication | external 24 MB + internal/user [CHƯA ĐO] | như A | 1 bộ đang dùng + slot lưu nén | — |
| Isolation | 100% (OS) | 100% (OS) | 100% **nếu** không gắn device ID — [CHƯA ĐO] | — |
| Switching time | [CHƯA ĐO] | n/a | [CHƯA ĐO] | — |
| Corruption risk | Rất thấp | Rất thấp | Trung bình → giảm bằng force-stop + checksum + rollback | — |
| Instances | 1 | 1 | 1 | 1 |
| Cần root | Không (≤4) | Không | C1 không / C2 có | — |
| Khả thi | Một phần | **Loại** | **Ứng viên chính – chờ PoC** | Bắt buộc |

---

## 4. Sơ đồ kiến trúc đề xuất (dự kiến, phụ thuộc PoC)

```
┌──────────────────────── Windows ─────────────────────────────┐
│ AccountManager.UI (WPF)  Dashboard · Quick Switch · Storage   │
│            │                                                  │
│ AccountManager.Application  SwitchAccountUseCase, Backup/Restore,│
│            │                 VerifyLaunch, Rollback           │
│ AccountManager.Domain   Account, Slot, Snapshot, SwitchJob,   │
│            │             ISwitchStrategy (UserStrategy|DataStrategy)│
│ ┌──────────┴───────────┐  ┌──────────────────────────────┐    │
│ │ Infrastructure.Adb    │  │ Infrastructure.Storage        │    │
│ │ AdbClient, LdConsole  │  │ SQLite metadata, SlotStore    │    │
│ │ GameProbe (pidof,     │  │ (zstd + SHA-256, dedupe theo  │    │
│ │ dumpsys activity)     │  │ hash file), Journal log       │    │
│ └──────────┬───────────┘  └──────────────────────────────┘    │
└────────────┼───────────────────────────────────────────────────┘
             │ adb (127.0.0.1:5555)
┌────────────▼──────── LDPlayer instance (1 duy nhất) ───────────┐
│ /data/app/<pkg>-*/  ← APK 866 MB, DÙNG CHUNG                     │
│ /data/user/0/<pkg>  ← slot ĐANG HOẠT ĐỘNG (swap theo tài khoản)   │
│ /sdcard/Android/data/<pkg>/files ← asset (đo xem có phụ thuộc TK)│
│ [tùy chọn] /data/user/10..12 ← Option A cho ≤3 tài khoản ưu tiên │
└──────────────────────────────────────────────────────────────────┘
```
`ISwitchStrategy` cho phép giữ cả A và C, chọn theo kết quả PoC. Có thể tích hợp với bot hiện tại (`main.py`) để bot lặp theo **tài khoản** thay vì theo **instance**.

## 5. Luồng chuyển đổi tài khoản (Option C)

```
Select(target)
 1. Preflight: adb online? dung lượng host đủ? target slot hợp lệ (checksum)?
 2. Probe: pidof <pkg> → nếu chạy: am force-stop <pkg>; chờ pidof rỗng (timeout → ABORT)
 3. Snapshot slot hiện tại → tmp; verify SHA-256; atomic rename → slots/<current>/<ts>
 4. Ghi journal: "SWITCHING current→target"
 5. Restore: xoá data app trong máy → giải nén slot target → chown/restorecon (C2) | adb restore (C1)
 6. Verify: so manifest checksum trong máy vs slot
 7. am start -n <pkg>/com.revengeofempire.plugins.MainActivity
 8. VerifyLaunch: pidof + mResumedActivity trong T giây; (tuỳ chọn) OCR nickname/server
 9. OK → journal "DONE", cập nhật LastUsed
    FAIL ở 5–8 → force-stop → restore snapshot bước 3 → journal "ROLLED_BACK" → báo lỗi
```
Nguyên tắc: **không bao giờ ghi khi game đang chạy**; mọi ghi đè đều có snapshot trước; journal cho phép khôi phục sau khi app Windows/LDPlayer crash giữa chừng.

## 6. Phân tích dung lượng

| Thành phần | Hiện tại (9 instance) | Option C (1 instance) |
|---|---|---|
| system.vmdk | 1.74 GB dùng chung | 1.74 GB |
| APK game | ~0.87 GB × số instance có game | **0.87 GB × 1** |
| Data/vmdk mỗi instance | 6.6–21.4 GB/instance, tổng ≈ 121 GB [ĐO] | 1 instance (~16 GB như #0) |
| Slot dữ liệu/tài khoản | — | **[CHƯA ĐO]** = internal data + phần external phụ thuộc TK, nén |

Công thức ước tính sau PoC: `Tổng ≈ 1 instance + N × size(slot nén)`. Chỉ đưa ra con số sau khi đo internal data ở Phase 1.

## 7. Rủi ro mất dữ liệu

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Ghi đè data khi game đang ghi SQLite | Cao | Luôn force-stop + kiểm tra pidof trước, không bao giờ copy "nóng" |
| Restore thiếu file (adb backup loại trừ) → đăng nhập sai TK | Cao | So sánh danh sách file trước/sau; ưu tiên C2 |
| Sai owner/SELinux sau restore → game crash/xoá data | Trung bình | `chown` theo uid của app + `restorecon -R`; verify trước khi launch |
| Guest account gắn device ID → các slot trùng nhau | Cao | PoC bước kiểm tra riêng; chỉ dùng tài khoản đã liên kết |
| Crash giữa chừng | Trung bình | Journal + snapshot tmp + atomic rename + rollback tự động |
| Mất dữ liệu tài khoản thật trong PoC | Cao | `ldconsole backup` toàn VM (.ldbk) trước mọi thử nghiệm; PoC trên instance phụ |
| Server-side: tài khoản game nằm trên server | Thấp | Dữ liệu tiến trình game lưu server; slot chủ yếu giữ phiên đăng nhập + cache |
| vmdk phình không co | Thấp | Dọn định kỳ / compact vmdk (ngoài phạm vi) |

## 8. Kế hoạch Proof of Concept (Phase 1 — chờ xác nhận)

**Môi trường:** dùng một instance phụ (đề xuất **#7 MFarm07** hoặc #8, 6.6 GB) — **không** dùng #0. Trước tiên `ldconsole backup` toàn VM.

| Bước | Mục tiêu | Đo |
|---|---|---|
| P0 | Backup .ldbk instance thử nghiệm | thời gian, kích thước |
| P1 | Kiểm tra login: tài khoản trong game đang là guest/Google/Facebook/LT? | ghi nhận |
| P2 (A) | `pm create-user`, `install-existing`, `switch-user`; đăng nhập TK thứ 2 ở user 10 | thời gian switch, du APK có bị copy không, RAM |
| P3 (C) | Bật root LDPlayer trên instance thử nghiệm; đo `du` internal data; snapshot slot A | kích thước, thời gian |
| P4 (C) | `pm clear` → đăng nhập TK B → snapshot slot B | — |
| P5 (C) | Restore A → mở game → đúng TK A? Restore B → đúng TK B? lặp 10 lần | tỉ lệ thành công, thời gian |
| P6 (C1) | Thử `adb backup -noapk` không root, so sánh danh sách file với C2 | đủ/thiếu |
| P7 | Rollback giả lập lỗi (rút giữa chừng) | khôi phục được? |
| P8 | Báo cáo số liệu thật → chọn strategy | — |

Tiêu chí chọn: C đạt nếu P5 thành công 10/10 cho cả hai tài khoản và không có lỗi dữ liệu. Nếu C thất bại vì gắn device ID → chuyển A (≤4) + xem xét nâng `fw.max_users` (cần bạn đồng ý dùng root).

## 9. Lệnh ADB để kiểm chứng

```bash
# ---- Biến (Git Bash) ----
ADB=/d/LDPlayer/LDPlayer9/adb.exe; LD=/d/LDPlayer/LDPlayer9/ldconsole.exe
P=com.ageofwarpath.globalwarzone.vn; S=127.0.0.1:5555   # đổi theo instance thử nghiệm

# ---- An toàn: backup toàn VM trước mọi thử nghiệm ----
$LD backup --index 7 --file "E:/AOW-BOT/backups/MFarm07-pre-poc.ldbk"

# ---- Khảo sát (read-only, đã chạy trong Phase 0) ----
$ADB -s $S shell getprop ro.build.version.release
$ADB -s $S shell pm get-max-users
$ADB -s $S shell dumpsys user
$ADB -s $S shell pm list features
$ADB -s $S shell "dumpsys package $P | grep -E 'versionName|codePath|dataDir|flags='"
$ADB -s $S shell "pm path $P"
$ADB -s $S shell "pidof $P; dumpsys activity activities | grep mResumedActivity"

# ---- Option A ----
$ADB -s $S shell pm create-user poc_acc2           # -> in ra user id (vd 10)
$ADB -s $S shell pm install-existing --user 10 $P
$ADB -s $S shell "pm path --user 10 $P"            # phải trùng codePath của user 0
$ADB -s $S shell am switch-user 10
$ADB -s $S shell "am start --user 10 -n $P/com.revengeofempire.plugins.MainActivity"
$ADB -s $S shell am switch-user 0
$ADB -s $S shell am stop-user -w 10
$ADB -s $S shell pm remove-user 10                  # dọn sau PoC (xoá data user 10)

# ---- Option B (chỉ xác minh giới hạn) ----
$ADB -s $S shell pm create-user --profileOf 0 --managed poc_work
$ADB -s $S shell pm create-user --profileOf 0 --managed poc_work2   # kỳ vọng thất bại

# ---- Option C2 (root mode của instance thử nghiệm) ----
$LD modify --index 7 --root 1                                  # cần restart instance
$ADB -s $S shell am force-stop $P
$ADB -s $S shell "pidof $P || echo stopped"
$ADB -s $S shell "su -c 'du -sh /data/user/0/$P; du -sh /data/user/0/$P/*'"
$ADB -s $S shell "su -c 'stat -c \"%u %g %C\" /data/user/0/$P'"   # uid/gid/SELinux
$ADB -s $S shell "su -c 'tar -cf /sdcard/slotA.tar -C /data/user/0 $P'"
$ADB -s $S pull /sdcard/slotA.tar E:/AOW-BOT/slots/A.tar
# restore (chỉ khi game đã dừng):
$ADB -s $S push E:/AOW-BOT/slots/A.tar /sdcard/slotA.tar
$ADB -s $S shell "su -c 'rm -rf /data/user/0/$P/* && tar -xf /sdcard/slotA.tar -C /data/user/0 && chown -R <uid>:<gid> /data/user/0/$P && restorecon -R /data/user/0/$P'"

# ---- Option C1 (không root) ----
$ADB -s $S backup -f E:/AOW-BOT/slots/A.ab -noapk $P    # cần bấm xác nhận trên màn hình
$ADB -s $S restore E:/AOW-BOT/slots/A.ab

# ---- Đo thời gian ----
time $ADB -s $S shell am switch-user 10
time $ADB -s $S shell "am start -W -n $P/com.revengeofempire.plugins.MainActivity"
```

---

## 10. Quyết định cần bạn xác nhận trước Phase 1
1. Đồng ý chạy PoC trên **instance phụ (#7 hoặc #8)**, có backup `.ldbk` trước — không đụng #0?
2. Đồng ý **bật root mode của LDPlayer** trên instance thử nghiệm (để đo internal data và thử C2)?
3. Tài khoản game hiện tại đăng nhập bằng gì (guest / Google / Facebook / tài khoản nhà phát hành)? Cần ít nhất **2 tài khoản thử nghiệm không quan trọng**.
