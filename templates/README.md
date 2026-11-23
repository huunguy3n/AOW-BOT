# Anh mau (templates) - Age of Warpath bot

Tat ca anh mau cat tu man hinh **540x960 (doc, DPI 240)** (cung do phan giai instance LDPlayer).
Cach lam: `python main.py --capture 0` -> mo file trong `logs/` bang Paint -> cat dung
vung nut (nho gon, chi lay phan dac trung, tranh nen thay doi) -> luu PNG dung ten duoi day.
Kiem tra con thieu gi: `python main.py --check`. Thieu anh nao thi bot bo qua thao tac do va ghi canh bao.

## common/ (dung chung)
| File | Mo ta |
|---|---|
| btn_to_world.png | Nut qua dia cau goc trai duoi (dang o thanh pho) |
| btn_to_city.png | Nut ve thanh pho (dang o ban do the gioi) |
| btn_x.png / btn_x_small.png | Nut X dong bang |
| btn_close.png | Nut "Dong" o man thuong |
| btn_back.png | Mui ten quay lai goc trai tren cua cac bang |
| btn_cancel_exit.png | Nut "Huy" khi game hoi thoat game (lo bam Back) |
| btn_help.png | Nut tro giup lien minh (bat tay) |
| btn_free.png | Nut "Mien phi" tang toc (khi con < 5 phut) |
| msg_insufficient.png | Bang bao thieu tai nguyen |

## gather/ (gui quan di mo)
| File | Mo ta |
|---|---|
| btn_search.png | Icon ong nhom goc phai duoi ban do the gioi |
| tab_food / tab_metal / tab_oil / tab_alloy.png | Chu duoi hinh mo: Xuong Thuc Pham / Luyen Kim / Loc Dau / Hop Kim (tim voi nguong 0.72 vi chu lech khi cuon) |
| btn_level_minus / btn_level_plus.png | Nut - / + cap (bam tung buoc 0.5s, bam nhanh game bo qua) |
| lv/1.png ... lv/8.png | So trong o "Cap:" - bot doc cap hien tai roi bam +/- toi dung cap. Hop kim thap nhat cap 3 |
| btn_search_go.png | Nut "Tim kiem" |
| btn_gather.png | Nut XE TAI "Thu thap" trong menu vong tron quanh mo. KHONG cat "Chuyen thanh"/"Chiem linh" |
| btn_recommended.png | Nut "Doi hinh de xuat" |
| btn_march.png | Chu "Xuat chinh" (khong cat dong ho) |
| msg_type_locked.png | Chu "tam thoi khong the thu thap" (chua du cap, vd Hop kim can cap 9) -> bot bo ca loai mo |
| march_header.png | (P3, co) Chu "Hanh quan" + mui ten goc trai tren ban do the gioi (x 8-110, y 138-158). Vang mat = 0 doi dang di |
| dlg_contested.png | (P3, co) Than hop thoai "Chu y! Co Chi huy truong khac dang hanh quan den diem tai nguyen nay..." sau Xuat chinh -> bot bam Huy, KHONG bao gio Tiep tuc |
| msg_not_found.png | (P3, CAN CHUP) Thong bao noi giua man (y ~270-380) sau "Tim kiem" khi khong co mo loai/cap do. Cat dong chu, khong cat ban do |
| mine_occupied.png | (P3, CAN CHUP) Cham mo dang co doi nguoi khac: bang/menu mo hien nut "Tan cong"/"Trinh sat" thay vi xe tai "Thu thap". Cat ten nguoi chiem/nhan dang chiem hoac nut Tan cong (KHONG bam) |
| msg_march_full.png | (P3, CAN CHUP) Bam xe tai "Thu thap" khi "Hanh quan x/y" da day -> thong bao noi het quan doan. Cat dong chu |
| msg_no_troops.png | (P3, CAN CHUP) Bam xe tai "Thu thap" / Xuat chinh khi khong con linh -> thong bao khong du binh. Cat dong chu |

Thieu 4 anh CAN CHUP: bot log `thieu anh mau gather/<ten>` (1 lan/gio) va doc thong bao bang OCR (`gather_rules.classify_msg`), khong bam mo.

Sau "Tim kiem" ban do can giua mo vao `gather.node_xy` (270,452). Menu sai thi bot dong bang phim Back
(khong cham man hinh - ben trai co icon su kien). "Hanh quan x/y" doc tu `march_counter_roi`: P3 bang `mdigits/` truoc, roi Tesseract, roi `digits/`.

