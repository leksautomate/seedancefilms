"""plan.html: one self-contained page that shows the whole episode at a glance.

The scrubber across the top is the episode's runtime: one block per clip, as wide as its estimated length, so
the rhythm of the episode (and a scene that runs long) is visible before reading anything. Under it, one card per
clip: why the scene earns its place, the spoken lines, the shots, the warnings, and the prompt with a copy button.
Everything on the page is derived from episode.json. Nothing is written twice.
"""
from __future__ import annotations

import html

from .render import MODE_HELP, seg_files

CSS = """
:root{--bg:#f6f3ec;--card:#fffdf8;--ink:#1d1a16;--ink2:#5b554b;--rule:#ded7c8;--accent:#b4401f;--ok:#2f7d4f;--warn:#b7791f;--bad:#b3261e;
--gen:#b4401f;--ext:#d89a7f;--chain:#5a4a8a;--single:#2c6e7f}
@media (prefers-color-scheme:dark){:root{--bg:#16130f;--card:#1f1b16;--ink:#efe9dc;--ink2:#a79f8f;--rule:#35302a;--accent:#e0714d;--ok:#6cc48c;--warn:#e0b255;--bad:#f2766d;
--gen:#e0714d;--ext:#8a5a49;--chain:#8c7bd0;--single:#5ab1c4}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 Georgia,'Times New Roman',serif}
.wrap{max-width:1040px;margin:0 auto;padding:0 16px 64px}
.sans{font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}
.mono{font-family:ui-monospace,Menlo,Consolas,monospace}
header{padding:36px 0 12px}.eyebrow{font:600 12px/1 -apple-system,sans-serif;letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}
h1{font-size:clamp(28px,5vw,44px);line-height:1.1;margin:8px 0 12px}.deck{color:var(--ink2);max-width:62ch;margin:0 0 14px}
.facts{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 6px}.fact{font:13px -apple-system,sans-serif;border:1px solid var(--rule);border-radius:999px;padding:3px 12px;background:var(--card)}
.rib{position:sticky;top:0;z-index:5;background:var(--bg);padding:10px 0 12px;border-bottom:1px solid var(--rule)}
.scrub{display:flex;gap:2px;height:38px}.cell{min-width:22px;border-radius:3px;color:#fff;font:600 11px/38px -apple-system,sans-serif;text-align:center;
overflow:hidden;white-space:nowrap;text-decoration:none;opacity:.92}.cell:hover,.cell.on{opacity:1;outline:2px solid var(--ink)}
.m-single{background:var(--single)}.m-generate{background:var(--gen)}.m-extend{background:var(--ext)}.m-new-chain{background:var(--chain)}
.cell.needs-review{background-image:repeating-linear-gradient(45deg,rgba(0,0,0,.28) 0 5px,transparent 5px 10px)}
.cell.pending{opacity:.4}.legend{display:flex;gap:14px;flex-wrap:wrap;margin-top:8px;font:12px -apple-system,sans-serif;color:var(--ink2)}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}
.act{margin:34px 0 8px;padding-top:10px;border-top:2px solid var(--ink)}.act b{font:700 13px -apple-system,sans-serif;letter-spacing:.08em;text-transform:uppercase}
.act span{display:block;color:var(--ink2);font-size:15px}
.card{display:grid;grid-template-columns:200px 1fr;gap:20px;background:var(--card);border:1px solid var(--rule);border-radius:10px;padding:18px;margin:14px 0;scroll-margin-top:90px}
@media(max-width:720px){.card{grid-template-columns:1fr}}
.id{font:700 26px/1 -apple-system,sans-serif}.scene{color:var(--ink2);font-size:14px;margin:4px 0 10px}
.badge{display:inline-block;font:600 11px -apple-system,sans-serif;text-transform:uppercase;letter-spacing:.06em;border-radius:4px;padding:2px 7px;color:#fff;margin:0 4px 4px 0}
.s-ok{background:var(--ok)}.s-needs-review{background:var(--bad)}.s-pending{background:var(--ink2)}
.bar{height:8px;background:var(--rule);border-radius:4px;margin:10px 0 4px;position:relative;overflow:hidden}.bar i{position:absolute;left:0;top:0;bottom:0;background:var(--accent)}
.bar i.over{background:var(--bad)}.nums{font:12px -apple-system,sans-serif;color:var(--ink2)}
h3{font:700 12px -apple-system,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--ink2);margin:16px 0 6px}h3:first-child{margin-top:0}
.why{font-size:17px;margin:0}.why.weak{color:var(--bad)}
table{border-collapse:collapse;width:100%;font:13px -apple-system,sans-serif}th,td{text-align:left;padding:4px 8px 4px 0;border-bottom:1px solid var(--rule);vertical-align:top}
th{color:var(--ink2);font-weight:600}.say{margin:0 0 4px}.say b{font:700 12px -apple-system,sans-serif;letter-spacing:.04em}
.warn{font:13px -apple-system,sans-serif;color:var(--warn);margin:2px 0}.err{font:13px -apple-system,sans-serif;color:var(--bad);margin:2px 0}
details{margin-top:12px}summary{cursor:pointer;font:600 13px -apple-system,sans-serif}
pre{white-space:pre-wrap;word-wrap:break-word;background:var(--bg);border:1px solid var(--rule);border-radius:8px;padding:12px;font:13px/1.5 ui-monospace,Menlo,Consolas,monospace;margin:8px 0}
button{font:600 12px -apple-system,sans-serif;border:1px solid var(--ink);background:var(--card);color:var(--ink);border-radius:6px;padding:5px 12px;cursor:pointer}
button:hover{background:var(--ink);color:var(--bg)}.files{font:12px ui-monospace,Menlo,monospace;color:var(--ink2);margin-top:6px}
.status{margin-top:34px}.status table td:first-child{font-weight:700}
"""

