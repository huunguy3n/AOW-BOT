# templates/steer — buff trong trận chạy đường (P7-9)

Tùy chọn: nhận diện buff theo màu đã có (`bot/steer.py detect`); ảnh mẫu ở đây **bổ sung** khi hiệu ứng lửa/khói che màu.
Mọi file `buff_*.png` được dò trong dải y 110–600 (phía trước đội quân), ngưỡng 0,8.
Cắt ở **540×960** từ khung trận thật (`logs/steer/*.jpg` khi `battle.debug_dir` bật, hoặc `python main.py --capture N` giữa trận).
Ảnh tham khảo (không cắt từ đó): `data/pm-shots/owner-20261124/minigame_runner_gates_minus_plus.png`.

| File | Mô tả | Kích thước gợi ý |
|---|---|---|
| `buff_soldiers.png` | Cổng xanh dương lính "+N" (3 lính + mũi tên) — chỉ phần icon, không gồm số | ~70×60 |
| `buff_ammo.png` | Băng đạn xanh lá "+%" có mũi tên — chỉ icon | ~60×60 |

HUD trận chiến dịch (cho `campaign/battle_hud_*.png`, nhóm `campaign`): khi log có "Khong xac nhan duoc dang trong tran", ảnh
khung cuối nằm ở `logs/inv/steer_no_battle/` — cắt icon cố định trên HUD trận (vd nút kỹ năng máy bay góc trên-trái ~10,30,75,95)
thành `templates/campaign/battle_hud_2.png`.