## mdigits/ (P3 - doc "Hanh quan x/y", bot/march_count.py)
`1.png` ... `5.png`, `slash.png` - cat tu anh that o khung "Hanh quan" ban do the gioi, khop xam. Do tren 547 anh: dung 544, sai 0, 3 mo -> khong ro.

## digits/ (du phong khi khong co Tesseract)
`0.png` ... `9.png`, `slash.png` - cat tung chu so trong o "Hanh quan x/y".

## research/ (nghien cuu nhanh thu thap)
| File | Mo ta |
|---|---|
| btn_research_building.png | Toa nha nghien cuu / Hoc vien tren thanh pho |
| btn_research_enter.png | Nut "Nghien cuu" hien ra sau khi cham toa nha |
| tab_gathering_tech.png | Tab/nhanh cong nghe thu thap tai nguyen |
| tech_01_gather_speed.png, tech_02_load.png, ... | (tuy chon) bieu tuong tung cong nghe, bot thu theo thu tu ten file |
| node_available.png | Node cong nghe dang sang/mo khoa (dung khi khong co tech_*) |
| btn_research.png | Nut "Nghien cuu" trong bang chi tiet cong nghe |
| research_in_progress.png | Dau hieu dang co nghien cuu chay (thanh thoi gian) |

## train/ (huan luyen - qua bang "Doi ngu huan luyen", khong can tim nha linh tren ban do)
| File | Mo ta |
|---|---|
| queue_icon.png | Icon may bay "0/1" ben trai thanh pho (chi cat icon, khong cat so) |
| btn_goto.png | Nut "Den" canh nha linh dang nhan roi trong bang |
| btn_train.png | Chu "Huan luyen" o nut PHAI (khong cat dong ho). TUYET DOI khong cat nut "Huan luyen ngay" (ton kim cuong) |
| btn_max.png | (tuy chon) nut toi da - thanh so luong mac dinh da toi da |

The cap I..IV o vi tri co dinh (`train.card_x`, `card_y` trong config). Cap bi khoa khong co nut Huan luyen -> bot tu ha cap.

## research/ - LUU Y
Tai khoan MFarm00 (Xuong kien truc cap 4) chua co toa nha nghien cuu; cat anh mau tren tai khoan da co.

