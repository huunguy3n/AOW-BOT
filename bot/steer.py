"""Lai doi quan trong tran kieu chay duong (Mo ruong lanh tho, Tieu diet quan noi loan...):
giu ngon tay tren doi quan suot tran, truot ngang de NHAT buff (bang xanh +N, vu khi phat sang xanh la,
cong +%) va NE nerf (bang do -N, cong -%) va NE vong do nem bom.

Nhan dien theo mau tren khung 540x960 (khong can anh mau):
  buff : khoi xanh duong (bang +N) hoac xanh la sang (vu khi) dac, nam phia truoc doi quan
  nerf : khoi do DAC hinh chu nhat (bang -N). Linh dich mau do co hinh khong deu -> do dac thap, bo qua
  nguy: vong do RONG (hinh elip lon, ruot rong) = vung nem bom
"""
import time, logging, threading, os, re
import cv2, numpy as np

from bot.stream import FrameStream
from bot.touch import Finger

log = logging.getLogger("aow")
AHEAD = (110, 600)        # dai y phia truoc doi quan can xet (nhin xa hon de kip doi lan truoc cong)
SQUAD_Y = 700             # cho dat ngon tay (tren doi quan)
SQUAD_BAND = (560, 820)   # dai y tim doi quan (dong phuc xanh)
X_MIN, X_MAX = 90, 450    # pham vi duoc di chuyen
LANES = np.arange(X_MIN, X_MAX + 1, 15)
MAX_STEP = 110            # (cu, dung cho che do khac)
GAIN = 0.4                # linh di = 0.4 x do keo ngon tay (do 2026-11-18: keo -165 -> -66, +305 -> +136)
MAX_SQUAD_STEP = 70       # px linh toi da moi nhip
FINGER_MIN, FINGER_MAX = 40, 500


