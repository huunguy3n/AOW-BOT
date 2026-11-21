# Kế hoạch giai đoạn E–I — Bot học máy mini

Ngày: 2026-11-20 · Trạng thái: **chờ chủ dự án duyệt** (ADR-0012: làm từng giai đoạn)
Yêu cầu: *"việc nhận diện hình ảnh còn quá kém. Trí nhớ thì như một kẻ ngốc. Tôi cần bot thông minh hơn sau mỗi lần làm, nó cần là một mô hình bot máy học mini"*

## 1. Hiện trạng [ĐO trên `data/memory.db`, 2026-11-20]

| Chỉ số | Giá trị | Ý nghĩa |
|---|---|---|
| Chạm mà màn hình **không đổi** (`nav.action = tap`) | **593 / 996 = 60 %** | Bot chạm trượt hoặc chạm vào thứ không phản hồi rất nhiều |
| Màn hình không nhận ra (`unknown`) | 125 / 2651 = 4,7 % | Mỗi lần gặp màn lạ là phải bấm Back mò |
| Bước kết thúc không "ổn" (warn/miss/err/stuck) | 96 / 432 = 22 % | Hơn 1/5 số bước không hoàn thành |
| Thời gian 1 lần ghé máy | ~9,9 phút | |

**Vì sao bot "ngốc":**
- **Nhận diện cứng.** Ảnh mẫu khớp 1 ngưỡng cố định (0,82). Nền khác hoặc hoạt ảnh là trượt: "Free" trên nền vàng chỉ đạt 0,47, "Nhận" mốc 0,52, tick tình báo 0,61. Mỗi lần trượt lại phải có người chụp ảnh rồi agent sửa code.
- **Trí nhớ chỉ ghi, không dùng.** `memory.db` có 2651 dòng điều hướng nhưng không gì đọc lại để quyết định. Lần sau bot vẫn mở lại chấm đỏ "Chiêu mộ" không nhận được gì, vẫn chạm chỗ đã chạm trượt.
- **Không có tín hiệu kết quả.** Bot không biết hành động nào *thành công*, nên không thể học.

## 2. Nguyên tắc thiết kế

1. **Mô hình mini, không cài thêm thư viện nặng.** Chỉ dùng numpy + OpenCV đã có. Máy cài OpenCV 5 không kèm `cv2.ml`, nên tự viết kNN, logistic và bandit bằng numpy (vài trăm dòng). Mạng CNN nhỏ (ONNX) chỉ cân nhắc ở giai đoạn sau, nếu chủ dự án đồng ý cài `onnxruntime`.
2. **Học từ chính lần chạy.** Mỗi hành động ghi lại *ảnh trước, chạm ở đâu, vì sao, kết quả*. Nhãn kết quả tự sinh: màn đổi, chấm đỏ mất, hiện bảng thưởng, bước tiến lên.
3. **An toàn đứng ngoài việc học.** Học chỉ được *chọn giữa các hành động an toàn*. Danh sách cấm cứng giữ nguyên, mô hình không bao giờ ghi đè được:
   - kim cương, "Tăng cấp ngay", "Huấn luyện ngay";
   - "Mở khóa", "Cấp mùa", "Nạp thẻ", "Đến" của Thẻ tháng;
   - icon "Quà" $, pm clear.
   Ảnh mẫu tự học chỉ được *thêm biến thể* cho nút đã có trong danh sách an toàn.
4. **Hàm thuần + hồi quy.** Mỗi mô hình là hàm `ảnh → dự đoán`, kiểm tra offline bằng ảnh đã lưu (ADR-0011).
5. **Có thước đo.** Mỗi giai đoạn chốt bằng 1 lượt + 1 lần chạy lại, so với bảng chỉ số ở mục 1.

## 3. Các giai đoạn

### E — Nhật ký kinh nghiệm (nền móng cho mọi thứ học)

Không có dữ liệu có nhãn thì không học được gì.

- **Bảng `exp` trong `memory.db`.** Mỗi lần `ctx.tap` / `tap_tpl` ghi:
  - máy, bước, màn trước (`screens.identify`), ảnh mẫu / lý do (`why`);
  - toạ độ, điểm khớp, thời gian chờ;
  - màn sau, `changed`, kết quả (`reward` / `reddot_gone` / `new_screen` / `none`);
  - thời gian phản hồi thật (ms tới khi màn đổi).
