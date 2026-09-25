#!/usr/bin/env python3
"""Build the SETI Post-Detection Protocols archive site.

Usage:
  python3 build.py                      # writes index.html from catalogue.json
  python3 build.py --catalogue X.json --preview --fragment --out preview.html

Only entries whose "release" is "public" or "cite" are published.
With --preview, entries marked "review" are included and flagged.
Edit catalogue.json to add or change documents, put the file in files/,
then run this script again. No other software is needed.
"""
import argparse, json, html, re, datetime
from collections import OrderedDict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("--catalogue", default=str(HERE / "catalogue.json"))
ap.add_argument("--out", default=str(HERE / "index.html"))
ap.add_argument("--preview", action="store_true")
ap.add_argument("--fragment", action="store_true", help="omit <html>/<head>/<body> wrapper")
args = ap.parse_args()

cat = json.load(open(args.catalogue, encoding="utf-8"))
docs_all = cat["documents"] if isinstance(cat, dict) else cat
allowed = {"public", "cite", "link", "pending"} | ({"review"} if args.preview else set())
docs = [d for d in docs_all if d.get("release") in allowed]
byid = {d["id"]: d for d in docs}
principles = json.load(open(HERE / "principles.json", encoding="utf-8"))
compare = json.load(open(HERE / "compare.json", encoding="utf-8"))
milestones = json.load(open(HERE / "milestones.json", encoding="utf-8"))

e = lambda s: html.escape(str(s or ""), quote=True)
YEARS = ["1989", "2010", "2026"]
CATS = OrderedDict([
    ("core", "Protocols and position papers"),
    ("revision", "The 2022–2026 revision"),
    ("scales", "Assessment scales"),
    ("history", "Histories"),
    ("governance", "Governance"),
    ("meetings", "Committee records"),
])

def status_class(s):
    s = (s or "").lower()
    if s.startswith("current"): return "st-current"
    if "draft" in s or "forthcoming" in s: return "st-draft"
    if "superseded" in s: return "st-old"
    if "adopted" in s: return "st-adopted"
    return "st-record"

def file_link(d):
    if d.get("file") and d.get("release") in ("public", "review"):
        kind = "JPG" if d["file"].lower().endswith(".jpg") else "PDF"
        return f'<a class="btn" href="files/{e(d["file"])}">Open {kind}</a>'
    return ""

def card(d, alt=None):
    rv = d.get("release") == "review"
    did = d["id"] + (f"--{alt}" if alt else "")
    meta = [("Date", d.get("date_label")), ("Issued by", d.get("issuer")), ("Type", d.get("type"))]
    if d.get("ref"): meta.append(("Reference", d["ref"]))
    if d.get("meeting") and d.get("category") == "meetings": meta.append(("Meeting", d["meeting"]))
    dl = "".join(f"<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>" for k, v in meta if v)
    links = file_link(d)
    if d.get("link"):
        links += f' <a class="btn ghost" href="{e(d["link"])}" rel="noopener">{e(d.get("link_label") or "External link")} ↗</a>'
    if d.get("release") == "cite":
        links += '<span class="cite-note">Citation only. The full text is not hosted here.</span>'
    if d.get("release") == "pending":
        links += '<span class="cite-note">Not yet available. It will be added here once adopted.</span>'
    flag = f'<p class="review-flag"><strong>Needs your OK before publishing.</strong> {e(d.get("review_note"))}</p>' if rv else ""
    notes = f'<p class="notes">{e(d.get("notes"))}</p>' if d.get("notes") else ""
    return f'''<details class="doc{' is-review' if rv else ''}" id="{e(did)}" data-cat="{e(d['category'])}" data-text="{e((d['title']+' '+d.get('summary','')+' '+d.get('issuer','')+' '+d.get('date_label','')).lower())}">
<summary><span class="d-date">{e(d.get('date_label'))}</span><span class="d-title">{e(d['title'])}</span><span class="pill {status_class(d.get('status'))}">{e(d.get('status'))}</span>{'<span class="pill st-pd">Post-detection</span>' if alt is not None and (d.get('pdp') or d.get('category')=='revision') else ''}{'<span class="pill st-review">Review</span>' if rv else ''}</summary>
<div class="d-body">{flag}<p>{e(d.get('summary'))}</p>{notes}<dl class="meta">{dl}</dl><div class="links">{links}</div></div>
</details>'''

