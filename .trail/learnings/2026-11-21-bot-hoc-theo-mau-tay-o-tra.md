---
title: "Bot hoc theo mau tay o may #3 thay vi chay cac buoc theo thu tu co dinh"
author: Trần
date: 2026-11-21
branch: roadmap-impl
cost: { minutes: 24, tokens: 100553 }
id: l-d9399f6f
scope: repo
status: active
src: agent
touches:
  - bot/runner.py
  - bot/ctx.py
  - bot/modules/gather.py
  - web/index.html
  - bot/imitate.py
  - bot/ocr.py
  - tests/legacy/test_imitate.py
  - CLAUDE.md
---

## Decided
- Chu du an (2026-11-21): bo chay tuyen tinh ORDER chi o may #3; #3 sang che do "hoc mau": bot mo game roi dung yen, ghi moi thao tac tay; cac may khac giu ORDER.
- Lam theo = phan ung theo man hinh (gap man giong man da lam mau -> cham dung cho do -> kiem man ket qua), khong phat lai macro.
- An toan = tin thao tac lam mau nhung chan nut nguy hiem (kim cuong / Mua / Nap / Tang toc ngay); chu du an go duoc tren web.
- Hoc tu thao tac tay thuong ngay: chi qua hang cho duyet tren web, khong tu hoc.
- Moi script/cong cu offline dung OCR phai khoi tao OCR truoc; ham doc chu quanh cho cham cua bo "lam theo mau" tu khoi tao neu chua.
- Chu du an: nut "... ngay" (Xay dung/Tang cap ngay) o moc mien phi hien "Mien phi" thay so kim cuong = 0 kim cuong -> dung luat, bot duoc bam. Doc ra so kim cuong hoac khong doc duoc dong duoi -> van chan.

## Tried and ruled out
- Tat ORDER cho moi may: bo vi de bo sot viec hang ngay khi chua hoc du.
- Phat lai nguyen chuoi (macro): gay khi game hien popup khac thu tu.
- Tu nhan bien the anh mau / tu hoc thao tac tay: da sinh 2 bien the rac cho nut quay lai (nen mo, mat nhan vat) vi cham nen ngoai popup cung dong popup -> bi tinh la "dung".
- Tin ket qua "0 nut bi chan nham" lan quet dau: sai, vi OCR chua khoi tao nen moi chuoi deu rong (9 ms/lan la dau hieu; doc that ~150 ms/lan). Sau khi khoi tao: 192/368 cho cham doc duoc chu, bat dung 5 lan chu du an bam "Xay dung/Tang cap ngay".

## Watch out
- Che do agent chi quyet dinh KHI NAO ghe may; trong lan ghe runner van chay ORDER -> trong "van tuyen tinh".
- HumanWatch doi toa do sai ~5% (vd 33,1168 / 675,181 tren man 540x960) -> phai sua truoc khi giai doan 2 dua vao ban ghi.
- Hai web cung nghe cong 8080 tren Windows khong bao loi; request roi vao ban cu.

In the code:
- schedule.mode = "demo" theo may (web: o "Che do" + nut "Bat dau hoc mau"); config `demo.idle_min/max_min/keep_open`; bot/demo.py session(); Runner._auto_ids() loai may demo khoi vong auto/agent.
- Giai doan 2 (lam theo) CHUA lam: viet decide() thuan, test offline tren logs/human cua #3 truoc khi chay that.
- Moi phim Back qua Ctx.press_back (khong bam o thanh pho/ban do); hang cho thao tac tay: bot/human_review.py, chot server: hop thoat chi day nut Huy.
- Anh gia lap ngau nhien lam mo cho test nhan dien man rat giong nhau (cosine ~0,996) -> muon "man khac" phai ve khoi lon khac han.
- Chen duong dan Windows qua heredoc Python: "\t" thanh dau tab -> dung dau "/".

- bot/ocr.py: text() tra "" khi _ok khong True; ocr.init(cmd) chi duoc goi trong Runner.__init__.
- bot/imitate.py text_near(): goi ocr.init("C:/Program Files/Tesseract-OCR/tesseract.exe") neu ocr._ok is None.
- Test hong 3 lan khong phai do logic: chen regex qua heredoc Python lam "\b" thanh ky tu backspace (\x08) trong file -> regex khong khop. Kiem bang repr() dong code; sua bang script dung chr(92)+"b".
- OCR 1 dong (psm 7) tren nut 2 dong doc kem; doc ca khoi (psm 6, cao 80 px) moi ra "xay dung ngay @ mien phi" (@ = bieu tuong kim cuong).

- bot/imitate.py: is_danger() + FREE = r"\bmien ph"; text_near() vung x+-110, y-40..y+40, psm=6.
- Kiem tren 368 cho cham mau #3: 8 nut "ngay" mien phi duoc cho bam, 1 chu meo bi chan.
