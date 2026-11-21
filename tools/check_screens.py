"""Hoi quy nhan dien man (bot/screens.py): moi anh trong tests/fixtures/screens/<nhan>/*.png phai ra dung <nhan>.

  python tools/check_screens.py          # in ket qua, exit 1 neu sai
Them ca moi: chep anh (540x960) vao thu muc nhan tuong ung (city, world, popup, panel, panel_key, exit_dialog,
reward, dialog, loading, unknown).
"""
import glob, os, sys, time
import cv2

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from bot.vision import Vision  # noqa: E402
from bot.screens import identify  # noqa: E402


def main():
    v = Vision(os.path.join(BASE, "templates"), 0.82)
    bad = n = 0
    t0 = time.time()
    for f in sorted(glob.glob(os.path.join(BASE, "tests", "fixtures", "screens", "*", "*.png"))):
        want = os.path.basename(os.path.dirname(f))
        got, _ = identify(cv2.imread(f), v)
        n += 1
        if got != want:
            bad += 1
            print(f"SAI  {os.path.relpath(f, BASE)}: mong {want}, ra {got}")
    print(f"{n - bad}/{n} dung, {(time.time() - t0) / max(n, 1) * 1000:.0f} ms/anh")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