- **Ảnh cắt quanh điểm chạm** (96×96) và **dấu vân tay màn** (dHash + vector nhỏ) lưu vào `data/exp/`, bỏ trùng theo hash, có trần dung lượng (vd 300 MB, xoá cũ nhất).
- **Báo cáo** `tools/learn.py report`: tỉ lệ chạm trượt theo ảnh mẫu / bước / máy; top 10 thao tác hay hỏng.
- **Thước đo xong:** 1 lượt 2 máy ghi được ≥ 95 % số chạm kèm kết quả.

### F — Nhận diện ảnh tự học

| # | Việc | Giải quyết |
|---|---|---|
| F1 | **Bộ phân loại màn hình kNN.** Mỗi màn → vector ~512 chiều (ảnh xám thu nhỏ + histogram HSV + biên). Học từ ~2600 màn đã gắn nhãn trong `nav`. Khi `identify` trả `unknown` hoặc điểm thấp thì hỏi kNN, kèm độ tin cậy. | Màn lạ 4,7 % → mục tiêu < 1 % |
| F2 | **Ảnh mẫu đa biến thể tự mở rộng.** Ảnh mẫu khớp 0,6–0,82 và chạm xong *đúng kết quả mong đợi* (vd bấm "Nhận" ra bảng thưởng) → lưu thành biến thể ứng viên `templates/<tên>@auto<N>.png`. Đúng 2 lần → dùng chính thức. Tối đa 6 biến thể / nút. | "Free"/"Nhận" trên nền khác không còn trượt |
| F3 | **Phân loại nút theo ảnh cắt** (kNN trên ảnh cắt từ E): `nhan_xanh` / `xam_khoa` / `tra_phi` / `dong` / `khac`. Nút `tra_phi` luôn bị chặn, kể cả khi ảnh mẫu khớp nhầm. | Thêm lớp bảo vệ kim cương; giảm chạm nút xám |
| F4 | **Hồi quy tự động:** mọi ảnh mẫu và mô hình chạy trên `tests/fixtures/` + 200 khung ngẫu nhiên từ `data/exp/` trước khi nhận biến thể mới. | Tự học không làm hỏng cái đang chạy |

**Thước đo xong:** chạm trượt 60 % → **< 30 %**; màn lạ < 1 %.

### G — Trí nhớ dùng được

| # | Việc |
|---|---|
| G1 | **Bản đồ điều hướng học được.** Từ `nav` + `exp` dựng đồ thị *màn → hành động → màn* có xác suất thành công. `goto()` đi đường ngắn nhất có xác suất cao, thay vì thử Back mò. |
| G2 | **Nhớ vị trí phần tử.** Nút X lần trước ở đâu trên màn Y thì tìm ở vùng đó trước. Vừa nhanh hơn, vừa bớt khớp nhầm. |
| G3 | **Trí nhớ sự kiện có hạn dùng.** "Chấm đỏ Chiêu mộ @124,736 mở ra không nhận được gì" → không mở lại trong 6 h hoặc tới reset 0h. Tương tự cho nút xám, nhiệm vụ thiếu lực chiến, mỏ quá sức chở. |
| G4 | **Dữ kiện có độ tin cậy.** Mỗi dữ kiện (cấp nhà chính, bản đồ mở...) có thời điểm thấy + nguồn. Dữ kiện cũ thì giảm tin cậy và tự đọc lại. |

**Thước đo xong:** số lần mở lại thứ vô ích giảm ≥ 70 %; thời gian 1 lần ghé giảm ≥ 20 %.

### H — Học từ kết quả (bandit mini)

- **Chọn hành động bằng Thompson sampling.** Ở các điểm có nhiều lựa chọn an toàn:
  - ứng viên bàn tay hay ô xanh/đỏ nào trong tân thủ;
  - chấm đỏ nào mở trước;
  - lệch chạm (−16, +17) hay khác.
  Mỗi lựa chọn giữ phân phối Beta(thành công, thất bại) theo bối cảnh (màn + lý do). Bot thử, ghi kết quả, lần sau nghiêng về cái hay thành công.