def doc_ref(i, label=None):
    d = byid.get(i)
    if not d: return ""
    if d.get("category") == "revision" and d.get("also_meetings"):
        i = i + "--" + re.sub(r"[^a-z0-9]+", "-", d["also_meetings"][0].lower()).strip("-")
    return f'<a href="#{e(i)}" data-open="{e(i)}">{e(label or d.get("short") or d["title"])}</a>'

# ---------- sections ----------
lineage_ids = ["declaration-1989", "position-paper-1996", "declaration-2010", "declaration-2026"]
def year_of(d): return int(d["date"][:4])
axis = []
for i in lineage_ids:
    d = byid.get(i)
    if not d: continue
    y = year_of(d); pos = (2030 - y) / (2030 - 1985) * 100
    cls = {"reply-draft-1995": " nr", "position-paper-1996": " nl"}.get(i, "")
    axis.append(f'<a class="tick{cls}" style="left:{pos:.2f}%" href="#{e(i)}" data-open="{e(i)}"><span class="tick-y">{y}</span><span class="tick-dot"></span></a>')
decades = "".join(f'<span class="dec" style="left:{(2030-y)/45*100:.2f}%">{y}</span>' for y in (2030, 2020, 2010, 2000, 1990))
lin_cards = []
for n, i in enumerate([x for x in reversed(lineage_ids) if x != "declaration-2026"], 1):
    d = byid.get(i)
    if not d: continue
    lin_cards.append(f'''<li class="lin"><span class="lin-y">{e(d['date'][:4])}</span>
<h3><a href="#{e(i)}" data-open="{e(i)}">{e(d['short'])}</a></h3>
<p class="lin-t">{e(d['title'])}</p><span class="pill {status_class(d['status'])}">{e(d['status'])}</span></li>''')

ms = []
for m in reversed(milestones):
    ref = doc_ref(m["doc"], "Source") if m.get("doc") else ""
    ms.append(f'<li class="{"planned" if m.get("planned") else ""}"><span class="ms-d">{e(m["date"])}</span><p>{e(m["text"])} {ref}</p></li>')

cmp_rows = []
for row in compare:
    cells = []
    for y in YEARS:
        c = row["cells"][y]
        ps = c["p"]
        label = ("Principle " if len(ps) == 1 else "Principles ") + ", ".join(str(p) for p in ps) if ps else "—"
        full = "".join(f'<p><b>{p}.</b> {e(principles[y][str(p)])}</p>' for p in ps)
        det = f'<details class="full"><summary>Full text</summary>{full}</details>' if ps else ""
        cells.append(f'<div class="cell{" empty" if not ps else ""}"><div class="cell-h"><span class="cy">{y}</span><span class="cp">{e(label)}</span></div><p>{e(c["gist"])}</p>{det}</div>')
    cmp_rows.append(f'<article class="crow"><header><h3>{e(row["theme"])}</h3><p>{e(row["change"])}</p></header><div class="cells">{"".join(cells)}</div></article>')

GROUP_INTRO = {
    "scales": "Two scales developed within the Committee to put a number on events that are otherwise hard to judge. The Rio Scale rates the significance of a claimed detection of extraterrestrial intelligence; the San Marino Scale rates the potential impact of a deliberate transmission from Earth.",
}
def by_date(ds): return sorted(ds, key=lambda d: d["date"])
cat_blocks = []
for k, label in CATS.items():
    if k in ("meetings", "revision"): continue
    items = by_date([d for d in docs if d["category"] == k])[::-1]
    items.sort(key=lambda d: d["id"] != "declaration-2026")
    items.sort(key=lambda d: d["id"] == "dumas-catalogue")
    if not items: continue
    intro = f'<p class="gintro">{e(GROUP_INTRO[k])}</p>' if k in GROUP_INTRO else ""
    cat_blocks.append(f'<section class="cgroup" data-group="{k}"><h3>{e(label)} <span class="count">{len(items)}</span></h3>{intro}{"".join(card(d) for d in items)}</section>')

