"""P13h: doc / sua vms/config/leidian{idx}.config truoc khi bat may (#0 bi LDPlayer tra ve mac dinh 1280x720).

Chi quan tam 3 khoa: do phan giai, DPI, adbDebug. Do phan giai / DPI doi bang `ldconsole modify` (LDConsole);
file nay chi ghi DUNG 1 khoa basicSettings.adbDebug (ldconsole khong co co adb) bang cach thay tai cho trong
van ban goc -> moi byte khac (ke ca cac khoa dinh danh propertySettings.*) giu nguyen. Khong log noi dung file.
"""
import json
import os
import re
import time

RES_KEY = "advancedSettings.resolution"
DPI_KEY = "advancedSettings.resolutionDpi"
ADB_KEY = "basicSettings.adbDebug"
DEFAULT_DISPLAY = (540, 960, 240)       # rong, cao, DPI (ADR-0003)
_ADB_RE = re.compile(rb'("basicSettings\.adbDebug"\s*:\s*)(-?\d+|true|false|null|"[^"\r\n]*")')


def config_path(lc, idx):
    """ldplayer.config_dir (tuy chon), mac dinh <thu muc cua ldconsole.exe>/vms/config."""
    lc = lc or {}
    folder = lc.get("config_dir") or os.path.join(os.path.dirname(str(lc.get("ldconsole") or "")), "vms", "config")
    return os.path.join(folder, f"leidian{int(idx)}.config")


def expected_display(lc):
    """-> (w, h, dpi) tu ldplayer.resolution [w, h] / ldplayer.dpi. Thieu -> mac dinh; sai dang -> ValueError."""
    lc = lc or {}
    res = lc.get("resolution") or DEFAULT_DISPLAY[:2]
    if isinstance(res, str):
        res = re.split(r"[x,]", res.lower())
    if not isinstance(res, (list, tuple)) or len(res) != 2:
        raise ValueError(f"ldplayer.resolution phai la [rong, cao], dang la {res!r}")
    w, h, dpi = int(res[0]), int(res[1]), int(lc.get("dpi") or DEFAULT_DISPLAY[2])
    if min(w, h, dpi) <= 0:
        raise ValueError(f"ldplayer.resolution / dpi phai > 0, dang la {w}x{h} dpi {dpi}")
    return w, h, dpi


def read(path):
    """-> (bytes goc, dict). File dang ghi do / hong -> ValueError."""
    with open(path, "rb") as f:
        raw = f.read()
    data = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("file cau hinh khong phai doi tuong JSON")
    return raw, data


def problems(data, expected):
    """-> {khoa: gia tri cu} cho nhung khoa (trong 3 khoa) khac ky vong. Thieu khoa = sai (gia tri cu None)."""
    w, h, dpi = expected
    out = {}
    res = data.get(RES_KEY)
    if not isinstance(res, dict) or (res.get("width"), res.get("height")) != (w, h):
        out[RES_KEY] = res
    if data.get(DPI_KEY) != dpi:
        out[DPI_KEY] = data.get(DPI_KEY)
    if data.get(ADB_KEY) != 1:
        out[ADB_KEY] = data.get(ADB_KEY)
    return out


def describe(bad):
    """Chuoi 'khoa=gia tri' de ghi log (chi co 3 khoa tren, khong co khoa dinh danh)."""
    return ", ".join(f"{k}={v}" for k, v in bad.items())


def with_adb_debug(raw):
    """Van ban cau hinh voi basicSettings.adbDebug = 1, khong doi gi khac. Khong chac chan -> ValueError."""
    old = json.loads(raw.decode("utf-8-sig"))
    if ADB_KEY in old:
        new = _ADB_RE.sub(rb"\g<1>1", raw)
    else:
        i = raw.index(b"{") + 1
        nl = b"\r\n" if b"\r\n" in raw else b"\n"
        new = raw[:i] + nl + b'    "' + ADB_KEY.encode() + b'": 1' + (b"," if old else b"") + raw[i:]
    if json.loads(new.decode("utf-8-sig")) != {**old, ADB_KEY: 1}:
        raise ValueError("sua adbDebug se lam doi khoa khac - khong ghi")
    return new


def enable_adb_debug(path):
    """Ghi adbDebug = 1 (ghi file tam roi thay the nguyen tu). Chi goi khi may DA TAT."""
    raw, _ = read(path)
    new = with_adb_debug(raw)
    tmp = path + ".aowtmp"
    try:
        with open(tmp, "wb") as f:
            f.write(new)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def wait_quiet(path, quiet_s, max_wait_s=30.0):
    """Cho toi khi file khong bi ghi trong quiet_s giay (LDPlayer vua tat may con dang luu). -> False neu cho
    qua max_wait_s ma file van dang doi."""
    t0 = time.time()
    while True:
        age = time.time() - os.path.getmtime(path)
        if age >= quiet_s:
            return True
        if time.time() - t0 >= max_wait_s:
            return False
        time.sleep(min(1.0, quiet_s - max(age, 0.0)))
