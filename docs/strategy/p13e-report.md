# P13e — dùng hết thợ xây (báo cáo ngắn)

Nhánh `p13e` (từ `p13d`). **Chưa chạy máy thật** — chỉ kiểm bằng test đơn vị/giả lập; cần live để xác nhận.

## Nguyên nhân
1. **"dùng tối đa 1"**: `build.max_builders: 1` (config) kẹp số thợ dù game báo `0/2`; chỉ #1 có `max_builders=2` trong
   `data/settings.json`. `builder_idle`, `idle_slots` (ưu tiên ô rảnh), lịch `plan_build` ("thợ xây rảnh (0/1)"), `quick_wait`
   và `hqplan.yield_builder` đều đọc cấu hình cứng.
   Log 26/11: cả 7 máy luôn đọc tổng `y = 2` (198 lần 0/2, 53 lần 1/2, 142 lần 2/2), không có bước thuê/mua trong log.
2. **Bước bị tắt**: `scheduler.BUILD_STEPS` thiếu `construct`; lượt spawn từ lịch/hẹn giờ chỉ chạy `modules=set(steps)` nên
   `runner.run_account` đặt `enabled = k in modules` → bước không có trong danh sách bị tắt ("Buoc dang tat").
   Lượt Đăng nhập hẹn giờ chỉ có `warday,notify,rewards` nên tắt luôn upgrade/construct/mainquest.
3. **Bỏ xây giữa chừng**: `should_quick_wait` (P13d) cố ý không đứng chờ khi còn việc khác, nhưng không có bước nào quay lại
   lấp thợ rảnh sau khi các bước khác xong.

## Sửa
- **P13e-1** `aowbot.domain.builders.effective_max`: số thợ hiệu lực = `y` trong `x/y` game báo (fact `builders_total`, observe ghi),
  kẹp bởi `build.max_builders_cap` (2). `build.use_game_slots: false` quay về cách cũ. Ô chưa có → game báo `y=1` → giữ 1.
  **Bot không thuê thợ / mua ô bằng kim cương** (không có đường mã nào như vậy; không thêm).
- **P13e-2** `Runner._fill_builders`: trước `observe`, đọc lại hàng chờ xây; còn thợ rảnh → chạy lại
  construct/upgrade/mainquest/quests, tối đa `build.fill_rounds` (2) vòng, dừng nếu vòng trước không bắt đầu thêm việc.
  Tăng tốc vẫn chỉ nút "Miễn phí" (P13d, không đổi).
- **P13e-3** `BUILD_STEPS` + `plan_step` có `construct`; `scheduler.with_build_steps` luôn thêm construct/upgrade/mainquest
  (nếu máy bật) vào lượt khi thợ rảnh, kể cả đang gian chu kỳ stepgate; lượt Đăng nhập hẹn giờ gộp các bước xây khi thợ rảnh
  (vẫn bị trần `timed_login_visit_max_min` 12 phút). Khi mọi thợ bận, lịch hẹn lại đúng máy theo timer `build:*` (đã có sẵn,
  nay tính trên số thợ hiệu lực nên không còn coi 1/2 là "bận hết").
- **P13e-4** (phụ) ô phát sáng bấm xong vẫn sáng (ô khóa Dưỡng Tướng @130,669 / @138,729 / @139,530) → không bấm lại trong lượt
  ghé (`ctx.glow_dead`); `hero_story` không còn tap x âm (kẹp ≥ 46). **Giới hạn**: nguồn chính xác của `(-42,688)` suy ra
  từ log (không có ảnh) — kẹp ở `hero_story`, `Device`/`ctx.tap` vẫn kẹp 0..539 như cũ; ô khóa vẫn có thể bị bấm 1 lần/lượt ghé.

## Kiểm
`tests/unit/test_builders.py`, `tests/legacy/test_p13e_glow.py` (số thợ 2 khi `0/2`, không dùng ô thứ 2 khi `y=1`, #1 vẫn 2,
lịch `(0/2)`, ép bước xây, hẹn theo timer, lấp vòng). 3 test `test_p13b_cham_do_khong_doi` fail trong worktree vì thiếu ảnh
`data/owner-feedback` (gitignore); sau khi chép thư mục đó từ worktree p13d: 1307 pass, 0 fail.

## Cần xác nhận khi chạy thật
- `0/2` có thật là 2 thợ dùng được ở farm (log cho thấy tổng 2 ở mọi máy) — nếu một máy hóa ra chỉ 1, đặt
  `build.use_game_slots: false` hoặc `instances.N.build.max_builders` trên web.
- Việc "công trình hữu ích tiếp theo" ngoài chuỗi nhà chính vẫn do `construct` (công trình mới) và `quests` ("Đến") đảm nhiệm;
  chưa có bước nâng nhà tài nguyên theo "Đề xuất" riêng — chưa làm.