meet = OrderedDict()
for d in by_date(docs):
    if d["category"] == "meetings" and d.get("meeting"):
        meet.setdefault(d["meeting"], []).append((d, ""))
    for mm in d.get("also_meetings") or []:
        meet.setdefault(mm, []).append((d, re.sub(r"[^a-z0-9]+", "-", mm.lower()).strip("-")))
for k in meet: meet[k].sort(key=lambda t: t[0]["date"], reverse=True)
meet_order = sorted(meet.items(), key=lambda kv: max(d["date"] for d, _ in kv[1]), reverse=True)
def mhead(k, v):
    n_pd = sum(1 for d, _ in v if d.get("pdp") or d.get("category") == "revision")
    pd = f'<span class="pill st-pd">Post-detection</span>' if n_pd else ""
    return f'<header class="mhead"><h3>{e(k)}</h3><span class="mcount">{len(v)} document{"s" if len(v) != 1 else ""}</span>{pd}</header>'
meet_blocks = "".join(f'<section class="mgroup" id="m-{re.sub(r"[^a-z0-9]+", "-", k.lower()).strip("-")}">{mhead(k, v)}{"".join(card(d, alt) for d, alt in v)}</section>' for k, v in meet_order)
meet_index = "".join(f'<a href="#m-{re.sub(r"[^a-z0-9]+", "-", k.lower()).strip("-")}">{e(k)}</a>' for k, v in meet_order)

n_review = sum(1 for d in docs if d.get("release") == "review")
banner = f'<div class="preview-banner" role="note"><strong>Private preview.</strong> This version includes {n_review} documents marked <em>Review</em> that are not yet cleared for publication. The public site leaves them out until you approve them.</div>' if args.preview else ""
chips = "".join(f'<button type="button" class="chip" data-f="{k}" aria-pressed="false">{e(v)}</button>' for k, v in CATS.items() if k not in ("meetings", "revision"))
today = datetime.date.today().strftime("%-d %B %Y")
n_docs = len(docs)

