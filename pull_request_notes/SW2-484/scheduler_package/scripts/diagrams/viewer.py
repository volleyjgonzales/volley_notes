"""Build figures/viewer.html: a self-contained, offline pan/zoom gallery of every figure.

Only one figure lives in the DOM at a time (each SVG embeds its own font subset under the same
family names, so mounting them all at once would make the subsets fight)."""
from __future__ import annotations

import json
import re
from pathlib import Path

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Scheduler Core Refactor — Figures</title>
<style>
:root{--bg:#020617;--panel:#0F172A;--card:#1B2336;--muted-bg:#272F42;--fg:#F8FAFC;--fg2:#CBD5E1;--muted:#94A3B8;--faint:#64748B;--border:#334155;--accent:#22C55E}
*{box-sizing:border-box}
html,body{margin:0;height:100%;background:var(--bg);color:var(--fg);font-family:'IBM Plex Sans','Segoe UI',Roboto,Helvetica,Arial,sans-serif}
.app{display:grid;grid-template-columns:300px 1fr;height:100vh}
aside{background:var(--panel);border-right:1px solid var(--border);overflow:auto;padding:18px 14px}
aside h1{font-size:15px;margin:2px 6px 4px;font-weight:600}
aside p.sub{font-size:12px;color:var(--muted);margin:0 6px 14px;line-height:1.45}
aside h2{font:600 10.5px/1 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;letter-spacing:.08em;text-transform:uppercase;color:var(--faint);margin:18px 6px 8px}
aside button{display:block;width:100%;text-align:left;background:none;border:1px solid transparent;color:var(--fg2);font:inherit;font-size:13px;padding:8px 10px;border-radius:8px;cursor:pointer;line-height:1.35}
aside button small{display:block;color:var(--faint);font:11px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;margin-top:2px}
aside button:hover{background:var(--card)}
aside button[aria-current="true"]{background:var(--card);border-color:var(--border);color:var(--fg)}
aside button:focus-visible,.tools button:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
main{position:relative;overflow:hidden;background:radial-gradient(circle at 50% 40%,#0B1222 0,#020617 70%)}
#stage{position:absolute;inset:0;touch-action:none;cursor:grab}
#stage.drag{cursor:grabbing}
#stage svg{width:100%;height:100%;display:block}
.tools{position:absolute;top:14px;right:14px;display:flex;gap:6px;align-items:center;background:rgba(15,23,42,.88);border:1px solid var(--border);border-radius:12px;padding:6px;backdrop-filter:blur(6px)}
.tools button,.tools a{min-width:36px;height:36px;border-radius:8px;border:1px solid var(--border);background:var(--card);color:var(--fg);font:500 14px/1 inherit;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;padding:0 10px;text-decoration:none;font-family:inherit}
.tools button:hover,.tools a:hover{background:var(--muted-bg)}
.tools .zoom{color:var(--muted);font:12px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;min-width:48px;text-align:right;padding-right:4px}
.hint{position:absolute;left:16px;bottom:14px;color:var(--faint);font-size:12px;pointer-events:none}
.menu{display:none}
@media (max-width:820px){
  .app{grid-template-columns:1fr}
  aside{position:fixed;inset:0 30% 0 0;z-index:5;transform:translateX(-105%);transition:transform .2s ease}
  aside.open{transform:none}
  .menu{display:inline-flex}
  .hint{display:none}
}
@media (prefers-reduced-motion:reduce){aside{transition:none}}
</style>
</head>
<body>
<div class="app">
  <aside id="side" aria-label="Figures">
    <h1>Scheduler Core Refactor</h1>
    <p class="sub">Figure viewer · scroll or pinch to zoom, drag to pan, ← → to switch figures.</p>
    <nav id="nav"></nav>
  </aside>
  <main>
    <div id="stage" role="img" aria-live="polite"></div>
    <div class="tools">
      <button class="menu" id="menu" aria-label="Show figure list">☰</button>
      <span class="zoom" id="zoom">100%</span>
      <button id="out" aria-label="Zoom out" title="Zoom out (-)">−</button>
      <button id="in" aria-label="Zoom in" title="Zoom in (+)">+</button>
      <button id="fit" aria-label="Fit to screen" title="Fit (0)">Fit</button>
      <a id="raw" href="#" target="_blank" rel="noopener" title="Open the SVG file">SVG ↗</a>
    </div>
    <div class="hint">double-click to fit · keys: + − 0 ← →</div>
  </main>
</div>
<script>
const FIGS = __FIGS__;
const nav=document.getElementById('nav'), stage=document.getElementById('stage');
let cur=-1, svg=null, vb0=null, vb=null;
const groups={};
const DOCS={'01-background.html':'01 · Background','02-task-planning.html':'02 · Task planning','03-motion-planning.html':'03 · Motion planning','04-action-graph.html':'04 · Action graph','05-issue-and-proposal.html':'05 · Issue & proposal','06-verification.html':'06 · Verification'};
FIGS.forEach((f,i)=>{(groups[f.doc]=groups[f.doc]||[]).push(i)});
for(const [doc,idx] of Object.entries(groups)){
  const h=document.createElement('h2'); h.textContent=DOCS[doc]||doc; nav.appendChild(h);
  idx.forEach(i=>{const b=document.createElement('button'); b.innerHTML=FIGS[i].title+'<small>'+FIGS[i].name+'.svg</small>'; b.onclick=()=>{show(i); document.getElementById('side').classList.remove('open')}; b.dataset.i=i; nav.appendChild(b)});
}
function setVB(){svg.setAttribute('viewBox',vb.join(' ')); document.getElementById('zoom').textContent=Math.round(vb0[2]/vb[2]*100)+'%';}
function show(i){
  cur=(i+FIGS.length)%FIGS.length; const f=FIGS[cur];
  stage.innerHTML=f.svg; svg=stage.querySelector('svg');
  svg.removeAttribute('width'); svg.removeAttribute('height'); svg.setAttribute('preserveAspectRatio','xMidYMid meet');
  vb0=svg.getAttribute('viewBox').split(/\s+/).map(Number);
  const pad=Math.max(vb0[2],vb0[3])*0.03; vb0=[vb0[0]-pad,vb0[1]-pad,vb0[2]+2*pad,vb0[3]+2*pad]; vb=vb0.slice(); setVB();
  stage.setAttribute('aria-label',f.title);
  nav.querySelectorAll('button').forEach(b=>b.setAttribute('aria-current',String(+b.dataset.i===cur)));
  document.getElementById('raw').href=f.name+'.svg';
  if(location.hash!=='#'+f.name) history.replaceState(null,'','#'+f.name);
  document.title=f.title+' — Scheduler Core Refactor';
}
function toUser(cx,cy){const p=svg.createSVGPoint(); p.x=cx; p.y=cy; return p.matrixTransform(svg.getScreenCTM().inverse());}
function zoomAt(ux,uy,f){
  const nw=Math.min(vb0[2]*4,Math.max(vb0[2]/16,vb[2]/f)); f=vb[2]/nw; const nh=vb[3]/f;
  vb=[ux-(ux-vb[0])/f, uy-(uy-vb[1])/f, nw, nh]; setVB();
}
function center(){return [vb[0]+vb[2]/2, vb[1]+vb[3]/2]}
stage.addEventListener('wheel',e=>{e.preventDefault(); const p=toUser(e.clientX,e.clientY); const d=e.deltaMode===1?e.deltaY*16:e.deltaY; zoomAt(p.x,p.y,Math.exp(-d*0.0015*(e.ctrlKey?4:1)));},{passive:false});
const ptr=new Map(); let drag=null, pinch=null;
stage.addEventListener('pointerdown',e=>{stage.setPointerCapture(e.pointerId); ptr.set(e.pointerId,[e.clientX,e.clientY]); stage.classList.add('drag');
  if(ptr.size===1) drag={x:e.clientX,y:e.clientY,vb:vb.slice()};
  if(ptr.size===2){const [a,b]=[...ptr.values()]; pinch={d:Math.hypot(a[0]-b[0],a[1]-b[1])}; drag=null;}});
stage.addEventListener('pointermove',e=>{ if(!ptr.has(e.pointerId)) return; ptr.set(e.pointerId,[e.clientX,e.clientY]);
  if(pinch&&ptr.size===2){const [a,b]=[...ptr.values()]; const d=Math.hypot(a[0]-b[0],a[1]-b[1]); const m=toUser((a[0]+b[0])/2,(a[1]+b[1])/2); zoomAt(m.x,m.y,d/pinch.d); pinch.d=d; return;}
  if(drag){const s=svg.getScreenCTM().a; vb=[drag.vb[0]-(e.clientX-drag.x)/s, drag.vb[1]-(e.clientY-drag.y)/s, vb[2], vb[3]]; setVB();}});
function up(e){ptr.delete(e.pointerId); if(ptr.size<2) pinch=null; if(ptr.size===0){drag=null; stage.classList.remove('drag');}}
stage.addEventListener('pointerup',up); stage.addEventListener('pointercancel',up);
stage.addEventListener('dblclick',()=>{vb=vb0.slice(); setVB();});
document.getElementById('in').onclick=()=>zoomAt(...center(),1.25);
document.getElementById('out').onclick=()=>zoomAt(...center(),0.8);
document.getElementById('fit').onclick=()=>{vb=vb0.slice(); setVB();};
document.getElementById('menu').onclick=()=>document.getElementById('side').classList.toggle('open');
document.addEventListener('keydown',e=>{ if(e.target.tagName==='INPUT') return;
  if(e.key==='+'||e.key==='=') zoomAt(...center(),1.25); else if(e.key==='-') zoomAt(...center(),0.8);
  else if(e.key==='0'){vb=vb0.slice(); setVB();} else if(e.key==='ArrowRight'||e.key==='ArrowDown'){e.preventDefault(); show(cur+1);} else if(e.key==='ArrowLeft'||e.key==='ArrowUp'){e.preventDefault(); show(cur-1);} });
window.addEventListener('hashchange',()=>{const i=FIGS.findIndex(f=>'#'+f.name===location.hash); if(i>=0&&i!==cur) show(i);});
const start=FIGS.findIndex(f=>'#'+f.name===location.hash); show(start>=0?start:0);
</script>
</body>
</html>
"""

# Reading order = figure numbering in the documents (site/src/content/*.html), in tab order.
CONTENT = ("01-background.html", "02-task-planning.html", "03-motion-planning.html", "04-action-graph.html",
           "05-issue-and-proposal.html", "06-verification.html")
FIRST_DOC: dict = {}   # figure name -> the document it first appears in
def _doc_order():
    """Figure order and per-document numbers, read from the <img> order in the HTML sources."""
    root = Path(__file__).resolve().parents[2] / "site" / "src" / "content"
    order = []
    for name in CONTENT:
        seen = []
        source = re.sub(r"<!--.*?-->", "", (root / name).read_text(encoding="utf-8"), flags=re.S)
        for n in re.findall(r'<img src="figures/([^"]+)\.svg"', source):
            if n not in seen:
                seen.append(n)
        order += [(n, f"Fig {i}") for i, n in enumerate(seen, 1)]
        for n in seen:
            FIRST_DOC.setdefault(n, name)
    return order


ORDER = _doc_order()


def build(out: Path, figures):
    items = []
    rank, label = {}, {}
    for i, (n, lab) in enumerate(ORDER):
        rank.setdefault(n, i)
        label.setdefault(n, lab)
    for f in sorted(figures, key=lambda f: rank.get(f.name, 99)):
        svg = (out / f"{f.name}.svg").read_text(encoding="utf-8")
        svg = re.sub(r"<\?xml[^>]*\?>\s*", "", svg)
        svg = re.sub(r"<script>.*?</script>", "", svg, flags=re.S)   # viewer supplies its own pan/zoom
        title = f"{label[f.name]} · {f.title}" if f.name in label else f.title
        items.append({"name": f.name, "title": title, "doc": FIRST_DOC.get(f.name, ""), "svg": svg})
    html = TEMPLATE.replace("__FIGS__", json.dumps(items).replace("</", "<\\/"))
    (out / "viewer.html").write_text(html, encoding="utf-8")