JS = """
document.querySelectorAll('button[data-copy]').forEach(b=>b.addEventListener('click',()=>{
 const t=document.getElementById(b.dataset.copy).textContent;
 navigator.clipboard.writeText(t).then(()=>{const o=b.textContent;b.textContent='Copied';setTimeout(()=>b.textContent=o,1200)})}));
const cells=[...document.querySelectorAll('.cell')];
const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){cells.forEach(c=>c.classList.toggle('on',c.dataset.id===e.target.dataset.id))}}),{rootMargin:'-40% 0px -55% 0px'});
document.querySelectorAll('.card').forEach(c=>io.observe(c));
"""


def _e(x) -> str:
    return html.escape(str(x if x is not None else ""), quote=True)


def render(state: dict, offline: bool = False) -> str:
    a = state.get("analysis") or {}
    segs = state["segments"]
    total = sum(s.get("estimated_s", 0) for s in segs)
    notes = {n.get("scene"): n for n in a.get("scenes", [])}
    act_of: dict = {}
    for act in a.get("spine", []):
        for sc in act.get("scenes", []):
            act_of.setdefault(sc, act)
    counts = {k: sum(1 for s in segs if s.get("status") == k) for k in ("ok", "needs-review", "pending")}
    title = "Episode %02d%s" % (state["number"], (" — " + state["title"]) if state.get("title") else "")

    out = ["<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>",
           "<title>%s — %s</title><style>%s</style></head><body><div class=wrap>" % (_e(state["movie"]), _e(title), CSS),
           "<header><div class=eyebrow>%s</div><h1>%s</h1>" % (_e(state["movie"]), _e(title))]
    if a.get("logline"):
        out.append("<p class=deck>%s</p>" % _e(a["logline"]))
    out.append("<div class=facts><span class=fact>%.0fs estimated (%.1f min)</span><span class=fact>%d clips</span>"
               "<span class=fact>%s</span><span class=fact>%d ready · %d need review · %d pending</span>%s</div></header>" % (
                   total, total / 60, len(segs), _e(state.get("settings", {}).get("aspect_ratio", "16:9")), counts["ok"], counts["needs-review"], counts["pending"],
                   "<span class=fact>offline drafts, no model used</span>" if offline else ""))
    out.append("<div class=rib><div class=scrub>")
    for s in segs:
        out.append("<a class='cell m-%s %s' data-id='%s' style='flex:%.2f' href='#seg-%s' title='%s · %s · %.1fs'>%s</a>" % (
            _e(s["mode"]), _e(s.get("status", "pending")), _e(s["id"]), max(s.get("estimated_s", 1), 1), _e(s["id"]), _e(s["id"]), _e(s["mode"]),
            s.get("estimated_s", 0), _e(s["id"])))
    out.append("</div><div class=legend><span><i class=m-single></i>single</span><span><i class=m-generate></i>generate</span>"
               "<span><i class=m-extend></i>extension</span><span><i class=m-new-chain></i>new chain</span><span>hatched = needs review</span></div></div>")

    last_act = None
    for s in segs:
        act = act_of.get(s["scene"])
        if act is not None and act is not last_act:
            out.append("<div class=act><b>%s</b><span>%s</span></div>" % (_e(act.get("act", "")), _e(act.get("note", ""))))
            last_act = act
        folder, pfile, bfile = seg_files(s)
        note = notes.get(s["scene"]) or {}
        why = note.get("why") or ""
        weak = why.lower().startswith("not yet earned")
        limit = s.get("request_s") or 15
        pct = min(100, 100 * s.get("estimated_s", 0) / max(limit, 1))
        over = s.get("estimated_s", 0) > limit
        out.append("<section class=card id='seg-%s' data-id='%s'><div>" % (_e(s["id"]), _e(s["id"])))
        out.append("<div class=id>%s</div><div class=scene>%s</div>" % (_e(s["id"]), _e(s.get("scene_title") or s.get("heading", ""))))
        out.append("<span class='badge m-%s'>%s</span><span class='badge s-%s'>%s</span>" % (_e(s["mode"]), _e(s["mode"]), _e(s.get("status", "pending")), _e(s.get("status", "pending"))))
        out.append("<div class=bar><i class='%s' style='width:%.0f%%'></i></div><div class=nums>%.1fs estimated of %ds%s · %d lines · %d words</div>" % (
            "over" if over else "", pct, s.get("estimated_s", 0), limit, (" · plan %ds" % s["planned_s"]) if s.get("planned_s") and s.get("part", 1) == 1 else "",
            s.get("dialogue_lines", 0), s.get("dialogue_words", 0)))
        out.append("<div class=nums style='margin-top:8px'>%s</div></div><div>" % _e(MODE_HELP.get(s["mode"], "")))
        if why:
            out.append("<h3>Why this scene earns its place</h3><p class='why%s'>%s</p>" % (" weak" if weak else "", _e(why)))
        dl = [e for e in s.get("events", []) if e.get("kind") == "dialogue"]
        if dl:
            out.append("<h3>Spoken lines</h3>")
            for e in dl:
                out.append("<p class=say><b>%s</b> “%s”</p>" % (_e(e.get("speaker")), _e(e.get("text"))))
        if s.get("shots"):
            out.append("<h3>Shots</h3><table><tr><th>#<th>Scale<th>Angle<th>Camera<th>Sec<th>Job")
            for sh in s["shots"]:
                out.append("<tr><td>%s<td>%s<td>%s<td>%s<td>%s<td>%s" % tuple(_e(sh.get(k, "")) for k in ("n", "scale", "angle", "camera", "seconds", "function")))
            out.append("</table>")
        for er in s.get("errors", []):
            out.append("<div class=err>✖ %s</div>" % _e(er))
        for w in s.get("warnings", []):
            out.append("<div class=warn>⚠ %s</div>" % _e(w))
        if s.get("prompt"):
            out.append("<details><summary>Prompt</summary><p><button data-copy='p-%s'>Copy prompt</button></p><pre id='p-%s'>%s</pre></details>" % (_e(s["id"]), _e(s["id"]), _e(s["prompt"])))
        out.append("<div class=files>%s/%s</div></div></section>" % (_e(folder), _e(pfile)))

    out.append("<div class=status><h3>Status</h3><table><tr><th>Clip<th>Mode<th>Estimated<th>Request<th>Status<th>Attempts")
    for s in segs:
        out.append("<tr><td>%s<td>%s<td>%.1fs<td>%ss<td>%s<td>%s" % (_e(s["id"]), _e(s["mode"]), s.get("estimated_s", 0), _e(s.get("request_s")), _e(s.get("status", "pending")), _e(s.get("attempts", ""))))
    out.append("</table></div></div><script>%s</script></body></html>" % JS)
    return "".join(out)
