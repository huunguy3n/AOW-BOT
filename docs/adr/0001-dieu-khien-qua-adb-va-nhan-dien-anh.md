# ADR-0001: Điều khiển game qua ADB + nhận diện ảnh, không can thiệp bộ nhớ/mạng

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-11-16
- **Liên quan:** `bot/device.py`, `bot/vision.py`, `bot/ocr.py`, `templates/`

## Bối cảnh
Cần tự động hóa thao tác lặp lại trong Age of Warpath trên nhiều instance LDPlayer. Game là Unity/il2cpp, có SDK đăng nhập `com.ltsdk.union`, license check Google Play. Không có API chính thức.

## Quyết định
Bot chỉ "nhìn và chạm" như người chơi: `adb screencap` → OpenCV template matching / lọc màu / Tesseract OCR → `adb input tap/swipe` (hoặc `sendevent`, xem ADR-0007). Không đọc/ghi bộ nhớ game, không chặn/sửa gói tin, không sửa APK, không bypass license/anti-cheat.

## Phương án đã cân nhắc
- **Memory/packet hacking** — nhanh, chính xác nhưng rủi ro khóa tài khoản cao, vỡ theo mỗi bản cập nhật, vi phạm rõ ràng. Loại.
- **Macro ghi tọa độ thuần** — đơn giản nhưng mù trạng thái, gãy khi popup xuất hiện. Chỉ dùng tọa độ cứng cho phần tử cố định.
- **ADB + vision** (chọn) — chậm hơn, phụ thuộc ảnh mẫu, nhưng an toàn và chịu được thay đổi nhỏ.

## Hệ quả
- Tốt: không động vào game; dễ debug bằng ảnh (`logs/shots/`).
- Xấu: phải cắt và bảo trì ảnh mẫu (`templates/README.md`, `tools/snap.py`); UI đổi là phải cắt lại. Tesseract chỉ có `eng` → chữ Việt mất dấu, phải so theo từ khóa gần đúng.
- Thiếu ảnh mẫu → `Vision` cảnh báo một lần và coi như không thấy (bot bỏ qua thao tác, không crash).