- **Thời gian chờ tự thích nghi.** Học phân phối thời gian phản hồi từng loại hành động (từ E), chờ theo p90 thay vì số cố định × `wait_scale`. Đây là cách tăng tốc an toàn nhất.
- **Giá trị từng bước theo máy.** Bước nào hay ra phần thưởng thì bộ lập lịch ưu tiên. Bước luôn trắng tay ở một máy thì giãn chu kỳ, vd research ở nhà chính < 8.
- **Thước đo xong:** thời gian ghé giảm thêm ≥ 15 %; bước không "ổn" 22 % → < 10 %.

### I — Vòng học + chủ dự án dạy bot trên web

- `tools/learn.py train` chạy tự động lúc máy nghỉ giữa các vòng: dựng lại kNN, duyệt biến thể ảnh mẫu, cập nhật bandit.
- **Trang web "Bot học được gì":**
  - tỉ lệ chạm trúng theo ngày;
  - biến thể ảnh mẫu mới chờ duyệt (bấm ✔/✘);
  - **màn lạ cần gắn nhãn:** chủ dự án chọn nhãn từ danh sách hoặc *khoanh vùng cần bấm* ngay trên ảnh, thay cho việc gửi ảnh chụp vào chat. Nhãn này vào thẳng dữ liệu học.
- Đây là chỗ bot "thông minh hơn sau mỗi lần làm" rõ nhất: mỗi lần chủ dự án khoanh 1 vùng, mọi máy đều học.

## 4. Thứ tự và ước lượng

| Giai đoạn | Phụ thuộc | Công sức ước lượng | Rủi ro |
|---|---|---|---|
| **E** | — | nhỏ (1 phiên) | Dung lượng ảnh, đã có trần |
| **F1 + F2** | E | vừa | Biến thể sai → có F4 + duyệt 2 lần |
| G | E | vừa | — |
| H | E, G | vừa | Học sai hướng → luôn giữ 10 % thăm dò, quy tắc cứng ngoài học |
| F3, I | E, F | vừa–lớn | — |

Đề xuất làm **E rồi F1+F2** trước. Đây là gốc của cả hai lời phàn nàn (nhận diện kém, không học được gì), và đo được ngay bằng tỉ lệ chạm trượt.

## 5. Không làm

- Không dùng mô hình để bấm nút mới chưa có trong danh sách an toàn.
- Không gửi ảnh hay dữ liệu ra ngoài máy (không dùng API đám mây).
- Không cài thư viện mới khi chưa hỏi.

---

# Báo cáo giai đoạn E + F (2026-11-20)
Chủ dự án duyệt "làm E+F" ngày 2026-11-20.

## Đã làm
| Việc | File |
|---|---|
| **E** Bảng `exp` (`memory.db`): mỗi lần `tap` / `tap_tpl` / `tap_first` / phím Back ghi bước, ai chạm (`module.hàm`), ảnh mẫu, điểm khớp, toạ độ, màn trước; **kết quả đo ở lần chụp kế tiếp**: `reward` (bảng thưởng) / `dot_gone` (chấm đỏ mất) / `changed` (màn đổi) / `local` (vùng quanh điểm chạm đổi) / `none`, độ trễ. Ảnh cắt 96×96 quanh điểm chạm → `data/exp/crops/` (bỏ trùng dHash, trần 20 000) | `bot/learn.py`, `bot/ctx.py`, `bot/memory.py` (v4), `bot/runner.py` |
| **E** Sửa nhật ký `nav`: trước đây cột `changed` ghi lệch 1 dòng (kết quả của hành động *trước*) → số "60 % chạm trượt" ở mục 1 bị sai lệch; nay ghi đúng hành động đó | `bot/ctx.py` `goto()` |
| **E** "Chỗ chết": thống kê tỉ lệ ăn theo (ảnh mẫu, ô lưới 24 px), 14 ngày. `goto()` gặp nút ở chỗ chạm ≥ 8 lần mà ăn < 10 % → dùng Back luôn | `Learner.dead_spot` |
| **F1** kNN màn hình (numpy, cosine): đặc trưng 1632 chiều (ảnh xám 27×48 + histogram HSV lưới 4×3 + mật độ biên 9×16). Mỗi màn `goto()` nhận ra → thêm mẫu (bỏ mẫu gần trùng). Màn `unknown` **đứng yên** → hàng xóm sim ≥ 0,94 & tin ≥ 0,8 → chạm đúng nút đóng/quay lại của hàng xóm | `bot/learn.py`, `Ctx._learned_action` |
| **F2** Biến thể ảnh mẫu: màn lạ đứng yên mà nút đóng/quay lại khớp 0,65–0,82 → chạm thử; thành công = màn đổi **và** màn mới nhận ra được. Đúng ≥ 2 lần, 0 lần sai → hồi quy `tests/fixtures/screens` (F4) → `templates/<tên>@auto<N>.png`; `vision.py` dùng mọi biến thể (lấy điểm cao nhất) | `bot/learn.py`, `bot/vision.py`, `bot/screens.py` (`near_miss`) |
| An toàn | Chỉ học / chạm thử nút trong `learn.LEARNABLE` (X, Đóng, <, Huỷ thoát, chạm để tiếp tục). Không học nút nhận/mua/nâng cấp. Màn đang chuyển động (trận đánh) không chạm thử — đã gặp: nút góc trái trận chạy đường khớp `btn_back2` 0,80 | |
| Công cụ | `python tools/learn.py report | train | eval | cand`; cấu hình `learn:` trong `config.yaml` | |