CSS = r"""
:root{--bg:#F3F5F7;--surface:#FFFFFF;--ink:#15202B;--muted:#56636F;--rule:#D6DDE4;--accent:#1E4E8C;--accent-soft:#E3ECF7;--draft:#9A6412;--draft-soft:#F8EEDC;--ok:#2B7050;--ok-soft:#E1F1E8;--old:#6B7580;--old-soft:#ECEFF2;--rv:#A23B2A;--rv-soft:#FBE7E3;
--serif:"Newsreader",Georgia,"Times New Roman",serif;--sans:"Public Sans",system-ui,-apple-system,"Segoe UI",sans-serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#0D1319;--surface:#141C24;--ink:#E3E8EE;--muted:#98A5B2;--rule:#26323E;--accent:#8DB7EA;--accent-soft:#1A2A3D;--draft:#E3B25E;--draft-soft:#2E2413;--ok:#72C69B;--ok-soft:#15291F;--old:#9AA4AE;--old-soft:#1E2730;--rv:#F08C78;--rv-soft:#3A1E19;}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#0D1319;--surface:#141C24;--ink:#E3E8EE;--muted:#98A5B2;--rule:#26323E;--accent:#8DB7EA;--accent-soft:#1A2A3D;--draft:#E3B25E;--draft-soft:#2E2413;--ok:#72C69B;--ok-soft:#15291F;--old:#9AA4AE;--old-soft:#1E2730;--rv:#F08C78;--rv-soft:#3A1E19;}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:64px}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 var(--sans);-webkit-font-smoothing:antialiased}
a{color:var(--accent)}
a:focus-visible,button:focus-visible,summary:focus-visible,input:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:3px}
.wrap{max-width:1080px;margin:0 auto;padding-inline:20px}
h1,h2,h3{font-family:var(--serif);font-weight:500;text-wrap:balance;line-height:1.2;margin:0}
.eyebrow{font:500 12px/1 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.preview-banner{background:var(--rv-soft);color:var(--ink);border-bottom:1px solid var(--rv);padding:10px 20px;font-size:14px;text-align:center}
header.mast{padding-block:56px 40px;border-bottom:1px solid var(--rule)}
.brand{margin-bottom:28px}
.logo{height:auto;width:min(340px,80vw);display:block}
.logo-d{display:none}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .logo-l{display:none}:root:not([data-theme="light"]) .logo-d{display:block}}
:root[data-theme="dark"] .logo-l{display:none}:root[data-theme="dark"] .logo-d{display:block}
header.mast h1{font-size:clamp(30px,5vw,48px);letter-spacing:-.01em;margin-top:0;max-width:30ch;hyphens:manual}
header.mast .lede{font-size:19px;max-width:62ch;color:var(--muted);margin:18px 0 0}
header.mast .facts{display:flex;flex-wrap:wrap;gap:8px 28px;margin-top:26px;font:14px var(--mono);color:var(--muted)}
header.mast .facts b{color:var(--ink);font-weight:500}
nav.top{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:color-mix(in srgb,var(--bg) 92%,transparent);backdrop-filter:blur(6px);border-bottom:1px solid var(--rule)}
nav.top .wrap{display:flex;gap:4px;overflow-x:auto;padding-block:8px}
nav.top a{font:500 14px var(--sans);color:var(--ink);text-decoration:none;padding:8px 12px;border-radius:6px;white-space:nowrap}
nav.top a:hover{background:var(--accent-soft)}
section.band{padding-block:56px;border-bottom:1px solid var(--rule)}
section.band>.wrap>h2{font-size:clamp(26px,3.6vw,36px)}
.sub{color:var(--muted);max-width:64ch;margin:10px 0 0}
.current{margin-top:28px;background:var(--surface);border:1px solid var(--rule);border-left:4px solid var(--ok);border-radius:8px;padding:24px 26px}
.current h3{font-size:clamp(22px,3vw,28px);margin:10px 0 12px;max-width:40ch}
.current p{max-width:72ch;margin:0 0 12px}
.cur-meta{font:13px var(--mono);color:var(--muted)}
.cur-tg{font-size:15px}
.subhead{font-size:24px;margin-top:44px}
/* lineage axis */
.axis{position:relative;height:74px;margin:40px 8px 8px}
.axis::before{content:"";position:absolute;left:0;right:0;top:27px;height:2px;background:var(--rule)}
.dec{position:absolute;top:44px;transform:translateX(-50%);font:12px var(--mono);color:var(--muted);opacity:.7}
.dec::before{content:"";position:absolute;left:50%;top:-12px;width:1px;height:8px;background:var(--rule)}
.tick{position:absolute;top:0;transform:translateX(-50%);display:flex;flex-direction:column;align-items:center;text-decoration:none;color:var(--ink)}
.tick-dot{width:14px;height:14px;border-radius:50%;background:var(--surface);border:3px solid var(--accent);margin-top:4px}
.tick-y{font:600 13px/16px var(--mono)}
.tick.nl .tick-y{transform:translateX(-16px)}.tick.nr .tick-y{transform:translateX(16px)}
.lineage{list-style:none;padding:0;margin:28px 0 0;display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.lin{background:var(--surface);border:1px solid var(--rule);border-radius:8px;padding:16px;display:flex;flex-direction:column;gap:8px}
.lin-y{font:600 13px var(--mono);color:var(--accent)}
.lin h3{font-size:20px}
.lin h3 a{color:var(--ink);text-decoration:none}
.lin h3 a:hover{text-decoration:underline}
.lin-t{font-size:13px;color:var(--muted);margin:0;flex:1}
.lin .pill{align-self:flex-start}
@media (max-width:900px){.lineage{grid-template-columns:repeat(2,1fr)}.axis{display:none}}
@media (max-width:480px){.lineage{grid-template-columns:1fr}}
/* milestones */
.two{display:grid;grid-template-columns:1fr 1.6fr;gap:40px;margin-top:48px}
@media (max-width:800px){.two{grid-template-columns:1fr}}
.two h3{font-size:24px}
.ms{list-style:none;margin:0;padding:0;border-left:2px solid var(--rule)}
.ms li{position:relative;padding:0 0 18px 20px}
.ms li::before{content:"";position:absolute;left:-6px;top:7px;width:10px;height:10px;border-radius:50%;background:var(--accent)}
.ms li.planned::before{background:var(--bg);border:2px dashed var(--accent)}
.ms-d{font:500 13px var(--mono);color:var(--muted);font-variant-numeric:tabular-nums}
.ms p{margin:2px 0 0;max-width:62ch}
.ms a{font-size:14px;white-space:nowrap}
/* compare */
.legend{display:flex;gap:18px;flex-wrap:wrap;margin-top:18px;font:13px var(--mono);color:var(--muted)}
.crow{margin-top:28px;padding-top:24px;border-top:1px solid var(--rule)}
.crow header{display:grid;grid-template-columns:minmax(180px,1fr) 2fr;gap:8px 32px;align-items:baseline}
.crow h3{font-size:22px}
.crow header p{margin:0;color:var(--muted);max-width:64ch}
.cells{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:16px}
.cell{background:var(--surface);border:1px solid var(--rule);border-radius:8px;padding:14px 16px}
.cell.empty{background:transparent;border-style:dashed;color:var(--muted)}
.cell p{margin:8px 0 0;font-size:15px}
.cell-h{display:flex;justify-content:space-between;gap:8px;font:500 12px var(--mono);color:var(--muted)}
.cy{color:var(--accent);font-weight:600}
details.full{margin-top:10px}
details.full>summary{cursor:pointer;font-size:13px;color:var(--accent)}
details.full p{font-family:var(--serif);font-size:15.5px;line-height:1.55}
@media (max-width:800px){.cells{grid-template-columns:1fr}.crow header{grid-template-columns:1fr}}
/* catalogue */
.tools{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-top:24px}
.chip{font:500 13px var(--sans);border:1px solid var(--rule);background:var(--surface);color:var(--ink);border-radius:999px;padding:6px 12px;cursor:pointer}
.chip[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:var(--bg)}
.search{flex:1 1 220px;min-width:0;font:15px var(--sans);padding:8px 12px;border:1px solid var(--rule);border-radius:6px;background:var(--surface);color:var(--ink)}
.cgroup,.mgroup{margin-top:32px}
.mindex{display:flex;flex-wrap:wrap;gap:6px 8px;margin-top:20px}
.mindex a{font:500 13px var(--mono);padding:5px 10px;border:1px solid var(--rule);border-radius:999px;text-decoration:none;background:var(--surface)}
.mindex a:hover{border-color:var(--accent)}
.mhead{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 14px;margin-bottom:10px}
.mhead h3{margin:0!important}
.mcount{font:13px var(--mono);color:var(--muted)}
.gintro{color:var(--muted);max-width:70ch;margin:0 0 12px}
.cgroup h3,.mgroup h3{font-size:22px;margin-bottom:10px}
.count{font:13px var(--mono);color:var(--muted);vertical-align:middle}
details.doc{background:var(--surface);border:1px solid var(--rule);border-radius:8px;margin-top:8px}
details.doc>summary{list-style:none;cursor:pointer;display:grid;grid-template-columns:150px 1fr auto auto auto;gap:6px 14px;align-items:baseline;padding:12px 16px}
details.doc>summary::-webkit-details-marker{display:none}
details.doc>summary:hover .d-title{color:var(--accent)}
details.doc[open]>summary{border-bottom:1px solid var(--rule)}
.d-date{font:13px var(--mono);color:var(--muted);font-variant-numeric:tabular-nums}
.d-title{font-weight:500}
.d-body{padding:4px 16px 16px}
.d-body>p{max-width:70ch}
.notes{color:var(--muted);font-size:14.5px}
dl.meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px 24px;margin:14px 0;font-size:14px}
dl.meta dt{font:500 11px var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
dl.meta dd{margin:2px 0 0}
.links{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.btn{display:inline-block;font:500 14px var(--sans);padding:7px 14px;border-radius:6px;background:var(--accent);color:var(--bg);text-decoration:none}
.btn.ghost{background:transparent;color:var(--accent);border:1px solid var(--accent)}
.cite-note{font-size:13px;color:var(--muted)}
.pill{font:500 11px var(--mono);letter-spacing:.04em;text-transform:uppercase;padding:3px 8px;border-radius:4px;white-space:nowrap}
.st-current{background:var(--ok-soft);color:var(--ok)}
.st-adopted{background:var(--accent-soft);color:var(--accent)}
.st-draft{background:var(--draft-soft);color:var(--draft)}
.st-old{background:var(--old-soft);color:var(--old)}
.st-record{background:var(--old-soft);color:var(--muted)}
.st-pd{background:var(--accent-soft);color:var(--accent)}
.st-review{background:var(--rv-soft);color:var(--rv)}
.review-flag{background:var(--rv-soft);border-left:3px solid var(--rv);padding:8px 12px;font-size:14px}
@media (max-width:700px){details.doc>summary{display:flex;flex-wrap:wrap;gap:6px 8px}.d-date,.d-title{flex:1 1 100%}.pill{white-space:normal}}
.empty-msg{color:var(--muted);margin-top:24px}
/* about */
.about{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:28px;margin-top:28px}
.about h3{font-size:20px;margin-bottom:8px}
.about p{margin:0 0 10px;max-width:60ch}
footer{padding-block:36px;color:var(--muted);font-size:14px}
"""