## P2 (2026-11-23) - anh mau can chup tren #1 (chua co thi code van chay: log "thieu anh mau <ten>")
| File | Man hinh / vung cat |
|---|---|
| research/btn_research.png | DA CO (2026-11-23, #1 anh 14). Chu "Nghien cuu" nut PHAI bang chi tiet node. Bang nam GIUA man (nut y~491): bot tim tu tren khung bang (node_panel) toi day man, x 200-540; khong thay khung -> 2/3 duoi (y 320-960). Khop "Nghien cuu ngay" chi 0,41 (nguong 0,85) |
| research/node_panel.png | DA CO (2026-11-23). Nut X + icon i goc phai bang node. Nguong 0,9 (khop 0,807 voi hop thoai "Doi da du") |
| research/msg_no_res.png | Bam "Nghien cuu" khi thieu tai nguyen -> hop thoai/thong bao thieu: cat dong tieu de (vd "Tai nguyen khong du"), KHONG cat nut mua/kim cuong |
| train/btn_max.png | KHONG CAN (chu du an 2026-11-23): thanh so luong mac dinh da toi da, khong co nut MAX; `train.use_max_button: false` |
| common/msg_insufficient.png | (dung chung research + train) hop thoai thieu tai nguyen, cat tieu de |

## P4 (2026-11-23) - nhiem vu chinh / follow
| File | Trang thai | Man hinh / vung cat |
|---|---|---|
| rebels/npc_attack.png | DA CO (cat tu thao tac tay `logs/human/20261121/002012-i3-mainquest-091_before.png`, vung x 200-334, y 720-757) - chu du an kiem lai tren 1 phien quan cap khac | Cham thanh nhiem vu "Kich sat N lan phan quan Lv.X" -> ban do, cham muc tieu giua man -> bang "Phien quan Lv.N" (De xuat: luc chien) -> CHI chu "Tan cong" trong nut xanh duoi bang |

Dung lai anh mau co san (khong can chup): `play/btn_arena_fight` + `play/btn_arena_recommend` (man "Cai dat quan doan" kieu moi
cua Chien dich, khop 1,00 tren 8/8 anh `campaign_no_fight`), `gather/btn_recommended` + `gather/btn_march` (Xuat chinh danh
phien quan), `daily/tab_2_main`/`tab_3_daily` + `common/btn_x_small` (bang nhiem vu kieu moi), `intel/title`, `common/btn_to_city`.

## P5 (2026-11-23) - chien dau va tinh huong hiem (chua co thi code bo qua nhanh + log "thieu anh mau <ten>")
| File | Man hinh / vung cat | Tinh huong can cho |
|---|---|---|
| rebels/rally_mech.png | Lien minh -> tab "Su vu" -> "Tin van chien tranh": dong tap ket dang mo -> CHI icon/ten "Phan quan Co giap" tren dong (khong cat ten nguoi mo, cap, dong ho) | Dong minh dang mo tap ket Phan quan Co giap. Chi dung khi chu du an bat `rebels.join_mech_rally` |
| rebels/btn_join.png | Cung dong do: nut tham gia (+ / "Tham gia") o mep phai dong | Nhu tren |
| defense/alert_attack.png | Thanh pho hoac ban do khi CO QUAN DICH DANG HANH QUAN TOI: bieu tuong/bang canh bao (thuong o mep tren hoac canh nut ban do), cat phan khong doi (icon), khong cat dong ho dem nguoc | Can cu bi tan cong / bi trinh sat that. Thieu anh -> chi dua vao mep do nhay (`defense.red_flash`) |
| defense/row_8h.png | Thanh pho -> icon khien -> bang "Bao Ho Chien Tranh": dong khien 8 GIO - cat cung kieu/vung nhu `row_12h.png` (dai tieu de dong ~230x20 px, khong cat so luong / nut) | Mo bang khi co vat pham khien 8h (ngay chien tranh SVS dung 8h truoc 12h). Thieu -> warday/defense bao `missing_tpl`, KHONG mo bang |

Khong phai anh mau (bot tu luu, 1 anh/ngay/may, de chu du an xem/cat tiep): `logs/inv/intel_unknown_attack/` (man sau
"Tan cong" tinh bao ma bot khong nhan ra - 31 lan ngay 22/11), `logs/inv/intel_unknown_target/` (ban do sau "Di" khong
cham duoc muc tieu), `logs/inv/intel_unknown_panel/`, `logs/inv/heal_panel/` (bang benh vien khong thay nut "Hoi phuc"),
`logs/inv/heal_bubble_no_panel/`. Can them 1 anh chu du an chup tay: **bang chua tri cua Benh vien KHI CO thuong binh**
(`python main.py --capture <may>`, luu `logs/`) de kiem nut "Hoi phuc" (tai nguyen) va nut "Hoi phuc ngay" (kim cuong, bot chan).

## qdigits/ (P2 - doc hang cho "x/y" cot icon trai thanh pho, bot/queues.py)
`0.png`, `1.png`, `1b.png` (so 1 co chan), `2.png`, `3.png`, `slash.png`: anh XAM 14 px cao, cat tu anh that
(`tests/fixtures/screen_loop/queues_0-2_0-1_0-3.png`, `logs/snap-city.png`). Them so 4-6 neu gap tong > 3
(cung cach cat: vung so ben phai icon, 14 x 6-9 px). Khac `digits/` (chu "Hanh quan x/y" co co chu khac).

## city/ (thu tai nguyen noi tren cong trinh)
`res_*.png` - moi loai bieu tuong noi (vd `res_food.png`, `res_fist.png`, `res_alloy.png`).

## tutorial/ (tan thu - chi bat cho tai khoan moi)
arrow_yellow.png (mui ten vang chu V), btn_attack.png ("Tan cong"), btn_fight.png ("Chien dau"),
btn_auto_formation.png, btn_claim.png ("Nhan"), btn_upgrade.png ("Tang cap"), btn_confirm_build.png (dau tich),
btn_start_game.png, hint_swipe_gate.png, gate_green.png, hint_dodge.png, msg_warning.png ("CANH BAO"),
build_red.png, zone_green.png.

## common/ - dong bang phan thuong (dung cho rewards & daily)
| File | Mo ta |
|---|---|
| btn_confirm.png | Nut "Xac nhan"/"OK" tren bang "Nhan duoc phan thuong" |
| tap_to_continue.png | Dong chu "Cham de tiep tuc" (bot cham vung trong phia duoi) |
| btn_net_retry.png | Nut "Thu lai" cua hop thoai "Mang ngoai le" luc vao game (Ctx.POPUP_CLOSERS) |
| btn_rebuild.png | Nut "Xay dung lai" khi Xuong kien truc bi danh ve do ben 0 (Ctx.POPUP_CLOSERS) |
| btn_reward_close.png | (tuy chon) nut X rieng cua bang phan thuong - KHONG dung chung voi btn_x |

## rewards/<tuyen>/ (nhan qua) - moi tuyen 1 thu muc, ten tuyen khai bao o config `rewards.routes`
Bot lam: ve thanh pho -> cham `open_1`, `open_2`... theo thu tu -> (neu co) vao tung `tab_*` ->
bam lien tuc `claim_1`, `claim_2`... den khi het -> dong bang phan thuong -> ve thanh pho.

| Thu muc | Goi y anh mau |
|---|---|
| rewards/mail/ | open_1 = icon thu; tab_2_alliance, tab_3_system = tab (trang thai chua chon); once_1 = nut "Doc & nhan nhanh" (luon hien nen chi bam 1 lan) |
| rewards/signin/ | (KHONG dung tu 2026-11-18: "Diem danh 30 ngay" nam trong TT phuc loi, buoc notify nhan) open_1 = icon su kien/diem danh; open_2 = tab diem danh (neu can); claim_1 = nut "Diem danh"/"Nhan" |
| rewards/vip/ | open_1 = huy hieu VIP; claim_1 = nut nhan ruong VIP hang ngay; claim_2 = nut nhan diem VIP |
| rewards/free_chest/ | (chua dung: chua thay ruong mien phi that; "Ruong vat tu chien tranh" co nut Mien phi bi KHOA sau goi tra phi) open_1 = icon cua hang/ruong; claim_1 = nut "Mien phi" |
| rewards/celebration/ | open_1 = icon "Buoi le" (phai thanh pho); claim_1 = nut "Nhan" xanh. 2 hang tab theo cham do: config `rewards.dot_tabs.celebration` (hang Ngay -> hang muc con) |
| rewards/city/ | KHONG co open_*: claim_1, claim_2... = qua noi tren thanh pho (hop qua, xe tiep te...) |

Muon them tuyen khac (vd qua online, qua lien minh): tao thu muc moi + them ten vao `rewards.routes`.
Luu y: chi cat nut o trang thai CO THE NHAN (sang mau, co cham do), khong cat nut da nhan/xam.

## daily/ (nhiem vu)
| File | Mo ta |
|---|---|
| open_1.png | Icon nhiem vu tren thanh pho (open_2... neu can them buoc) |
| tab_1_daily.png, tab_2_main.png | (tuy chon) tab Hang ngay / Chinh-Chuong |
| claim_1.png, claim_2.png | Nut "Nhan" tren dong nhiem vu da xong (moi kieu mau 1 anh) |
| chest_1.png, chest_2.png | Ruong diem nang dong DA DU DIEM (co tia sang lap lanh) - khong cat ruong khoa/da nhan |
| btn_chest_claim.png | Nut "Nhan" trong bang chi tiet ruong |
| chapter_claim.png | (tuy chon) nut nhan thuong chuong |

## Cong cu cat anh nhanh: tools/snap.py
`python tools/snap.py shot ten` (chup), `tap X Y ten` (cham roi chup), `tpl common/btn_x ten` (cham theo anh mau),
`cut ten common/btn_x x1 y1 x2 y2` (cat tu logs/snap-ten.png va bao so diem khop - nen dung 1 diem).
Quy uoc: `once_*` = nut luon hien (chi bam 1 lan); `claim_*` = nut bien mat sau khi nhan (bam den het).

## P6 (2026-11-23) - anh mau cat tu #1 (data/pm-shots/adb, README trong do)
| File | Ghi chu |
|---|---|
| defense/row_8h.png | Tieu de dong "Hiep uoc hoa binh" (8h MIEN PHI, chuan bi 1h, hoi 14h) - chu du an dong y dung. Bot chi bam "Dung" khi OCR thay chu "Mien phi" phia tren nut |
| rebels/btn_join.png | O "+" tren the tap ket (Lien minh > Su vu). Nguong 0,9 + vung x 200-500, y 220-900 (khop 0,75 voi nut "+" benh vien / bang tim kiem) |
| gather/msg_not_found.png | Dong "Khong phat hien muc tieu nay gan Xuong kien truc cua ban!" |
