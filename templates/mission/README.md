# templates/mission — sự kiện "Sứ mệnh" (P7-7)

Cắt ở **540×960** từ ADB screencap (`python main.py --capture 1` rồi `python tools/snap.py cutmany SRC tên=x1,y1,x2,y2`).
Ảnh tham khảo giao diện (KHÔNG cắt từ đó, lệch vài px): `data/pm-shots/owner-20261124/su_menh_*.png`.

| File | Màn hình | Vùng gợi ý (x1,y1,x2,y2) | Mô tả |
|---|---|---|---|
| `icon.png` | Thành phố | ~488,280,536,330 | Icon "Sứ mệnh" cột phải (dưới Phúc lợi), cắt **không** gồm số đỏ |
| `title.png` | Sứ mệnh | ~210,12,330,48 | Chữ tiêu đề "Sứ mệnh" |
| `tab_daily.png` | Sứ mệnh | ~360,195,520,232 | Tab "Nhiệm vụ hàng ngày" (trạng thái chưa chọn) |
| `gift_icon.png` | Sứ mệnh | ~150,80,230,160 | Icon hộp quà "Quà kỳ diệu" (không gồm chữ) |
| `free_chest.png` | Quà kỳ diệu | góc trên-trái, trong vùng 0,200,280,460 | Rương nhỏ có đồng hồ (miễn phí), cắt không gồm chấm đỏ |

Không cắt / không bao giờ chạm: tab "Thẻ thông hành", tab "Săn kho báu", bàn xúc xắc, nút "+" xúc xắc, gói giá ₫.

## P9-4 (2026-11-24, live-run-2)

| File | Màn hình | Nguồn (ADB 540×960) | Vùng cắt (x1,y1,x2,y2) | Mô tả |
|---|---|---|---|---|
| `cart.png` | Sứ mệnh > Săn kho báu | `data/pm-shots/owner-20261124/p8-adb/mis1.png` | 486,296,516,326 | Icon xe đẩy (cửa hàng xúc xắc), không gồm chấm đỏ (522,288) |
| `shop_title.png` | Cửa hàng xúc xắc điều khiển từ xa | `data/pm-shots/owner-20261124/live2/auto/s110328.png` | 110,12,330,44 | Chữ tiêu đề — màn **không bao giờ** cho follower (tutorial-hand) chạm; chỉ nút "Miễn phí" có chấm đỏ |