JS = r"""
(function(){
  function openDoc(id){var el=document.getElementById(id);if(el&&el.tagName==='DETAILS'){el.open=true;var s=el.closest('section.cgroup');if(s)s.hidden=false;el.hidden=false;}}
  document.addEventListener('click',function(ev){var a=ev.target.closest('[data-open]');if(a)openDoc(a.getAttribute('data-open'));});
  if(location.hash){openDoc(location.hash.slice(1));}
  window.addEventListener('hashchange',function(){openDoc(location.hash.slice(1));});
  var chips=[].slice.call(document.querySelectorAll('.chip')),q=document.getElementById('q'),active=null,msg=document.getElementById('nores');
  function apply(){var t=(q.value||'').trim().toLowerCase(),shown=0;
    document.querySelectorAll('#catalogue section.cgroup').forEach(function(g){var any=false;
      g.querySelectorAll('details.doc').forEach(function(d){var ok=(!active||d.dataset.cat===active)&&(!t||d.dataset.text.indexOf(t)>-1);d.hidden=!ok;if(ok){any=true;shown++;}});
      g.hidden=!any;});
    msg.hidden=shown>0;}
  chips.forEach(function(c){c.addEventListener('click',function(){var f=c.dataset.f;active=(active===f)?null:f;chips.forEach(function(x){x.setAttribute('aria-pressed',String(x.dataset.f===active));});apply();});});
  if(q)q.addEventListener('input',apply);
})();
"""

