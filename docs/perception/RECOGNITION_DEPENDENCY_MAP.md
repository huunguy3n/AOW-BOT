# RECOGNITION_DEPENDENCY_MAP

Chỉ ghi quan hệ đã thấy trong mã (2026-11-21). `A → B` = A gọi/import B.

```
main.py ── tạo Vision(templates, match_threshold) ──► Runner ──► Ctx(dev, vision, cfg)   (mỗi tài khoản/lượt)
                                                                   │
  Device.screencap_raw ──► Ctx.shot() ──► ảnh BGR 540×960          │
                                                                   ▼
 bot/modules/* ─► ctx.find/tap_tpl/tap_first/wait_for ─► Vision.find ─► Vision.best ─► cv2.matchTemplate
        │                       │                            ▲  ▲          (+ biến thể @auto, prior ±60 px)
        │                       │                            │  └─ learn.py ghi biến thể / đọc `var,extra`
        │                       └─► learn (exp: kind,tpl,x,y,score,outcome) ◄─ Ctx._exp_begin/_exp_end
        ├─► badges.red_dots/glow_tiles/nhan_tiles (màu HSV, không qua Vision)
        ├─► ocr.* / ctx._ocr_* (Tesseract; trùng lặp)
        ├─► buttons.find/claims (hình+OCR)  ├─► imitate.decide (matchTemplate riêng)
        ├─► tutorial.decide (matchTemplate có mask riêng) └─► steer.py (màu, luồng frame)
 bot/screens.identify ─► Vision.find (ROI dict) ─► nav_action ─► Ctx.goto
 bot/screen_types, learn.feat/kNN ─► phân loại màn song song
 src/aowbot/infrastructure/legacy/* ─► bot/* (adapter; agent chỉ gọi gián tiếp)
 web/server.py ─► bot.learn / bot.screen_types (hiển thị, dạy tay)
```

## Phụ thuộc vòng / ẩn

| Vòng/ẩn | Bằng chứng |
|---|---|
| `Vision` ↔ `learn` | `vision.py` có `var`, `extra`, `prior` chỉ phục vụ `learn.regress_ok` và `reload_variants()`; `learn.py:343` tạo `Vision(TPL, 0.82)` riêng |
| `Ctx` ↔ `learn` | `Ctx.learner`, `_exp_begin/_exp_end` bọc mọi lần chạm; học lại ảnh hưởng lần `find` sau |
| Trạng thái toàn cục ẩn | `Vision.prior` (vị trí lần khớp trước, chia sẻ giữa 2 luồng song song), `cache`, `missing`; `miss_hits` theo luồng (`threading.local`) |
| Ngưỡng nhập từ 3 nguồn | `config.yaml match_threshold`, tham số `th=` tại điểm gọi, hằng số trong `screens/imitate/learn/buttons` |
| Ràng buộc import | `bot/*` chỉ được vào `aowbot.domain` (D7) → engine mới không thể đặt ở `application/infrastructure` rồi để `bot/vision.py` import trực tiếp (xem PLAN §Quyết định cần duyệt) |

## Người tiêu thụ kết quả

| Người dùng | Kết quả đang dùng | Rủi ro hành động |
|---|---|---|
| `modules/*` | `(x,y,score)` hoặc `None` | chạm ngay |
| `screens.identify` | tên màn, nút | chạm đóng/quay lại, phím Back |
| `defense` | mẫu cảnh báo bị tấn công | bật khiên (có thể tốn kim cương) |
| `gather`, `build`, `train`… | nút "…ngay" có tốn kim cương | chặn bằng OCR/danh sách chứ không bằng độ tin cậy |
| `src/aowbot` agent | gián tiếp qua adapter legacy | quyết định *khi nào*, không đọc điểm nhận diện |
