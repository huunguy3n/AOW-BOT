"""Kiem tra hoi quy tutorial.decide() tren cac khung da tung lam bot ket (tests/fixtures/tutorial/).

  python tools/check_tutorial.py

Moi ca = chuoi khung dung chung 1 state (mo phong cac vong lien tiep) + ket qua mong doi o khung CUOI:
(hanh dong, tien to ly do). Them ca moi moi khi sua 1 diem ket tren may that (ADR-0011).
"""
import os, sys
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)
import logging
logging.disable(logging.WARNING)       # bo canh bao thieu anh mau
import cv2
from bot.vision import Vision
from bot.modules import tutorial

F = "tests/fixtures/tutorial/"
CASES = [
    # (ten, [khung...], hanh dong, tien to ly do[, state ban dau])
    ("thua tran -> Bat dau lai", ["20261117-235637-i5-tutorial_lose.png"], "tap", "thua -> bat dau lai"),
    ("thua tran 2", ["20261118-000111-i5-tutorial_lose.png"], "tap", "thua -> bat dau lai"),
    ("thua tran 3", ["20261118-000655-i5-tutorial_lose.png"], "tap", "thua -> bat dau lai"),
    ("bang Chuong 2 -> Den", ["20261118-001529-i5-tutorial_stuck.png"], "tap", "bang chuong -> Den"),
    ("popup goi tra phi -> chi bam X", ["20261118-002831-i5-tutorial_stuck.png"], "tap", "dong popup goi tra phi"),
    ("thua co chu V -> theo V", ["20261118-003724-i5-tutorial_lose.png"], "tap", "thua -> theo mui ten V"),
    ("dat Mo quang dau chan do -> keo", ["20261118-010559-i5-tutorial_maxsteps.png"], "drag", "keo dau chan do"),
    ("Xay dung ngay Mien phi", ["20261118-011006-i5-tutorial_stuck.png"], "tap", "xay/nang cap ngay (Mien phi)"),
    ("xay Kho khong co o goi y -> tu tim cho trong", ["build_kho_no_zone.jpg"], "drag", "keo the cong trinh vao o trong"),
    ("can cu bi danh -> Xay dung lai", ["rebuild_popup.png"], "tap", "xay dung lai can cu"),
    ("tuong het nut Tang cap -> quay lai", ["hero_maxed.png"], "tap", "tuong het tang cap duoc", {"hero_lv": 3}),
    ("follow: man chieu mo -> quay ra", ["recruit_premium.png"], "back", "man chieu mo", {"follow": True}),
    ("follow: V chi Chieu mo 10 lan co cham do (phieu) -> bam (chu du an 2026-11-20)", ["recruit_v_ten_tickets.png"], "tap", "V chi Chieu mo", {"follow": True}),
    ("follow: da bam chieu mo 1 lan trong luot -> quay ra", ["recruit_v_ten_tickets.png"], "back", "man chieu mo", {"follow": True, "recruit_taps": 1}),
    ("follow: du doan thang, anh mau chi 0.79 -> van Chien dau (#1 2026-11-21)", ["campaign_pred_win_i1.png"], "tap", "chien dau", {"follow": True, "formation": True}),
    ("follow: doi hinh khong du doan thang -> khong danh", ["formation_weak.jpg"], "weak", "doi hinh khong du doan thang", {"follow": True, "formation": True}),
    ("tan thu: doi hinh -> van danh (bat buoc)", ["formation_weak.jpg"], "tap", "tu xep doi hinh"),
    ("menu cong trinh 1 khung -> cho chu V", ["ch5_menu_a.jpg"], "wait", "menu cong trinh: cho"),
    ("lop phu: V chi Tang cap, Mien phi bi khoa -> theo V (#4)", ["hq_upgrade_locked_free_i4.png"], "tap", "mui ten V (Mien phi bi khoa)", {"follow": True}),
    ("lop phu: V chi Tang cap, Mien phi bi khoa -> theo V (#2)", ["hq_upgrade_locked_free_i2.png"], "tap", "mui ten V (Mien phi bi khoa)"),
    ("ban tay chi thung tiep te -> cham thung", ["hand_supply_box.png"], "tap", "ban tay xanh"),
    ("tran chay duong bieu tuong dich khac -> lai quan (#5)", ["battle_enemy2.png"], "steer", "tran chay duong", {"follow": True}),
    ("ban tay nghieng chi tank (cot sang) -> cham tank (#4)", ["hand_tank_live.png"], "tap", "ban tay xanh", {"follow": True}),
    ("o do muc tieu dau lau -> cham than xe (vung duoi, #0)", ["beam_skull_noresp.png"], "tap", "o do duoi chan muc tieu", {"follow": True}),
    ("o do muc tieu dau lau cham 7 lan khong an -> thoi (#0)", ["beam_skull_noresp.png"] * 7, "wait", "cho", {"follow": True}),
    ("ban tay + o xanh duoi thung (bong bong che cot sang) -> cham o xanh (#4)", ["hand_crate_green_tile.png"], "tap", "ban tay xanh (cot sang) -> o duoi", {"follow": True}),
    ("ban tay TO (96x71) tren thung hang -> o xanh duoi (#2 2026-11-21)", ["guide_hand_big_crate.png"], "tap", "ban tay xanh", {"follow": True}),
    ("cot sang bi xe che, o do xa chan cot 150px -> cham o do (#2 2026-11-21)", ["guide_beam_jeep_long.png"], "tap", "o do duoi chan muc tieu", {"follow": True}),
    ("bong bong Free tren cong trinh -> cham (hoan thanh mien phi)", ["free_bubble.png"], "tap", "Free", {"follow": True}),
    ("che do xay: dau chan xanh -> bam nut tick", ["build_confirm_tick.png"], "tap", "xac nhan xay (nut tick)"),
    ("bong bong Free nen vang (anh 2) -> cham", ["free_bubble2.png"], "tap", "Free", {"follow": True}),
    ("o do dac (chu nhat) duoi tank dau lau -> cham giua vung rong (#?)", ["beam_skull_tank2.png"], "tap", "o do duoi chan muc tieu", {"follow": True}),
    ("che do xay that #6: dau chan xanh -> nut tick", ["build_confirm_live_i6.png"], "tap", "xac nhan xay (nut tick)", {"follow": True}),
    ("menu cong trinh 2 khung khong V -> het tan thu", ["ch5_menu_a.jpg", "ch5_menu_b.jpg"], "done", "menu cong trinh khong co chu V"),
]


def main():
    v = Vision("templates", 0.82)
    bad = 0
    for case in CASES:
        name, frames, act, why = case[:4]
        init = case[4] if len(case) > 4 else {}
        state, got = dict(init), None
        for fn in frames:
            got = tutorial.decide(v, cv2.imread(F + fn), idle=0, state=state)
        ok = got[0] == act and got[3].startswith(why)
        bad += not ok
        print(f"{'OK  ' if ok else 'FAIL'} {name:48} -> {got[0]} ({int(got[1])},{int(got[2])}) {got[3]}")
    print(f"{len(CASES) - bad}/{len(CASES)} ca dung")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