cur = byid.get("declaration-2026")
featured = ""
if cur:
    pr = byid.get("press-release-2026")
    prl = f'<a class="btn ghost" href="files/{e(pr["file"])}">Press release</a>' if pr and pr.get("file") else ""
    featured = (f'<div class="current"><span class="pill st-current">Current</span><h3>{e(cur["title"])}</h3>'
        f'<p>{e(cur["summary"])}</p><p class="cur-meta">Published by the International Academy of Astronautics · {e(cur["date_label"])}</p><p class="cur-tg">Prepared by the IAA SETI Committee Post-Detection Task Group, chaired by Michael Garrett, with Kathryn Denning, Les Tennen and Carol Oliver.</p>'
        f'<div class="links"><a class="btn" href="files/{e(cur["file"])}">Read the 2026 Update (PDF)</a> '
        f'{prl}</div></div>')
BODY = f"""{banner}
<header class="mast"><div class="wrap">
<div class="brand"><img class="logo logo-l" src="logo-light.png" alt="International Academy of Astronautics SETI Committee" width="808" height="192"><img class="logo logo-d" src="logo-dark.png" alt="International Academy of Astronautics SETI Committee" width="808" height="192"></div>
<h1>The SETI post-detection protocols and Committee records</h1>
<p class="lede">The IAA SETI Committee is the international forum for the scientific, technical and societal aspects of the search for extraterrestrial intelligence. It organises the IAA SETI Symposium at the International Astronautical Congress (IAC) each year. Its most important responsibility is the SETI post-detection protocols: the principles scientists should follow if they detect evidence of extraterrestrial intelligence. This site sets out the current protocols and every earlier version since 1989, together with the records of the Committee's meetings.</p>
<div class="facts"><span>Current protocols: <b>2026 Update</b></span><span><b>{n_docs}</b> documents</span><span><b>{len(meet)}</b> meetings on record</span></div>
</div></header>
<nav class="top" aria-label="Sections"><div class="wrap">
<a href="#protocols">Post-detection protocols</a><a href="#documents">Documents</a><a href="#meetings">Meetings</a><a href="#about">About</a>
</div></nav>
<main>
<section class="band" id="protocols"><div class="wrap">
<h2>The post-detection protocols</h2>
{featured}
<h3 class="subhead">Earlier versions</h3><p class="sub">Two earlier declarations, from 2010 and 1989, were adopted and later replaced. Alongside them sits the 1996 IAA Position Paper on how humanity should decide whether to reply to a detection.</p>
<div class="axis" aria-hidden="true">{decades}{''.join(axis)}</div>
<ol class="lineage">{''.join(lin_cards)}</ol>
<div class="two">
<div><h3>How the 2026 Update was made</h3><p class="sub">Most recent first, from 2026 back to 2021, when the Committee, under its new Chair, restarted work on the protocols. Each step links to its source document.</p></div>
<ol class="ms">{''.join(ms)}</ol>
</div>
</div></section>
<section class="band" id="catalogue"><div class="wrap" id="documents">
<h2>Documents</h2>
<p class="sub">The protocols and position papers (newest first, from the 2026 Update back to the 1989 Declaration), the Rio and San Marino scales, histories of the Committee and its governance documents. Select an entry for its summary, details and file.</p>
<div class="tools">{chips}<input id="q" class="search" type="search" placeholder="Search titles and summaries" aria-label="Search the documents"></div>
<p id="nores" class="empty-msg" hidden>No documents match. Clear the search or choose another group.</p>
{''.join(cat_blocks)}
</div></section>
<section class="band" id="meetings"><div class="wrap">
<h2>Committee meetings</h2>
<p class="sub">Agendas, notes, reports and presentations from the Committee's meetings, most recent meeting and most recent document first. Meetings tagged <em>Post-detection</em> include discussion of the protocols. Drafts of the protocols presented at meetings are kept for the record; the current text is the <a href='#protocols'>2026 Update</a>.</p>
<div class="mindex" aria-label="Jump to a meeting">{meet_index}</div>
{meet_blocks}
</div></section>
<section class="band" id="about"><div class="wrap">
<h2>About</h2>
<div class="about">
<div><h3>This site</h3><p>Maintained by the IAA SETI Committee to keep its meeting records and the texts of the post-detection protocols together in one place that anyone can read.</p><p>The summaries were written for this site. The documents themselves are the authoritative source.</p></div>
<div><h3>Copyright</h3><p>The Committee's meeting records, presentations and reports are placed in the public domain with the agreement of their authors. Texts issued by the International Academy of Astronautics are reproduced for reference, and copyright in them stays with the IAA. Papers whose copyright is held by the International Astronautical Federation are reproduced with the permission of the IAF and their authors. Obituaries published elsewhere are linked rather than copied.</p></div>
<div><h3>Sources</h3><p>Some copies were printed from the Committee's earlier website, iaaseti.org, and carry the print date. Where an official copy exists elsewhere, the entry links to it.</p><p>The current Declaration is published by the IAA at <a href="https://iaaspace.org/wp-content/uploads/iaa/Scientific%20Activity/iaasetideclaration.pdf" rel="noopener">iaaspace.org</a>.</p></div>
<div><h3>Contact</h3><p>To report an error on this site, email <a href="mailto:michael.garrett@manchester.ac.uk">michael.garrett@manchester.ac.uk</a>.</p></div>
</div>
</div></section>
</main>
<footer><div class="wrap">IAA SETI Committee · last updated {today}</div></footer>
<script>{JS}</script>"""

FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Newsreader:opsz,wght@6..72,400;6..72,500&family=Public+Sans:wght@400;500;600&display=swap">'
TITLE = "IAA SETI Committee"
DESC = "Meeting records of the IAA SETI Committee and the SETI post-detection protocols, 1989 to 2026."

if args.fragment:
    out = f"<title>{TITLE}</title>\n{FONTS}\n<style>{CSS}</style>\n{BODY}"
else:
    out = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{TITLE}</title><link rel="icon" type="image/png" href="favicon.png"><meta name="description" content="{DESC}">
{FONTS}<style>{CSS}</style></head>
<body>{BODY}</body></html>"""
Path(args.out).write_text(out, encoding="utf-8")
print(f"wrote {args.out}: {n_docs} documents ({n_review} for review)")