def squad_x(img):
    """Vi tri x THAT cua doi quan (dong phuc xanh, cac cham nho) - ngon tay va doi quan co the lech nhau
    (doi quan theo sau ngon tay co do tre, bi chan o mep). -> x hoac None (khong thay)."""
    y0, y1 = SQUAD_BAND
    hsv = cv2.cvtColor(img[y0:y1, 40:500], cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    m = ((H >= 100) & (H <= 125) & (S >= 90) & (V >= 70)).astype(np.uint8)
    n, _, st, cen = cv2.connectedComponentsWithStats(m)
    pts = [(cen[k][0] + 40, st[k][4]) for k in range(1, n) if 4 <= st[k][4] <= 400 and st[k][2] < 40]  # bo khoi lon = cong
    tot = sum(a for _, a in pts)
    if tot < 8:
        return None
    return int(sum(x * a for x, a in pts) / tot)


def _blobs(mask, min_area):
    n, _, st, cen = cv2.connectedComponentsWithStats(mask.astype(np.uint8))
    out = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if a >= min_area:
            out.append((x, y, w, h, a, a / float(w * h)))
    return out


def _barricade(p):
    """Hang rao gai sat: ong kim loai NGANG (co hang canh ngang dai >= 70% be rong), khong lan mau do
    (dam linh / mech dich xam co mau do + so sat thuong -> loai). Do tren 3401 khung logs/steer 2026-11-21."""
    hsv = cv2.cvtColor(p, cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    if (((H <= 10) | (H >= 165)) & (S >= 120) & (V >= 90)).mean() >= 0.03:
        return False
    if ((H >= 95) & (H <= 125) & (S >= 90) & (V >= 80)).mean() >= 0.05:   # mech / xe xanh
        return False
    gy = np.abs(cv2.Sobel(cv2.cvtColor(p, cv2.COLOR_BGR2GRAY).astype(np.float32), cv2.CV_32F, 0, 1, ksize=3))
    return float((gy > 60).mean(axis=1).max()) >= 0.7


def detect(img):
    """-> dict(buff=[(cx, cy, w)], nerf=[...], danger=[...], enemy=[...])"""
    y0, y1 = AHEAD
    roi = img[y0:y1]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    blue = (H >= 95) & (H <= 118) & (S >= 130) & (V >= 150)
    green = (H >= 45) & (H <= 85) & (S >= 120) & (V >= 170)
    red = ((H <= 7) | (H >= 172)) & (S >= 140) & (V >= 110)
    k = np.ones((5, 5), np.uint8)
    out = {"buff": [], "nerf": [], "danger": [], "enemy": [], "block": [], "target": []}
    for m in (blue, green):
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, k)
        for x, y, w, h, a, fill in _blobs(m, 900):
            if fill >= 0.45 and w >= 30 and h >= 25:
                # 2-3 cong xanh dat sat nhau bi dinh thanh 1 khoi -> tam roi vao KHE GIUA (di lot giua, mat ca 2).
                # Cong gan vuong (w/h ~1.1-1.3) -> khoi qua dai thi tach deu thanh tung cong.
                parts = max(1, int(round(w / (h * 1.2)))) if w > 1.7 * h else 1
                for j in range(parts):
                    out["buff"].append((x + int(w * (2 * j + 1) / (2 * parts)), y0 + y + h // 2, w // parts))
    # P9-10 (anh chu du an runner_ne_vat_can: "+5" linh tren MUI TEN XANH LA, mau nhat H 38-75 S 90-180): khoi mui ten
    # rong ~85x60, do dac thap (0.3-0.4, hinh mui ten) -> loc rieng, khong trung buff da co.
    ga = cv2.morphologyEx(((H >= 38) & (H <= 75) & (S >= 90) & (V >= 140)).astype(np.uint8), cv2.MORPH_CLOSE, k)
    for x, y, w, h, a, fill in _blobs(ga, 1500):
        cx, cy = x + w // 2, y0 + y + h // 2
        if (0.3 <= fill < 0.45 and 50 <= w <= 140 and 40 <= h <= 120
                and all(abs(cx - a2) >= 50 or abs(cy - b2) >= 50 for a2, b2, _ in out["buff"])):
            out["buff"].append((cx, cy, w))
    gm = cv2.morphologyEx(green.astype(np.uint8), cv2.MORPH_CLOSE, k)
    rm = cv2.morphologyEx(red.astype(np.uint8), cv2.MORPH_CLOSE, k)
    for x, y, w, h, a, fill in _blobs(rm, 700):
        if w >= 140 and h >= 50 and fill < 0.25:        # vong tron rong lon -> vung nem bom
            out["danger"].append((x + w // 2, y0 + y + h // 2, w))
        elif fill >= 0.55 and 40 <= w <= 200 and 30 <= h <= 140 and 0.8 <= w / h <= 3.0:
            # bang do co anh sang xanh la ngay phia tren (icon linh) = THUNG CUU TRO (ban vo duoc +linh) -> buff
            above = gm[max(0, y - 70):y + 5, x:x + w]
            if above.size and above.mean() > 0.08:
                out["buff"].append((x + w // 2, y0 + y + h // 2, w))
            else:
                out["nerf"].append((x + w // 2, y0 + y + h // 2, w))  # bang do -N
    # cong nhat / trong mo (anh chu du an 2026-11-21: "-10%" do S~140, "+5" xanh S~85) -> loc rieng, bo trung
    def _new(lst, cx, cy):
        return not any(abs(cx - a) < 60 and abs(cy - b) < 50 for a, b, _ in lst)
    # P13d-2 (anh runner_khong_dieu_khien: 3 VONG TIM/hong phat sang tren duong + bang "+5%"): vong elip hong H 140-172,
    # ruot rong (do dac 0.2-0.65), rong 80-160 x cao 45-95 -> nhat nhu buff (bot truoc day khong nhan ra vong tim)
    pm = cv2.morphologyEx(((H >= 140) & (H <= 172) & (S >= 40) & (V >= 215)).astype(np.uint8), cv2.MORPH_CLOSE, k)
    for x, y, w, h, a_, fill in _blobs(pm, 1500):
        cx, cy = x + w // 2, y0 + y + h // 2
        if 80 <= w <= 160 and 45 <= h <= 95 and 1.3 <= w / h <= 2.0 and 0.2 <= fill <= 0.65 and _new(out["buff"], cx, cy):
            out["buff"].append((cx, cy, w))
    for key, m in (("nerf", ((H <= 10) | (H >= 160)) & (S >= 80) & (V >= 170)),
                   ("buff", (H >= 95) & (H <= 118) & (S >= 55) & (V >= 170))):
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))   # bo vet dan / duong manh
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        for x, y, w, h, a, fill in _blobs(m, 2500):
            cx, cy = x + w // 2, y0 + y + h // 2
            if fill >= 0.45 and 80 <= w <= 200 and 40 <= h <= 120 and 1.0 <= w / h <= 3.2 and _new(out[key], cx, cy):
                out[key].append((cx, cy, w))
    # Chu du an 2026-11-21: bang do CO SO = vat the can TAN CONG (ban vao so tang len, >0 thanh co loi) ->
    # con XA (cy < FAR_Y) thi vao lan de ban; toi GAN ma van do thi NE (giu trong nerf, choose() chi phat khi gan)
    out["target"] = [(cx, cy, w) for cx, cy, w in out["nerf"] if cy < FAR_Y]
    # HANG RAO GAI SAT (xam kim loai, nhieu canh, dai ngang) -> chuong ngai bat buoc NE (khong ban vo duoc)
    g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    ed = cv2.blur((cv2.Canny(g, 60, 160) > 0).astype(np.float32), (25, 25))
    mm = cv2.morphologyEx(((S < 45) & (ed > 0.12)).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    for x, y, w, h, a, fill in _blobs(mm, 2500):
        if fill >= 0.5 and 40 <= h <= 100 and 70 <= w <= 240 and w / h >= 1.4 and y0 + y + h < SQUAD_BAND[0]:
            if _barricade(roi[y:y + h, x:x + w]):
                out["block"].append((x + w // 2, y0 + y + h // 2, w))
    # linh dich: khoi do NHO, hinh khong deu (khac bang do -N dac hinh chu nhat) -> muc tieu de ban
    nerf_boxes = [(cx - w // 2 - 10, cx + w // 2 + 10, cy) for cx, cy, w in out["nerf"]]
    for x, y, w, h, a, fill in _blobs(rm, 40):
        cx, cy = x + w // 2, y0 + y + h // 2
        if a > 1500 or (fill >= 0.55 and w >= 40):          # khoi lon / dac = bang, vong bom -> da xu ly o tren
            continue
        if any(l <= cx <= r and abs(cy - by) < 70 for l, r, by in nerf_boxes):
            continue
        out["enemy"].append((cx, cy, max(w, 20)))
    # vet do trong suot doc theo lan duong (xe lao toi) -> nguy hiem ca cot
    b, g, r = [roi[..., i].astype(int) for i in range(3)]
    tint = ((r - g > 25) & (r - b > 30) & (S >= 50) & (S < 170)).astype(np.uint8)
    col = tint.mean(axis=0)                       # ti le diem do theo tung cot
    hot = col > 0.3
    if hot.any():
        xs = np.where(hot)[0]
        groups = np.split(xs, np.where(np.diff(xs) > 6)[0] + 1)
        for gx in groups:
            if 40 <= len(gx) <= 200:
                out["danger"].append((int(gx.mean()), (y0 + y1) // 2, int(len(gx) + 30)))
    return out


FAR_Y = 330  # bang do co so o tren muc nay = con xa -> ban; duoi = gan -> ne
VY_S = 45    # px/giay: vat the lao xuong (do: 18 px/khung x 2.5 khung/giay, tran tan thu)
VX_S = 120   # px/giay: linh di ngang khi keo (MAX_SQUAD_STEP 70 px / nhip ~0.5 s, lay than trong)


STALL_S = 1.5            # P13d-2: khong co khung moi qua N giay -> luong anh dung hinh -> khoi dong lai
MAX_STREAM_RESTARTS = 4


class DragWatch:
    """P13d-2 (anh runner_khong_dieu_khien: bot keo ma doi quan dung yen): lenh keo vua gui (cmd_dx) ma sau do x doi quan
    khong doi theo huong do >= min_move px, `need` lan lien tiep -> keo khong co hieu luc (ngon tay mat / id cham cu) ->
    nguoi goi nhac tay roi dat lai. Ham thuan: x doi quan truyen vao, bo qua khi doi quan sat mep (bi chan that)."""

    def __init__(self, need=4, min_cmd=20, min_move=6, edge=(60, 480)):
        self.need, self.min_cmd, self.min_move, self.edge = need, min_cmd, min_move, edge
        self.prev_sx, self.prev_cmd, self.streak = None, 0.0, 0

    def update(self, sx, cmd_dx):
        """sx: x doi quan do duoc o khung nay (None neu khong thay); cmd_dx: do keo se gui sau khung nay (0 = khong keo).
        -> True khi can dat lai ngon tay."""
        stuck = False
        if sx is not None and self.prev_sx is not None and abs(self.prev_cmd) >= self.min_cmd:
            moved = (sx - self.prev_sx) * (1 if self.prev_cmd > 0 else -1)
            at_edge = (sx <= self.edge[0] and self.prev_cmd < 0) or (sx >= self.edge[1] and self.prev_cmd > 0)
            if moved >= self.min_move or at_edge:
                self.streak = 0
            else:
                self.streak += 1
                if self.streak >= self.need:
                    stuck, self.streak = True, 0
        if sx is not None:
            self.prev_sx = sx
            self.prev_cmd = cmd_dx
        elif cmd_dx:
            self.prev_cmd = cmd_dx
        return stuck


def reachable(cx, cy, w, cur_x):
    """Buff con kip toi khong: khoang cach ngang <= quang duong doi quan di duoc truoc khi vat toi."""
    t = max(0.3, (SQUAD_Y - cy) / VY_S)
    return abs(cx - cur_x) <= VX_S * t + w / 2 + 15


# ---------- P7-8 (chu du an 2026-11-24, anh minigame_runner_gates_minus_plus): cong do "-X" ban du se lat "+Y" ----------
GATE_MIN_W = 60          # bang do co so (cong) - nho hon la linh dich / dan
GATE_SAFETY = 0.8        # chi lao vao cong khi du doan con du 20 % thoi gian (ban cham hon uoc luong -> van kip)
GATE_DEFAULT_RATE = 1.0  # P13-10 (chu du an t72u: bot chua dung buff do): cong -2 xa -> ban 1/giay toi khi duong roi lao vao
GATE_DEFAULT_MAX = 3    # ... ap dung cho cong -1..-3 (cong lon hon van phai do toc do that, nhu P7-8)
GATE_OCR_MAX = 2         # doc so toi da 2 cong / khung (moi lan OCR ~0.1-0.2 s)
GATE_RX = re.compile(r"([+-]?)\s*(\d{1,4})")


def parse_gate(txt):
    """Chu OCR tren bang cong -> so co dau ('-5' -> -5, '+3' -> 3). Bang do mac dinh am khi mat dau '-'."""
    m = GATE_RX.search(txt or "")
    if not m:
        return None
    v = int(m.group(2))
    return v if m.group(1) == "+" else -v


def gate_value(img, cx, cy, w):
    """Doc so tren bang cong do (giua bang, chu trang)."""
    from bot import ocr
    h = max(20, int(w * 0.45))
    x0, y0 = max(0, cx - w // 2 + 6), max(0, cy - h // 2)
    roi = (x0, y0, min(img.shape[1] - x0, w - 12), min(img.shape[0] - y0, h))
    if roi[2] < 10 or roi[3] < 10:
        return None
    return parse_gate(ocr.text(img, roi, "+-0123456789", bright=170))


class GateTrack:
    """Theo doi gia tri tung cong do theo lan (x // 60) qua cac khung -> toc do tang (do doi quan ban). Ham thuan:
    thoi gian truyen vao."""

    def __init__(self, keep_s=6.0):
        self.keep_s, self.hist = keep_s, {}

    def update(self, cx, value, t):
        k = int(cx) // 60
        h = [(tt, vv) for tt, vv in self.hist.get(k, []) if t - tt <= self.keep_s] + [(t, value)]
        self.hist[k] = h
        return self.rate(cx)

    def rate(self, cx):
        """Gia tri tang / giay (>0 = dang bi ban, tien ve 0). Chua du 2 lan doc -> None."""
        h = self.hist.get(int(cx) // 60, [])
        if len(h) < 2 or h[-1][0] - h[0][0] < 0.3:
            return None
        return (h[-1][1] - h[0][1]) / (h[-1][0] - h[0][0])


def flip_ok(value, rate, cy, vy=VY_S, safety=GATE_SAFETY):
    """Cong am `value` (vd -5) dang tang `rate`/giay, cach doi quan (SQUAD_Y - cy) px, roi xuong vy px/giay -> kip lat
    thanh "+" truoc khi cham doi quan? Duong / chua doc duoc toc do -> False (giu luat cu: xa thi ban, gan thi ne)."""
    if value is None:
        return False
    if rate is None and -GATE_DEFAULT_MAX <= value <= 0:     # chi cong NHO (rui ro thap) khi chua do duoc toc do
        rate = GATE_DEFAULT_RATE      # P13-10: chua do duoc toc do (cong vua hien) -> gia dinh toc do ban mac dinh
    if rate is None or rate <= 0:
        return value > 0
    t = max(0.0, (SQUAD_Y - cy) / vy)
    return value + rate * t * safety >= 1


def classify_gates(det, img, track, t, read=gate_value, max_ocr=GATE_OCR_MAX):
    """Cong do co so (nerf rong >= GATE_MIN_W): doc so, cap nhat toc do; du doan lat kip -> det['flip'] (lao vao ban,
    an "+"), khong thi giu trong nerf (gan thi ne). Sua det tai cho, tra det."""
    flip, keep, n = [], [], 0
    for o in sorted(det["nerf"], key=lambda o: -o[1]):        # cong gan doi quan truoc
        cx, cy, w = o
        if w < GATE_MIN_W or n >= max_ocr:
            keep.append(o)
            continue
        n += 1
        v = read(img, cx, cy, w)
        r = track.update(cx, v, t) if v is not None else track.rate(cx)
        (flip if flip_ok(v, r, cy) else keep).append(o)
    det["nerf"], det["flip"] = keep, flip
    det["target"] = [o for o in det.get("target", []) if o not in flip]
    return det


def choose(det, cur_x):
    """Chon lan theo uu tien:
      1. co buff con KIP toi -> nhat buff
      2. khong co buff kip toi -> TAN CONG: vao lan co nhieu linh dich nhat (doi quan ban thang phia truoc)
      luon tranh di XUYEN bang do -N; vung nem bom chi tru nhe (tan cong uu tien hon ne)."""
    def layer(objs, only_reachable=False):
        sc = np.zeros(len(LANES))
        for cx, cy, w in objs:
            if cy > SQUAD_Y - 30:                    # da di qua doi quan -> khong con lien quan
                continue
            if only_reachable and not reachable(cx, cy, w, cur_x):
                continue
            near = 0.4 + 0.6 * (cy - AHEAD[0]) / (AHEAD[1] - AHEAD[0])   # cang gan doi quan cang quan trong
            sigma = w / 2 + 35
            sc += near * np.exp(-((LANES - cx) ** 2) / (2 * sigma ** 2))
        return sc
    buff = layer(det["buff"] + det.get("flip", []), only_reachable=True)   # P7-8: cong se lat "+" = buff
    enemy = layer(det.get("enemy", []) + det.get("target", []))
    if enemy.max() > 0:
        enemy = enemy / enemy.max()                  # chuan hoa: dam dong dich nhat = 1.0
    attack_w = 0.25 if buff.max() > 0.05 else 1.0   # co buff kip -> buff truoc; khong -> tan cong
    near_nerf = [o for o in det["nerf"] if o[1] >= FAR_Y]            # bang do xa = muc tieu ban, gan = ne
    score = (buff + attack_w * enemy - 1.6 * layer(near_nerf) - 1.0 * layer(det["danger"])
             - 2.5 * layer(det.get("block", [])))                     # hang rao gai: ne manh nhat
    score -= 0.002 * np.abs(LANES - cur_x)   # uu tien it di chuyen khi khong co gi
    return int(LANES[int(np.argmax(score))]), float(score.max())


def in_battle(v, img):
    if v.find(img, "campaign/btn_fight") or v.find(img, "common/btn_to_world") or v.find(img, "common/btn_to_city"):
        return False
    return bool(v.find(img, "campaign/battle_hud", th=0.9))


ENTER_WAIT_S = 25        # P7-9: tran chien dich #1 tai lau hon 10 s (live #1 2026-11-24: "Khong xac nhan duoc dang trong tran")


def campaign_battle(v, img):
    """P7-9: nhan tran chien dich rong hon in_battle (live #1: tran thua 79,7M/83,1M ma bot KHONG lai - battle_hud cu
    khong khop -> khong dat ngon tay, khong ne, khong an buff). Them: bien the campaign/battle_hud_* (chu du an cat) +
    dau hieu tran chay duong tan thu (battle_top/flag). -> True | False | None (chac chan khong phai tran)."""
    if v.find(img, "campaign/btn_fight") or v.find(img, "common/btn_to_world") or v.find(img, "common/btn_to_city"):
        return False
    if v.find(img, "campaign/res_win") or v.find(img, "campaign/res_lose"):
        return None
    if v.find(img, "campaign/battle_hud", th=0.85):
        return True
    for n in v.list("campaign/battle_hud_"):
        if v.find(img, n, th=0.85):
            return True
    from bot.modules import tutorial
    return bool(tutorial.is_battle(v, img))


def template_buffs(v, img, names=None, th=0.8):
    """P7-9: buff cat bang anh mau (templates/steer/buff_*.png: linh "+N" xanh, dan "+%" xanh la...) trong dai phia
    truoc doi quan -> [(cx, cy, w)] bo sung cho nhan dien theo mau (hieu ung lua/khoi che mau)."""
    out = []
    y0, y1 = AHEAD
    for n in (names if names is not None else v.list("steer/buff_")):
        for x, y, _ in v.find_all(img, n, th=th, roi=(0, y0, img.shape[1], y1 - y0)):
            out.append((int(x), int(y), 60))
    return out


# P9-10 (chu du an 2026-11-24, runner_ne_vat_can.png: live #1 thua chien dich vi khong ne con lan gai): CON LAN GAI
# (truc kim loai + 5 dia rang cua, ~160x80) - lua / khoi che mat mau nen nhan bang ANH MAU, them vao det['block'] (ne manh
# nhat, -2.5). Mau cat lech trai con lan -> dx = tam con lan - tam mau.
#   steer/block_roller      : logs/steer/1795203553_024.jpg (540x960 cua bot) 17,415,150,492 - con lan sach
#   steer/block_roller_fire : anh chu du an (dien thoai 541x956 -> 540x960) 142,388,235,465 - nua trai, nua phai chay
# Khop >= 0.62 tren 8817 khung logs/steer: deu la con lan that (kiem bang mat 6 khung), nen p99 ~0.59.
BLOCK_TH = 0.62
ROLLER_W = 170
BLOCK_DX = {"steer/block_roller": 14, "steer/block_roller_fire": 28}


def template_blocks(v, img, names=None, th=BLOCK_TH):
    """Vat can theo anh mau (templates/steer/block_*.png) trong dai phia truoc doi quan -> [(cx, cy, w)]."""
    out = []
    y0, y1 = AHEAD
    for n in (names if names is not None else v.list("steer/block_")):
        for x, y, _ in v.find_all(img, n, th=th, roi=(0, y0, img.shape[1], y1 - y0), min_dist=60):
            out.append((int(x) + BLOCK_DX.get(n, 0), int(y), ROLLER_W))
    return out


def merge_blocks(det, extra, dist=80):
    """Them vat can tu anh mau, bo trung (gan nhau < dist px) voi vat can theo mau / mau khac."""
    for cx, cy, w in extra:
        if all(abs(cx - a) >= dist or abs(cy - b) >= dist for a, b, _ in det["block"]):
            det["block"].append((cx, cy, w))
    return det


def merge_buffs(det, extra, dist=50):
    """Them buff tu anh mau, bo trung voi buff theo mau (gan nhau < dist px)."""
    for cx, cy, w in extra:
        if all(abs(cx - a) >= dist or abs(cy - b) >= dist for a, b, _ in det["buff"]):
            det["buff"].append((cx, cy, w))
    return det


def save_enter_fail(img, root="logs/inv/steer_no_battle", keep=30):
    """Khong xac nhan duoc dang trong tran -> luu khung cuoi (toi da `keep` anh) de chu du an cat anh mau HUD tran."""
    try:
        if img is None:
            return None
        os.makedirs(root, exist_ok=True)
        if len(os.listdir(root)) >= keep:
            return None
        path = os.path.join(root, time.strftime("%Y%m%d-%H%M%S") + ".png")
        cv2.imwrite(path, img)
        return path
    except Exception:
        return None


RESULT_TPLS = ["campaign/btn_done", "campaign/btn_done_lose", "campaign/btn_retry", "campaign/btn_continue"]


# 2 may chay song song (2026-11-20): luc 1 may dang lai quan, luong may kia tam dung thao tac (ctx.shot/tap goi
# wait_battle) -> CPU host danh cho tran (khung hinh tran rot tu 1.6 xuong 1.0/s khi 2 may cung lam viec).
_battle_owner = None
active_serials = set()   # may dang lai quan bang sendevent -> bot/human.py bo qua su kien cham tren may nay
_battle_cv = threading.Condition()


def wait_battle(max_wait=150):
    """Luong KHAC dang lai quan -> cho toi khi tran xong (toi da max_wait giay)."""
    me = threading.get_ident()
    with _battle_cv:
        t0 = time.time()
        while _battle_owner not in (None, me) and time.time() - t0 < max_wait:
            _battle_cv.wait(1.0)


def result_of(vision, img):
    """Man ket qua tran -> 'win' | 'lose'. Man thang kieu moi (#1 2026-11-21: huy hieu kiem vang, "So ke dich tieu
    diet", nut "Dong" giua, co hang "Nhan" thuong) KHONG khop res_win -> truoc day bi ghi 'lose'.
    Thu tu: res_lose -> thua; res_win -> thang; con lai: nut "Dong" (btn_done) khop hon nut cua man thua -> thang."""
    if vision.find(img, "campaign/res_lose"):
        return "lose"
    if vision.find(img, "campaign/res_win") or vision.find(img, "campaign/btn_continue"):
        return "win"          # P13-10: man 'Thang loi' co nut 'Tiep tuc Chien dich'
    d = vision.best(img, "campaign/btn_done")
    dl = vision.best(img, "campaign/btn_done_lose")
    return "win" if d and d[2] >= 0.82 and (not dl or d[2] > dl[2]) else "lose"


def run_battle(adb, serial, vision, timeout=150, debug_dir=None, is_battle=None, enter_wait=10, scale=1.0):
    global _battle_owner
    with _battle_cv:
        while _battle_owner not in (None, threading.get_ident()):
            _battle_cv.wait(1.0)        # may kia cung dang trong tran -> lan luot
        _battle_owner = threading.get_ident()
    try:
        if debug_dir:
            os.makedirs(debug_dir, exist_ok=True)
        active_serials.add(serial)
        return _run_battle(adb, serial, vision, timeout, debug_dir, is_battle, enter_wait, scale)
    finally:
        active_serials.discard(serial)
        with _battle_cv:
            _battle_owner = None
            _battle_cv.notify_all()


def _run_battle(adb, serial, vision, timeout=150, debug_dir=None, is_battle=None, enter_wait=10, scale=1.0):
    """Da bam 'Chien dau'. Lai den khi hien man ket qua. -> 'win' | 'lose' | 'error'
    is_battle(vision, img) -> bool: bo nhan dien tran rieng (vd tran tan thu khong co battle_hud)."""
    in_battle_fn = is_battle or in_battle
    s = FrameStream(adb, serial)
    fg = Finger(adb, serial, scale=scale)
    x = 270
    miss = 0
    gates = GateTrack()
    watch = DragWatch()
    stalls, reissued = 0, 0
    t0, last, i = time.time(), 0, 0
    result = "error"
    try:
        # cho vao tran that su (KHONG BAO GIO dat ngon tay khi chua chac dang trong tran)
        img = None
        while time.time() - t0 < enter_wait:
            img, last = s.latest(last)
            if img is not None and in_battle_fn(vision, img):
                break
        else:
            log.warning("Khong xac nhan duoc dang trong tran sau %ss - khong lai (anh %s)", enter_wait, save_enter_fail(img))
            return "error"
        tbuffs = vision.list("steer/buff_")       # P7-9: buff theo anh mau (neu chu du an da cat)
        tblocks = vision.list("steer/block_")     # P9-10: con lan gai theo anh mau
        time.sleep(0.8)          # cho het hieu ung vao tran / dem nguoc: cham dat xuong luc nay game bo qua
        fg.down(270, SQUAD_Y)
        est = 270.0              # uoc luong x cua doi quan (cong don theo do keo, hieu chinh bang anh khi hop ly)
        tele = open(f"{debug_dir}/{int(t0)}_trace.csv", "w") if debug_dir else None
        if tele:
            tele.write("i,t,finger,squad_raw,squad_est,target,score,buff,buff_reach,nerf,enemy,danger,recenter\n")
        while time.time() - t0 < timeout:
            img, t_new = s.latest(last)
            if t_new <= last:      # P13d-2: khong co khung moi trong timeout -> luong anh dung hinh
                stalls += 1
                if stalls >= 2 and time.time() - last > STALL_S:
                    if s.restarts >= MAX_STREAM_RESTARTS:
                        log.warning("Luong anh dung hinh %d lan - bo lai", s.restarts)
                        fg.up()
                        result = "error"
                        break
                    log.warning("Luong anh dung hinh %.1fs - khoi dong lai luong (lan %d)", time.time() - last,
                                s.restarts + 1)
                    s.restart()
                    stalls = 0
                if img is None:
                    continue
            else:
                stalls = 0
            last = t_new
            if any(vision.find(img, n) for n in RESULT_TPLS):
                result = result_of(vision, img)
                break
            if is_battle:
                ib = in_battle_fn(vision, img)
                miss = 0 if ib else (99 if ib is None else miss + 1)   # None = chac chan da roi tran
                if miss >= 4:      # 4 khung lien tiep khong con dau hieu tran (banner CANH BAO co the che 1-2 khung)
                    fg.up()
                    result = "left"
                    break
            elif not in_battle_fn(vision, img) and not vision.find(img, "campaign/battle_hud", th=0.7):
                fg.up()  # roi khoi tran (man khac) -> nhac tay ngay
            det = detect(img)
            if tbuffs:
                merge_buffs(det, template_buffs(vision, img, tbuffs))
            if tblocks:
                merge_blocks(det, template_blocks(vision, img, tblocks))
            if det["nerf"]:
                classify_gates(det, img, gates, time.time() - t0)   # P7-8: cong do lat duoc -> lao vao
            sx = squad_x(img)
            if sx is not None and abs(sx - est) < 70:   # bo do anh nhieu (bat nham cong/thung xanh) -> chi tin khi gan
                est = 0.6 * est + 0.4 * sx
            cur = int(est)
            tx, sc = choose(det, cur)
            # Linh di theo DO LECH keo tuong doi, he so GAIN (~0.4), chi khi keo cham theo thoi gian (drag_by).
            d = max(-MAX_SQUAD_STEP, min(MAX_SQUAD_STEP, tx - est))
            recenter = 0
            if fg.down_ and watch.update(sx, d / GAIN if abs(d) >= 8 else 0.0):
                log.warning("Keo khong co hieu luc (doi quan dung yen x=%s) - dat lai ngon tay (lan %d)", sx, reissued + 1)
                fg.up()
                time.sleep(0.05)
                fg.down(270, SQUAD_Y)
                reissued += 1
                recenter = 2
            if fg.down_ and abs(d) >= 8:
                fdx = d / GAIN
                if not (FINGER_MIN <= fg.x + fdx <= FINGER_MAX):   # het cho keo -> nhac tay, dat lai giua (nhu touchpad)
                    fg.up()
                    time.sleep(0.03)
                    fg.down(270, SQUAD_Y)
                    recenter = 1
                fg.drag_by(fdx)
                est = max(40.0, min(500.0, est + d))
            x = int(fg.x) if fg.x is not None else 270
            if tele:
                tele.write(f"{i},{time.time() - t0:.2f},{x},{sx if sx is not None else ''},{cur},{tx},{sc:.2f},"
                           f"{len(det['buff'])},{sum(reachable(*b, cur) for b in det['buff'])},{len(det['nerf'])},"
                           f"{len(det.get('enemy', []))},{len(det['danger'])},{recenter}\n")
            if debug_dir:
                dbg = img.copy()
                for k, col in (("buff", (255, 200, 0)), ("nerf", (0, 0, 255)), ("danger", (0, 0, 180))):
                    for cx, cy, w in det[k]:
                        cv2.circle(dbg, (cx, cy), max(12, w // 2), col, 3)
                cv2.line(dbg, (x, 640), (x, 760), (0, 255, 0), 4)          # xanh la: ngon tay
                cv2.line(dbg, (cur, 770), (cur, 830), (0, 255, 255), 4)    # vang: uoc luong vi tri doi quan
                for cx, cy, w in det.get("enemy", []):
                    cv2.circle(dbg, (cx, cy), 6, (0, 140, 255), 2)        # cam: linh dich
                cv2.line(dbg, (tx, 640), (tx, 700), (255, 0, 255), 2)       # tim: dich
                cv2.imwrite(f"{debug_dir}/{int(t0)}_{i:03d}.jpg", dbg, [cv2.IMWRITE_JPEG_QUALITY, 70])
            i += 1
    finally:
        fg.close()
        s.close()
        if debug_dir and "tele" in locals() and tele:
            tele.close()
    log.info("Tran lai: %s sau %.0fs (%d khung, %.1f khung/s luong anh, %d lan khoi dong lai luong, %d lan dat lai tay)",
             result, time.time() - t0, i, s.fps(), s.restarts, reissued)
    return result
