---
title: "Nhan dien: khop mau da ty le giai quyet lech ty le, con CLAHE va Sobel lam khop te hon; uoc luong nhieu bang MAD sai tren anh so nguyen"
author: Trần
date: 2026-11-22
branch: roadmap-impl
cost: { minutes: 77, tokens: 357440 }
id: l-de63121e
scope: repo
status: active
src: agent
touches:
  - src/aowbot/perception/contract.py
  - src/aowbot/perception/core/__init__.py
  - src/aowbot/perception/diagnostics/__init__.py
  - src/aowbot/perception/core/frame.py
  - src/aowbot/perception/core/buffer.py
  - src/aowbot/perception/core/roi.py
  - src/aowbot/perception/diagnostics/inspector.py
  - tools/vision_inspector.py
  - tests/unit/test_perception_core.py
  - tests/unit/test_perception_inspector.py
---

## Decided
- Benchmark Phase 2 (121 neo that, bien doi tong hop): khop mau BGR da ty le 0,90-1,10 giu 100% khi anh lech ty le +-10% (legacy chi 17-47%), khong tang bao nham dang ke. Che 25% khong cach nao cuu duoc -> can dac trung cuc bo (ORB) o Phase 3.
- Do sang toan cuc khong phai nguyen nhan chinh: legacy van giu 100% voi gamma/sang/toi. Khong dua CLAHE hay Sobel vao khop mau.
- detect_change dung mac dinh k=4, min_area=0,01 (do tren 715 cap khung); nhieu duoi 2% bao nham.
- ORB mac dinh cua OpenCV (edgeThreshold 31, patchSize 31) loai het diem dac trung cua mau nho: chi 2 trong 121 mau co tu 12 diem tro len. Ha edgeThreshold va patchSize xuong 15 thi 32 trong 121 mau (khoang 26%) dung duoc. Phan con lai la icon phang it goc, ORB khong ap dung.
- ORB phai chay trong ROI quanh cho nghi ngo (ROI-first) va dat nfeatures 2000: voi 500 diem tren ca khung 540x960 no bo sot ca vat khong bi che.
- Detector khong ket luan: luon tra ve trang thai UNCERTAIN, ket luan thuoc tang hop nhat o Phase 5.
- Tim bang anh xam cho nhanh nhung phai xac minh lai bang BGR tai dung cho tim thay; BGR thap hon xam qua 0,10 thi tim lai bang BGR day du.
- Detector phu (ORB) khong duoc mot minh day ung vien len CONFIRMED: can xac suat cua template >= 0,5.

## Tried and ruled out
- CLAHE va gradient Sobel truoc khi khop: retention thap hon legacy (blur 1,2: 0,37 va 0,46 so voi 0,88), gradient bao nham 33% khi vang mat.
- Uoc luong san nhieu bang MAD: tren so nguyen trung vi |chenh lech| bi lam tron (nhieu sigma=2 cho 1,48) nen nhieu bi bao thanh thay doi cuc bo 100%. Doi sang (p95-p5)/3,29.
- Hoi quy affine binh phuong toi thieu tren moi diem: vung doi lon (17% dien tich) keo lech mo hinh, bo sot thay doi cuc bo. Khoi dau a=1, b=trung vi, sigma bang IQR.
- Nguong co dinh 128 cho phat hien hinh: hong hoan toan khi anh toi (P va R bang 0 o do sang 0,5). Otsu giu P 0,997 va R 0,992 trong ca ba che do sang. Adaptive threshold cho P chi 0,75 vi vo manh tren nen co ket cau.
- Chon xam lam mac dinh vi retention va ti le bao nham bang BGR tren benchmark tong hop: sai, vi tap vang mat chi la inpaint, khong co vat giong hinh khac mau.
- Cat tia ty le khi vang mat: diem o ty le 1,0 cua vat dung (p1 0,27) chong lan voi vang mat (p95 0,55) nen khong an toan.

## Watch out
- Neo la mau cat tu chinh khung nen so do la do ben, khong phai do chinh xac. Chua co hard-negative.
- gain 1,1 van bao cuc bo nham 18% (bao hoa 255 pha mo hinh affine).
In the code: src/aowbot/perception/features/brightness.py, tools/perception_phase2_bench.py, docs/perception/PHASE2_RESULTS.md
- Anh test tong hop co ket cau qua mem lam khop mau don ty le nhin nhu chiu duoc lech ty le; phai tang do sac nen thi moi thay khac biet voi khop da ty le.
In the code: src/aowbot/perception/detectors/{orb,template,shape}.py, tools/perception_phase3_bench.py
- Nut X xanh-trang khop X do, nut Xay dung lai khop Bat dau lai (chu 'lai' chung cho 9 inlier ORB) la hard negative that, nen dua vao tap kiem thu.
- Muc tang recall 0,887 tung bao la do cac xac nhan chi nho ORB; sau khi chan con 0,829 xap xi legacy 0,833.
In the code: src/aowbot/perception/detectors/template.py, src/aowbot/perception/fusion.py, tools/perception_perf_bench.py, docs/perception/PHASE456_RESULTS.md
