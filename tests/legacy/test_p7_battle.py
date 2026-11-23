"""P7-9 (chu du an 2026-11-24, live #1: thua chien dich 79,7M/83,1M - bot KHONG ne, KHONG an buff vi khong xac nhan
duoc dang trong tran sau 10 s -> khong dat ngon tay). Nhan tran rong hon, cho lau hon, buff theo anh mau, luu anh."""
import inspect
import os

import numpy as np

from bot import steer
from bot.modules import campaign


class V:
    def __init__(self, seen=(), lists=None, alls=None):
        self.seen, self.lists, self.alls = set(seen), lists or {}, alls or {}

    def find(self, img, name, th=None, **k):
        return (40, 60, 0.9) if name in self.seen else None

    def list(self, prefix):
        return self.lists.get(prefix, [])

    def find_all(self, img, name, **k):
        return self.alls.get(name, [])


def test_campaign_battle_variants():
    assert steer.campaign_battle(V({"campaign/battle_hud"}), None) is True
    assert steer.campaign_battle(V({"campaign/battle_hud_2"}, {"campaign/battle_hud_": ["campaign/battle_hud_2"]}),
                                 None) is True
    assert steer.campaign_battle(V({"tutorial/battle_flag"}), None) is True     # dau hieu tran chay duong
    assert steer.campaign_battle(V({"campaign/btn_fight", "campaign/battle_hud"}), None) is False
    assert steer.campaign_battle(V({"campaign/res_lose"}), None) is None
    assert steer.campaign_battle(V(), None) is False


def test_campaign_passes_wider_detector_and_longer_wait():
    src = inspect.getsource(campaign.battle)
    assert "is_battle=steer.campaign_battle" in src and "enter_wait" in src
    assert steer.ENTER_WAIT_S > 10
    assert "enter_wait" in inspect.signature(steer.run_battle).parameters


def test_template_buffs_merge():
    img = np.zeros((960, 540, 3), np.uint8)
    v = V(alls={"steer/buff_ammo": [(300, 280, 0.9)], "steer/buff_soldiers": [(110, 460, 0.85)]})
    extra = steer.template_buffs(v, img, ["steer/buff_ammo", "steer/buff_soldiers"])
    det = {"buff": [(305, 285, 80)]}
    steer.merge_buffs(det, extra)
    assert det["buff"] == [(305, 285, 80), (110, 460, 60)]          # trung voi buff theo mau -> bo
    x, _ = steer.choose({"buff": [(110, 460, 60)], "nerf": [], "danger": []}, 200)
    assert abs(x - 110) <= 30                                        # lai toi buff


def test_save_enter_fail(tmp_path):
    root = str(tmp_path / "inv")
    p = steer.save_enter_fail(np.zeros((960, 540, 3), np.uint8), root, keep=1)
    assert p and os.path.exists(p)
    assert steer.save_enter_fail(np.zeros((960, 540, 3), np.uint8), root, keep=1) is None   # du anh -> khong luu them
    assert steer.save_enter_fail(None, root) is None