## Đo offline
- Chọn đặc trưng kNN trên 127 ảnh có nhãn (bỏ-1-ra): bản đơn giản 93,7 % (sim ≥ 0,9: 96,7 %); **bản dùng 94,5 % (sim ≥ 0,9: 100 %)** → đủ tin để chạm theo hàng xóm.
- Nạp 91 mẫu từ ảnh cũ (`tools/learn.py train`). Hồi quy: `check_screens` 13/13, `check_tutorial` 29/29.

## Bổ sung 2026-11-21
| Việc | File |
|---|---|
| **Ghi thao tác tay của chủ dự án** ("mỗi khi tôi click, kéo thả là bot chưa hoàn thiện"): luồng đọc `getevent` mỗi máy bot đang ghé → chụp ảnh lúc chạm + ~1,2 s sau + ảnh đánh dấu (vòng tròn / mũi tên kéo) vào `logs/human/<ngày>/`, `exp` kind=`human`, bước đang chạy thành "có ảnh lỗi". Tắt: `learn.watch_human: false` | `bot/human.py`, `bot/runner.py` |
| Lọc chạm **của chính bot**: trên LDPlayer `input tap` cũng hiện ở `/dev/input/event2` và `getevent` về trễ vài giây → `Device` ghi mọi lần chạm/kéo/Back *trước* khi gửi lệnh; sự kiện trùng chỗ (±25 px) trong 8 s bị bỏ (mỗi lần chạm của bot trừ 1 sự kiện); lái quân (`steer`) bỏ qua theo `steer.active_serials`. Lần chạy đầu (00:02–00:11) bị ghi nhầm ~60 sự kiện → đã chuyển ra `logs/human_false/`, xoá khỏi `exp` | `bot/device.py`, `bot/human.py`, `bot/steer.py` |
| Thứ tự bước mới (chủ dự án): chấm đỏ → quà → tình báo → xây → lính → nghiên cứu → liên minh, chiến dịch → phản quân → thu thập | `bot/runner.py` `ORDER`, `web/options.py` |
| Phản quân tập kích: từ nhà chính cấp 15, 5 lượt/ngày (reset 0h UTC), trigger lịch mỗi 60′ khi chưa đủ | `scheduler.rebels_ready/plan_rebels`, `config.yaml` `rebels.*` |
| Thu thập: `observe` đặt timer `arrive:<i>` lúc đội tới mỏ → lịch ghé lúc đội **cuối cùng** tới mỏ + 1′ để đọc giờ thu thập xong; giờ về = giờ thu thập xong + thời gian đi của **chính đội đó** (đi = về) | `observe.remember`, `scheduler.plan_gather` |
| Làm theo hướng dẫn của game hiện giữa các bước (bàn tay / V / ô đỏ) sau mỗi bước | `tutorial.guide_visible`, `Runner._follow_guide` |
| Nhận diện: bàn tay to (tới 110 px), cột sáng bị xe che (cửa sổ ô đỏ 300 px khi thẳng hàng ±25 px) | `tutorial.find_hand_beam`, `find_beam`; hồi quy 33/33 |
| Sự kiện chữa thương: còn hộp cứu thương → chạm hộp → chạm vòng vàng; hết (số 0) thì dừng; không bao giờ chạm "+" | `notify.heal_event`, `templates/event/heal_*` |
| Chiêu mộ ở chế độ `follow`: V chỉ "Chiêu mộ 10 lần" + nút có chấm đỏ (đủ phiếu) → bấm 1 lần | `tutorial.decide` 0a, `badges.red_dots(min_v)` |
| TK chính #1: tình báo chỉ ghim vàng/tím (`notify.intel_only_gold`), 2 thợ xây (`build.max_builders`), lịch xây khi còn thợ rảnh (observe đọc "x/y" cạnh icon búa) | `notify.pin_gold/special_pins`, `observe.read_builders`, `scheduler.plan_build` |
| Phân loại thắng/thua: màn thắng mới ("Thắng toàn diện", huy hiệu kiếm vàng) trước đây bị ghi **thua** → chặn nhầm NV chính 5 máy; nay `steer.result_of` | `bot/steer.py`, `tests/fixtures/result/` |
| Chấm đỏ: icon kiếm chéo (tập hợp phản quân/quái) bỏ qua; quà liên minh: tab thường chỉ nhận khi "Có thể nhận" > 0 | `reddots._kind`, `alliance.gifts` |
| Lối chơi: rương Mỏ khoáng sản; Đấu trường 3 lượt miễn phí, chỉ lực chiến đỏ, nhớ đối thủ đã thua | `bot/modules/play.py`, `templates/play/` |
| Phản quân tự tập kết: chạm Phản quân Cơ giáp quanh căn cứ → "Tập kết tấn công" → 3 phút "Xác nhận" → quân đoàn → "Xuất chinh" khi chữ xanh "Thắng toàn diện"; trí nhớ `rebels_levels` (cấp cao nhất đã xuất chinh, cấp dự đoán thua) | `rebels.attack`, `templates/rebels/`, `tests/fixtures/rebels_*` |

