# Age of Warpath farm bot (LDPlayer 9, nhieu instance)

Bot chay **lan luot** tung instance LDPlayer (ID trong config `instances`, mac dinh 0-8): bat may ->
mo game -> chay cac buoc -> tat may -> sang may ke tiep. Moi tai khoan chay theo thu tu:

1. `tutorial` (tat mac dinh) - qua tan thu theo mui ten vang.
2. `collect_city` - cham cac bieu tuong tai nguyen noi tren cong trinh.
3. `rewards` - nhan qua theo tuyen trong config `rewards.routes` (thu, diem danh, VIP, ruong mien phi, qua noi tren thanh pho).
4. `research` - mo toa nha nghien cuu -> nhanh **thu thap tai nguyen** (toc do thu thap, tai trong...) -> nghien cuu, bam tro giup / mien phi neu co.
5. `train` - vao tung nha linh -> chon **linh T3** -> so luong toi da -> huan luyen.
6. `gather` - gui quan di mo **cho den khi Hanh quan x/y day (x == y)**. Uu tien alloy > metal > food, cap tu cao xuong thap; loai/cap nao khong tim duoc thi thu loai/cap tiep theo. Dung khi day doi, het linh, hoac moi loai/cap deu that bai.
7. `daily` - nhan thuong nhiem vu (hang ngay + chinh) va ruong diem nang dong.

Bat/tat tung buoc trong `config.yaml` -> `modules`, hoac tam thoi: `python main.py --modules research,train`.

## Cai dat (Windows)
1. Cai Python 3.10+ tu python.org (tick "Add to PATH"; tat alias "App execution aliases" cua Microsoft Store neu lenh `python` mo Store).
   Trong LDPlayer: Cai dat -> Khac -> "Go loi ADB" = "Mo ket noi cuc bo" cho moi instance.
2. `pip install -r requirements.txt`
3. (Khuyen nghi) Cai Tesseract OCR de doc "Hanh quan x/y".
4. Sua `config.yaml`: duong dan `ldconsole.exe`/`adb.exe`, danh sach instance, cap mo toi da.
5. Cat anh mau theo `templates/README.md` (`python main.py --capture 0` de chup man hinh), kiem tra `python main.py --check`.
6. Chay thu 1 may: `python main.py --once --only 0`, roi chay that: `run.bat`.

Log: `logs/bot-YYYYMMDD.log`; anh loi: `logs/shots/`.

## Phat trien (cong cu kiem tra)
Cai mot lan: `pip install -e .[dev]` (pytest, ruff, mypy, import-linter, coverage - chi dung khi phat trien,
bot chay khong can). Truoc moi commit:
```
python -m pytest                                          # test (anh fixture chi co tren may local)
python -m ruff check .                                    # ma moi: luat nghiem
python -m ruff check bot web tools main.py --select E9,F63,F7,F82   # ma cu: loi cu phap / ten chua dinh nghia
python tools/check_screens.py && python tools/check_tutorial.py      # hoi quy nhan dien (can tests/fixtures)
```
Kien truc va lo trinh: `docs/strategy/MASTER-IMPLEMENTATION-PLAN.md`, `docs/architecture/`.

## Giao dien quan ly (web)
`run.bat` (hoac `python main.py --web`) -> mo http://localhost:8080
- Moi may: bat/tat auto, "Chay ngay" (auto dang tat thi chi chay rieng may do), bat/tat tung buoc.
- Tai nguyen (kim loai, thuc pham, the luc, vang, kim cuong) + hanh quan: dang di / thu thap xong luc / ve luc.
  Doc bang Tesseract o buoc `observe` cuoi moi luot (ra ban do the gioi).
- Tuy chon chung luu o `data/settings.json` (de len `config.yaml`); trang thai o `data/state.json`.
- Muc "sap co" = da co cho cai dat, bot chua thuc hien.

