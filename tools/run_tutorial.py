"""Chay thu buoc tan thu tren 1 instance dang mo game (khong bat/tat may, khong chay buoc khac).

  python tools/run_tutorial.py --idx 5

Ket qua: logs/live/<ngay_gio>_tutorial_i<idx>/ (NNN.jpg = anh + quyet dinh moi buoc, battle/ = khung lai tran, run.log)
"""
import argparse, datetime, logging, os, sys
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)
import yaml
from bot.device import Device
from bot.vision import Vision
from bot.ctx import Ctx
from bot.modules import tutorial

ap = argparse.ArgumentParser()
ap.add_argument("--idx", type=int, required=True)
ap.add_argument("--max-steps", type=int, default=600)
a = ap.parse_args()

out = os.path.join("logs", "live", datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + f"_tutorial_i{a.idx}")
os.makedirs(os.path.join(out, "battle"))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    handlers=[logging.StreamHandler(), logging.FileHandler(os.path.join(out, "run.log"), encoding="utf-8")])
cfg = yaml.safe_load(open("config.yaml", encoding="utf-8"))
cfg.setdefault("tutorial", {})["trace_dir"] = out
cfg.setdefault("battle", {})["debug_dir"] = os.path.join(out, "battle")
dev = Device(cfg["ldplayer"]["adb"], a.idx)
ctx = Ctx(dev, Vision("templates", cfg.get("match_threshold", 0.82)), cfg)
logging.info("Bat dau tan thu tren instance %d -> %s", a.idx, out)
ok = tutorial.run(ctx, max_steps=a.max_steps)
logging.info("KET THUC: %s", "xong tan thu" if ok else "dung giua chung (xem anh cuoi)")