## Kết quả đo giai đoạn E + F (3 giờ chạy thật, 2026-11-21 ~01:00, #0 #1 #2 #3 #5 #6)
| Chỉ số | Trước (mục 1) | Sau | Mục tiêu | Ghi chú |
|---|---|---|---|---|
| Lần chạm có kết quả đo được | 0 % | **97 %** (1192/1224) | ≥ 95 % | E đạt |
| Chạm "ăn" (màn/vùng đổi, chấm đỏ mất, có thưởng) | không đo được | **92 %** | — | trượt 8 % |
| Chạm trượt trong `goto()` | 60 % (số sai, lệch 1 dòng) | **20 %** (55/280) | < 30 % | đạt; con số cũ là do lỗi ghi lệch, không phải bot tốt lên 3 lần |
| Màn không nhận ra | 4,7 % | **3,0 %** (30/996) | < 1 % | **chưa đạt** |
| Bước không "ổn" | 22 % | **26 %** (42/161) | (mục tiêu của H) | tăng vì có thêm bước mới (Lối chơi, phản quân) và ảnh lỗi từ ghi thao tác tay |
| Thời gian 1 lần ghé | 9,9′ | **8,8′** | — | |
| Mẫu kNN màn hình | 0 | **369** (city 164, panel 96, world 48, popup 48…) | — | tự tăng mỗi lượt |
| kNN / chạm thử nút gần khớp được dùng trên máy thật | — | **0 lần** | — | 30 màn lạ đều là màn đang chuyển động (trận, hoạt ảnh) → bị chặn có chủ ý |
| Biến thể ảnh mẫu tự học | 0 | **0** | — | chưa có ca nào đủ điều kiện |
| Chỗ chết phát hiện | — | 1 (@96,720, 0/10) | — | |

**Đánh giá:** E hoàn thành (bot đo được kết quả gần như mọi lần chạm). F đã chạy đúng cơ chế nhưng **chưa tạo ra cải thiện đo được**: kNN và biến thể ảnh mẫu chưa kích hoạt lần nào vì màn lạ thật sự toàn là màn động. Lợi ích lớn nhất của đợt này đến từ những gì **dữ liệu E làm lộ ra**: ghi nhầm thắng → thua (chặn nhầm 5 máy), dự đoán thắng bị đọc sai (thoát khỏi chiến dịch), ghi thao tác tay của chủ dự án. Bước trượt nhiều nhất: `mainquest` (58 % ăn), phím Back (45 %), `hero_story` (69 %).