## Lo trinh
| Giai doan | Noi dung | Trang thai |
|---|---|---|
| 1 | Web quan ly, doc tai nguyen/hanh quan, kiem tra tai trong vs mo | xong |
| 3 | Nhiem vu Chuong/Chinh: "Den" -> nang cap cong trinh (Nhay qua dieu kien), nha chinh <= lv22; lien minh: quyen gop VANG, tro giup | xong |
| 4 | Huan luyen: nha chinh >= lv22 chi luyen T3; chi luyen den khi du so doi x `troops_per_march` | xong |
| 5 | Tham gia tap ket Phan quan Co giap khi con the luc + doi ranh | code xong, CAN anh mau |
| 3b | Chien dich (danh man du doan thang + treo may); cham do: TT phuc loi, Thuong online, Hoat dong, Tinh bao (danh / quet phan quan / nhat tiep te), Chieu mo mien phi, tang cap tuong | xong |
| 2 | Bi tan cong -> khien (vat pham, het thi kim cuong trong tran/ngay), so tan quan; nut Khien tren web | code xong, CAN anh mau |

## Anh mau con thieu (chi cat duoc khi tinh huong xay ra trong game)
`python tools/snap.py shot ten` roi `cut`:
- `defense/alert_attack.png` - dau hieu DANG BI TAN CONG (canh bao do / icon) -> bot tu bat khien. Chua co thi chi bat khien bang nut tren web.
- `rebels/rally_mech.png` + `rebels/btn_join.png` - dong tap ket Phan quan Co giap trong Lien minh > Su vu > Tin van chien tranh va nut tham gia.
- `ally/btn_help_all.png` - nut giup tat ca (Lien minh > Giup do, khi co yeu cau).
- `daily/claim_1.png`, `daily/chapter_claim.png` - nut Nhan nhiem vu da xong / "Nhan toan bo" khi sang.

## Nhiem vu chinh (buoc `mainquest`, chay dau tien) & lai doi quan
- Cham thanh nhiem vu goc trai duoi -> danh / nang cap cong trinh / chien dich / nhan thuong theo noi no dan toi.
- Gap tran khong du doan "Thang toan dien" (boss qua kho) hoac thua -> dung, de cac buoc khac tang suc manh
  (tuong, xay, chien dich, tinh bao, huan luyen); thu lai khi luc chien tang >= `mainquest.power_gain_pct`%.
- Tran kieu chay duong (`bot/steer.py`): giu ngon tay tren doi quan suot tran (sendevent /dev/input/event2,
  ti le x*960/540, y*540/960 - lay tu ban ghi thao tac that), truot ngang toi lan tot nhat:
  nhat bang xanh / vu khi xanh la / thung cuu tro (bang do co linh xanh), ne bang do -N, vong do nem bom,
  vet do xe lao. Chi dat ngon tay khi xac nhan dang trong tran (`campaign/battle_hud`, khong co nut Chien dau).
  `battle.debug_dir: logs/steer` de luu khung hinh co danh dau quyet dinh.

## Cham do (buoc `notify`)
Tim cham do bang mau, gan voi icon ben canh. Tinh bao va bong bong "Nhan" co hoat anh -> suy vi tri tu icon
Chien dich / Chieu mo. Nut "Nhan" xam (chua nhan duoc) bi bo qua nho kiem tra mau (xanh ngoc sat~220, xam ~0).
Bo qua: chat, Lanh tho / Co lien minh (chi R4), "Mo khoa", "Cap mua", "Tiep tuc nhan" (duong tra phi), "Nap the".

## Khong tu dong (co chu dich)
Nut ton kim cuong ("Huan luyen ngay", "Tang cap ngay", quyen gop kim cuong), "Den" o nhiem vu hang ngay
(chieu mo cao cap), nhan tin kenh lien minh, mua do tiem lien minh, xay co, "Tang toc"/"Dung thu" o bang tho xay.
Kim cuong chi tieu cho khien khi bat `defense.shield_buy_gems`, trong tran `defense.gem_cap_daily`.
