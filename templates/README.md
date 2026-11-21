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
| msg_not_found / mine_occupied / msg_march_full / msg_no_troops.png | (tuy chon) chua gap |

Sau "Tim kiem" ban do can giua mo vao `gather.node_xy` (270,452). Menu sai thi bot dong bang phim Back
(khong cham man hinh - ben trai co icon su kien). "Hanh quan x/y" doc tu `march_counter_roi` bang digits/.

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