---

# Giai đoạn G + H + I (2026-11-21)
Chủ dự án: "Báo cáo giai đoạn E+F rồi làm tiếp giai đoạn G+H+I".

| GĐ | Việc | File |
|---|---|---|
| G2 | **Nhớ vị trí nút**: `Vision.find` không có ROI → thử trước vùng ±60 px quanh lần thấy gần nhất; khớp ≥ 0,93 thì dùng luôn, không thì tìm cả màn như cũ | `bot/vision.py` (`prior`) |
| G3 | **Nhớ chấm đỏ vô ích giữa các lần ghé** (`reddots.dead_h`, mặc định 2 h): không mở lại mỗi lần ghé | `bot/modules/reddots.py`, fact `reddots_dead` |
| G1 | Chỗ chết (≥ 8 lần, ăn < 10 %) → Back (đã có từ E) + thống kê phím Back theo màn | `bot/learn.py` |
| H1 | **Thời gian chờ tự thích nghi**: mỗi thao tác (`module.hàm|ảnh mẫu`) học thời gian game phản ứng (chụp liên tục tới khi màn đổi); đủ 8 mẫu → chờ p80 + 0,35 s (≤ thời gian cũ); 15 % lần vẫn đo lại. Lần màn không đổi tính = thời gian cũ → thao tác hay "không ăn" không bị rút ngắn. Tắt: `learn.adaptive_wait: false` | `Ctx._after_tap`, `Learner.react_wait`, cột `exp.react` |
| H2 | **Bandit Thompson** ở `goto()`: màn popup/bảng → chạm nút đóng hay phím Back, chọn theo Beta(ăn, trượt) đã học | `Learner.choose_close` |
| H3 | **Giá trị bước**: bước chạy kèm trắng tay ≥ 2 lần liên tiếp ở một máy → chu kỳ ×2, ≥ 4 lần → ×4 | `scheduler.value_factor` |
| I | **Trang web `/hoc` "Bot học được gì"**: tỉ lệ chạm ăn, chạm trượt nhiều nhất, chỗ chết, thời gian chờ đã học, mẫu kNN, thao tác tay gần đây; **dạy màn lạ**: chọn loại màn (+ bấm chỗ cần chạm để thoát) → mẫu kNN `human` (mọi máy dùng ngay) + ảnh vào `tests/fixtures/taught/`; **duyệt biến thể ảnh mẫu** (hồi quy trước khi nhận) | `web/learn.html`, `web/server.py` (`/api/learn*`), `learn.summary/teach` |

