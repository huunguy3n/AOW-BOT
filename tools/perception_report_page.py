"""Sinh <out>/index.html tu <out>/data.json (do perception_report.py tao). Khong dung thu vien ngoai ngoai Google Fonts."""
import html
import json
import os
import shutil
import sys
from collections import Counter

out = sys.argv[1]
data = json.load(open(os.path.join(out, "data.json"), encoding="utf8"))
before = json.load(open(os.path.join(out, "before.json"), encoding="utf8")) if os.path.exists(os.path.join(out, "before.json")) else []

n = len(data)
scenes = Counter(r["scene"] or "?" for r in data)
dots_new = sum(r["reddots"] for r in data)
dots_old = sum(r["reddots_legacy"] for r in data)
conf_frames = sum(1 for r in data if r["confirmed"])
ms_new = sorted(r["ms"] for r in data)
ms_old = sorted(r["ms_legacy"] for r in data)
p50 = lambda a: a[len(a) // 2]  # noqa: E731

# lech so voi ban cu: lop ban cu thay ma moi khong CONFIRMED, va nguoc lai
only_old, only_new = Counter(), Counter()
for r in data:
    old, new = set(r["legacy_found"]), set(r["confirmed"])
    for c in old - new:
        only_old[c] += 1
    for c in new - old:
        only_new[c] += 1

SCENE_VI = {"city": "Thành phố", "world": "Bản đồ", "panel": "Bảng/menu", "popup": "Popup", "reward": "Nhận thưởng",
            "loading": "Đang tải", "unknown": "Không rõ", "dialog": "Hội thoại", "exit_dialog": "Thoát game", "?": "Không rõ"}


def esc(s):
    return html.escape(str(s), quote=True)


cards = []
for r in data:
    conf = ", ".join(f"{esc(k)} <i>{v:.2f}</i>" for k, v in r["confirmed"].items()) or "—"
    unc = ", ".join(f"{esc(k)} <i>{v:.2f}</i>" for k, v in r["uncertain"].items()) or "—"
    bot = "".join(f"<li>{esc(x[:150])}</li>" for x in r["bot"]) or "<li class=dim>(không có dòng log mới)</li>"
    miss = sorted(set(r["legacy_found"]) - set(r["confirmed"]))
    extra = sorted(set(r["confirmed"]) - set(r["legacy_found"]))
    diff = ""
    if miss:
        diff += f"<p class=warn>Bản cũ thấy, bản mới không xác nhận: {esc(', '.join(miss))}</p>"
    if extra:
        diff += f"<p class=warn>Bản mới xác nhận, bản cũ không thấy: {esc(', '.join(extra))}</p>"
    cards.append(
        f"<article class=card data-scene='{esc(r['scene'] or '?')}' data-dots='{r['reddots']}' data-conf='{len(r['confirmed'])}'"
        f" data-diff='{1 if (miss or extra) else 0}' data-i='{r['i']}'>"
        f"<button class=thumb aria-label='Phóng to khung {r['i']}'><img loading=lazy src='img/{r['i']:03d}.jpg' alt='Khung {r['i']}'></button>"
        f"<div class=meta><div class=row><b>{esc(r['clock'])}</b><span class=chip>{esc(SCENE_VI.get(r['scene'] or '?', r['scene']))}</span>"
        f"<span class=chip dot>{r['reddots']} chấm đỏ</span></div>"
        f"<p class=k>Đã xác nhận</p><p>{conf}</p><p class=k>Chưa chắc (p ≥ 0,5)</p><p>{unc}</p>{diff}"
        f"<details><summary>Việc bot đang làm</summary><ul class=log>{bot}</ul></details></div></article>")

fixes = ""
for b in before:
    fixes += (f"<figure class=fix><div class=pair><div><img loading=lazy src='before/{esc(b['before'])}' alt='Trước'><figcaption>Trước</figcaption></div>"
              f"<div><img loading=lazy src='img/{b['after']:03d}.jpg' alt='Sau'><figcaption>Sau</figcaption></div></div>"
              f"<p><b>{esc(b['title'])}</b> {esc(b['note'])}</p></figure>")

scene_chips = "".join(f"<button class=f data-f='scene:{esc(k)}'>{esc(SCENE_VI.get(k, k))} <i>{v}</i></button>"
                      for k, v in scenes.most_common())
only_old_txt = ", ".join(f"{esc(k)} ×{v}" for k, v in only_old.most_common(8)) or "không có"
only_new_txt = ", ".join(f"{esc(k)} ×{v}" for k, v in only_new.most_common(8)) or "không có"

page = f"""<title>Đánh giá nhận diện #2</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;700&display=swap">
<style>
:root{{--bg:#f6f7f6;--surface:#fff;--fg:#17201d;--dim:#5b6862;--line:#dbe1de;--accent:#0b7a6b;--accent-soft:#dff1ed;
--warn:#a14a00;--warn-soft:#fbeede;--dot:#c4263f;--shadow:0 1px 2px rgba(20,30,25,.08);
--font:'Inter',system-ui,sans-serif;--head:'Space Grotesk','Inter',system-ui,sans-serif}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#0f1514;--surface:#171f1d;--fg:#e8efec;--dim:#97a6a0;--line:#2a3532;
--accent:#4cc9b4;--accent-soft:#16332d;--warn:#f0b36b;--warn-soft:#33250f;--dot:#ff6b81;--shadow:none;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#0f1514;--surface:#171f1d;--fg:#e8efec;--dim:#97a6a0;--line:#2a3532;--accent:#4cc9b4;--accent-soft:#16332d;
--warn:#f0b36b;--warn-soft:#33250f;--dot:#ff6b81;--shadow:none;color-scheme:dark}}
*{{box-sizing:border-box}}
body{{background:var(--bg);color:var(--fg);font:15px/1.55 var(--font);padding-block:28px 56px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}}
main{{max-width:1180px;margin:0 auto;display:grid;gap:36px}}
h1,h2{{font-family:var(--head);margin:0;text-wrap:balance}}
h1{{font-size:clamp(26px,4vw,38px);line-height:1.15}}
h2{{font-size:21px;margin-bottom:12px}}
p{{margin:0 0 8px}} .dim{{color:var(--dim)}} .lead{{max-width:68ch;color:var(--dim)}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}}
.stat{{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:12px 14px;box-shadow:var(--shadow)}}
.stat b{{display:block;font:700 24px var(--head);font-variant-numeric:tabular-nums}} .stat span{{color:var(--dim);font-size:13px}}
.note{{background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--warn);padding:14px 16px;border-radius:4px}}
.note ul{{margin:6px 0 0;padding-left:20px}} .note li{{margin-bottom:5px}}
.fixes{{display:grid;gap:18px}}
.fix{{margin:0;background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:14px;box-shadow:var(--shadow)}}
.pair{{display:grid;grid-template-columns:1fr 1fr;gap:12px}} .pair img{{width:100%;height:auto;border-radius:4px;border:1px solid var(--line);display:block}}
.pair figcaption{{font-size:12px;color:var(--dim);margin-top:4px;text-transform:uppercase;letter-spacing:.06em}}
.bar{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px}}
.f{{font:500 13px var(--font);background:var(--surface);color:var(--fg);border:1px solid var(--line);border-radius:999px;padding:6px 12px;cursor:pointer}}
.f i{{font-style:normal;color:var(--dim);margin-left:4px}} .f[aria-pressed=true]{{background:var(--accent);border-color:var(--accent);color:#fff}} .f[aria-pressed=true] i{{color:#fff}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,300px),1fr));gap:16px}}
.card{{background:var(--surface);border:1px solid var(--line);border-radius:6px;overflow:hidden;display:flex;flex-direction:column;box-shadow:var(--shadow)}}
.thumb{{all:unset;display:block;cursor:zoom-in;background:#000}} .thumb:focus-visible{{outline:3px solid var(--accent);outline-offset:-3px}}
.thumb img{{width:100%;aspect-ratio:540/960;object-fit:cover;display:block}}
.meta{{padding:10px 12px 12px;min-width:0}} .row{{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:6px}}
.chip{{font-size:12px;background:var(--accent-soft);color:var(--accent);padding:2px 8px;border-radius:999px}} .chip.dot{{background:transparent;color:var(--dot);border:1px solid var(--dot)}}
.k{{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--dim);margin:8px 0 1px}} .meta p{{overflow-wrap:anywhere;font-size:13px}} .meta i{{color:var(--dim);font-style:normal}}
.warn{{color:var(--warn);background:var(--warn-soft);padding:4px 8px;border-radius:4px}}
details summary{{cursor:pointer;color:var(--dim);font-size:13px;margin-top:6px}} .log{{margin:6px 0 0;padding-left:16px;font-size:12px;color:var(--dim)}} .log li{{margin-bottom:3px;overflow-wrap:anywhere}}
dialog{{border:0;background:transparent;max-width:100vw;max-height:100vh;padding:0}} dialog::backdrop{{background:rgba(0,0,0,.82)}}
.lb{{display:flex;gap:10px;align-items:center;justify-content:center;height:100vh;padding:10px}} .lb img{{max-height:94vh;max-width:min(94vw,540px);object-fit:contain;border-radius:4px}}
.lb button{{font:600 22px var(--font);background:var(--surface);color:var(--fg);border:1px solid var(--line);border-radius:999px;width:44px;height:44px;cursor:pointer}}
@media (max-width:560px){{.pair{{grid-template-columns:1fr}}}}
@media (prefers-reduced-motion:no-preference){{.card{{transition:transform .12s}} .card:hover{{transform:translateY(-2px)}}}}
</style>
<main>
<header><p class="dim" style="margin-bottom:4px">22/11/2026 · giả lập #2 · Age of Warpath bản Global</p>
<h1>Đánh giá nhận diện hình ảnh trên máy #2</h1>
<p class="lead">Một lượt chạy thật của bot trên #2 (HQ 4, {n} khung hình lưu lại trong lượt). Bộ nhận diện mới chỉ đọc ảnh: nó không chạm, không bấm gì, bot cũ vẫn là bên quyết định. Mỗi khung được vẽ lại bằng bộ nhận diện hiện tại: khung xanh = đã xác nhận, vàng = chưa chắc, vòng tím = chấm đỏ thông báo.</p></header>

<section aria-label="Số liệu"><div class="stats">
<div class="stat"><b>{n}</b><span>khung hình đánh giá</span></div>
<div class="stat"><b>20,9 phút</b><span>một vòng đầy đủ của bot trên #2</span></div>
<div class="stat"><b>{dots_new} / {dots_old}</b><span>chấm đỏ: bản mới / bản cũ</span></div>
<div class="stat"><b>{conf_frames}</b><span>khung có ít nhất 1 lớp xác nhận</span></div>
<div class="stat"><b>{p50(ms_new)/1000:.0f} s</b><span>trung vị bản mới / khung, hỏi 213 lớp (bản cũ {p50(ms_old)/1000:.0f} s); đo khi chạy 6 tiến trình song song nên cao hơn lúc chạy thật</span></div>
</div></section>

<section><h2>Đã sửa theo phản hồi của bạn</h2><div class="fixes">{fixes}</div></section>

<section><h2>Điểm yếu còn lại</h2><div class="note"><ul>
<li><b>Chưa có nhãn người</b> cho tập khung này, nên mức độ đúng/sai ở đây là do mắt người xem, chưa phải độ chính xác đo được.</li>
<li><b>Chưa nhận diện đối tượng bản đồ</b>: quái, mỏ, công trình, thanh máu và các icon menu chưa có lớp nào. Chỉ các lớp có ảnh mẫu (nút, ghim tình báo) và chấm đỏ mới được tìm.</li>
<li><b>Bản Global 3.6.0</b> trên #2 dùng ảnh mẫu cắt từ bản VN: nút nào khác kích thước/màu sẽ bị bỏ sót hoặc chỉ ở mức "chưa chắc".</li>
<li>Bản cũ thấy mà bản mới không xác nhận: {only_old_txt}. Bản mới xác nhận mà bản cũ không thấy: {only_new_txt}.</li>
<li>Bộ nhận diện mới <b>chậm hơn</b> bản cũ khi hỏi mọi lớp (đa tỉ lệ), và chưa được nối vào vòng lặp bot.</li></ul></div></section>

<section><h2>Toàn bộ khung hình</h2>
<div class="bar" role="toolbar" aria-label="Bộ lọc"><button class="f" data-f="all" aria-pressed="true">Tất cả <i>{n}</i></button>{scene_chips}
<button class="f" data-f="dots">Có chấm đỏ</button><button class="f" data-f="conf">Có xác nhận</button><button class="f" data-f="diff">Khác bản cũ</button></div>
<div class="grid" id="grid">{''.join(cards)}</div></section>
</main>
<dialog id="lb"><div class="lb"><button id="prev" aria-label="Khung trước">‹</button><img id="big" alt=""><button id="next" aria-label="Khung sau">›</button></div></dialog>
<script>
const cards=[...document.querySelectorAll('.card')], dlg=document.getElementById('lb'), big=document.getElementById('big');
let cur=0, vis=cards;
function apply(f){{vis=[];cards.forEach(c=>{{let ok=f==='all'||(f==='dots'&&+c.dataset.dots>0)||(f==='conf'&&+c.dataset.conf>0)||(f==='diff'&&c.dataset.diff==='1')||(f.startsWith('scene:')&&c.dataset.scene===f.slice(6));c.hidden=!ok;if(ok)vis.push(c)}})}}
document.querySelectorAll('.f').forEach(b=>b.addEventListener('click',()=>{{document.querySelectorAll('.f').forEach(x=>x.setAttribute('aria-pressed','false'));b.setAttribute('aria-pressed','true');apply(b.dataset.f)}}));
function show(k){{cur=(k+vis.length)%vis.length;big.src=vis[cur].querySelector('img').src}}
cards.forEach(c=>c.querySelector('.thumb').addEventListener('click',()=>{{show(vis.indexOf(c));dlg.showModal()}}));
document.getElementById('prev').onclick=()=>show(cur-1);document.getElementById('next').onclick=()=>show(cur+1);
dlg.addEventListener('click',e=>{{if(e.target===dlg||e.target.classList.contains('lb'))dlg.close()}});
addEventListener('keydown',e=>{{if(!dlg.open)return;if(e.key==='ArrowLeft')show(cur-1);if(e.key==='ArrowRight')show(cur+1)}});
</script>
"""
open(os.path.join(out, "index.html"), "w", encoding="utf8").write(page)
print("index.html", len(page) // 1024, "KB;", n, "khung")
_ = shutil