Kèm sửa lỗi chủ dự án báo: **chiến dịch thoát ra dù "Thắng toàn diện"** — ảnh mẫu dự đoán chỉ khớp 0,77–0,79 < 0,82; nay `campaign.predicted_win` (ảnh mẫu ≥ 0,7 hoặc chữ xanh) + bấm "Tự xếp đội hình" trước khi xem dự đoán (nhiệm vụ chính, chiến dịch, tân thủ); mở lại các máy bị chặn nhầm "không dự đoán thắng". Hồi quy 34/34.
| **Cướp bóc xe khai thác** (học từ thao tác tay của chủ dự án 01:10–01:12 trên #1, 31 ảnh `logs/human/20261121/0110*–0112*`): Lối chơi → Mỏ khoáng sản → tab "Xe khai thác của người khác" → chỉ xe **cam (SSR) / tím (SR)** (nhận theo màu xe + màu chữ SSR/SR trên popup) → đọc tên + lực chiến từng xe → chọn đối thủ **yếu nhất trong ngưỡng** → "Tới cướp bóc" → "Cướp bóc" → đọc lực chiến quân đoàn → "Chiến đấu" → "Thất bại"/thắng. 4 lượt/ngày theo số game hiện ("Số lần cướp bóc còn lại N/4", reset 4h UTC). Trí nhớ `loot_mem`: người đã thua (14 ngày), lực chiến thua thấp nhất, tỉ lệ đối thủ/quân đoàn đã thắng cao nhất & đã thua thấp nhất; chưa thắng lần nào → chỉ đánh đối thủ yếu hơn quân đoàn mình. Đã nạp sẵn trận mẫu: thua (Th1)Hiếudls 493.760.508 với quân đoàn 220.020.045 | `play.loot*`, `templates/play/`, `tests/fixtures/loot_*` |
| Liên minh (ảnh chủ dự án #1): chấm đỏ "66" ở nút Liên minh không bao giờ mất → `reddots` mở liên minh lặp lại (quyên góp 7 lần liên tiếp) → nay Liên minh tối đa 1 lần / bước, mọi vị trí tối đa 2 lần; `notify.hub` không quét chấm đỏ trong bảng Liên minh (từng chạm nút **"Đến"** có chấm đỏ ở tab Lãnh thổ — chủ dự án gạch chéo); thêm **nhận rương BOSS liên minh** (30 % / 60 % / Tiêu diệt) và **"Đến thu thập" Mỏ liên minh** | `reddots.run`, `notify.in_alliance`, `alliance.boss/ally_mine`, `templates/ally/` |
| **Căn cứ trên web** (chủ dự án: "web chưa lưu trạng thái khiên…, thời gian xây, nghiên cứu"): `observe` đọc khiên dưới VIP (icon xanh + đếm ngược = đang bảo hộ; xám "Chưa bảo hộ"), thanh tiến độ xanh trên công trình (OCR nhiều khung, chỉ nhận chuỗi đúng dạng `Nd:hh:mm:ss`) → `state.json` (`shield`, `queues`, `builders`) + timer `build:<i>` cho lịch; web mục "Căn cứ". Chưa tách được xây và nghiên cứu (cần ảnh hàng chờ) | `observe.base_state/read_shield/progress_bars`, `web/index.html` `baseHTML` |
| **Bị tấn công = màn nháy đỏ**: chưa có ảnh mẫu cảnh báo → nhận 2 mép trái/phải ≥ 60 % đỏ, chỉ ở thành phố/bản đồ, 2/3 khung (nền đỏ TT phúc lợi làm mép đỏ 49 % → không tính); `defense.red_flash` (tắt: `defense.red_flash: false`) | `bot/modules/defense.py` |
| Mỏ liên minh: sau "Đến thu thập" là vòng menu quanh Xưởng Hợp Kim → chọn "Thu thập" | `alliance.ally_mine`, `templates/ally/mine_collect.png` |
| **Nghiên cứu** (ảnh Sở Công Nghệ Cấp 30, #1): chỉ 1 hàng (icon "1/1" thứ hai cột trái). Mở bằng icon đó → "Sở Công Nghệ"; có nút "Chi tiết" ở đáy = đang nghiên cứu → đọc tên + thời gian còn lại → timer `research` (lịch không ghé vì nghiên cứu tới khi xong) + web; rảnh → tìm node huy hiệu x/y với **x < y** (Hough + OCR), 3 tab, cuộn. Chưa có ảnh nút "Nghiên cứu" trong chi tiết node → lưu ảnh `research_node` để cắt | `bot/modules/research.py` (viết lại), `templates/research/` |
| TK chính #1: thanh tài nguyên 6 ô (thêm dầu, hợp kim; thể lực "363,000") → `ocr.TOPBAR_MAIN` tự nhận; "Hành quân 4/5" bị đọc "4S" → thêm OCR Otsu phóng 4; lượt phản quân đọc từ "Gửi Quà Thường: x/21" (đã đánh = 21 − x, tính cả đánh tay) → `rebels_done_today` lấy số lớn hơn. Ghi chú: #1 chưa từng chạy tới `gather`/`observe` vì web bị khởi động lại liên tục khi nạp code | `bot/ocr.py`, `Ctx.read_marches`, `alliance.gift_sent`, `scheduler.rebels_done_today` |
| Nhiệm vụ chính (chủ dự án): chỉ làm NV ở thanh dưới; bấm vào sẽ nhảy tới chỗ cần làm. Công trình **đang xây** (thanh tiến độ ngay trên menu) → ghi `mainquest_busy_until` = lúc xây xong, không làm NV ở các lượt sau tới khi xong; công trình **Lv.30** (cấp tối đa) → bỏ. OCR thời gian 4 nhóm "1d:05:40:52" khi chữ 'd' bị đọc thành số | `build.menu_busy/menu_level`, `mainquest.run`, `observe.bar_time` |
