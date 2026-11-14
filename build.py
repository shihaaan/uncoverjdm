import re, math, html
from cars import CARS, LINEAGE, HALLS

S = 0.2; X0 = 120; G = 400
def X(x): return round(X0 + x * S, 1)
def Y(h): return round(G - h * S, 1)

def path(d):
    """Convert a mm path (x,h pairs) to px."""
    out = []
    for tok in re.findall(r'[MLQCZ]|-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?', d):
        if tok in 'MLQCZ': out.append(tok)
        else:
            x, h = tok.split(','); out.append(f"{X(float(x))},{Y(float(h))}")
    return ' '.join(out)


def _flatten(d):
    """mm path -> list of (points, closed) per subpath."""
    toks = re.findall(r'[MLQCZ]|-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?', d)
    subs = []; cur = None; i = 0
    def pt(t): x, h = t.split(','); return (float(x), float(h))
    while i < len(toks):
        t = toks[i]
        if t == 'M': cur = [pt(toks[i+1])]; subs.append([cur, False]); i += 2
        elif t == 'L': cur.append(pt(toks[i+1])); i += 2
        elif t == 'Q':
            p0 = cur[-1]; c1 = pt(toks[i+1]); p1 = pt(toks[i+2])
            for k in range(1, 25):
                u = k / 24
                cur.append(((1-u)**2*p0[0] + 2*(1-u)*u*c1[0] + u*u*p1[0], (1-u)**2*p0[1] + 2*(1-u)*u*c1[1] + u*u*p1[1]))
            i += 3
        elif t == 'Z': subs[-1][1] = True; i += 1
        else: cur.append(pt(t)); i += 1
    return subs

def _resample(pts, step):
    out = [pts[0]]; carry = 0.0
    for a, bb in zip(pts, pts[1:]):
        seg = math.hypot(bb[0]-a[0], bb[1]-a[1])
        if seg == 0: continue
        dd = step - carry
        while dd <= seg:
            out.append((a[0] + (bb[0]-a[0])*dd/seg, a[1] + (bb[1]-a[1])*dd/seg)); dd += step
        carry = seg - (dd - step)
    if math.hypot(out[-1][0]-pts[-1][0], out[-1][1]-pts[-1][1]) > 1e-6: out.append(pts[-1])
    return out

def smooth(d, sigma, step=20.0):
    """Round every corner of a mm path with a Gaussian filter; returns a px path."""
    res = []
    for pts, closed in _flatten(d):
        if closed: pts = pts + [pts[0]]
        total = sum(math.hypot(q[0]-p[0], q[1]-p[1]) for p, q in zip(pts, pts[1:]))
        sg = min(sigma, total / 14.0); st = min(step, max(total / 60.0, 4.0))
        P = _resample(pts, st); n = len(P)
        if closed: P = P[:-1]; n = len(P)
        w = int(3 * sg / st) + 1
        ker = [math.exp(-0.5 * (k * st / sg) ** 2) for k in range(-w, w + 1)]; ks = sum(ker)
        out = []
        for i in range(n):
            sx = sy = 0.0
            for k in range(-w, w + 1):
                j = i + k
                j = j % n if closed else min(max(j, 0), n - 1)
                sx += P[j][0] * ker[k + w]; sy += P[j][1] * ker[k + w]
            out.append((sx / ks, sy / ks))
        if not closed: out[0] = P[0]; out[-1] = P[-1]
        s = 'M' + ' L'.join(f'{X(x)},{Y(h)}' for x, h in out)
        res.append(s + (' Z' if closed else ''))
    return ' '.join(res)

def wheel(cx, c):
    r = c['rt'] * S; cy = G - r
    rim = r * 0.64
    o = [f'<circle class="ln" cx="{cx}" cy="{cy}" r="{r:.1f}"/>',
         f'<circle class="ln-thin" cx="{cx}" cy="{cy}" r="{rim:.1f}"/>',
         f'<circle class="ln-thin" cx="{cx}" cy="{cy}" r="{r*0.14:.1f}"/>']
    n = {'steel': 8, 's5': 5, 's6': 6}[c['wheel']]
    if c['wheel'] == 'steel':
        o.append(f'<circle class="ln-thin" cx="{cx}" cy="{cy}" r="{rim*0.85:.1f}"/>')
    segs = []
    for i in range(n):
        a = -math.pi / 2 + i * 2 * math.pi / n
        for da in ((0,) if c['wheel'] == 'steel' else (-0.11, 0.11)):
            x1 = cx + math.cos(a + da * 2.2) * r * 0.16; y1 = cy + math.sin(a + da * 2.2) * r * 0.16
            x2 = cx + math.cos(a + da) * rim * (0.85 if c['wheel'] == 'steel' else 0.98)
            y2 = cy + math.sin(a + da) * rim * (0.85 if c['wheel'] == 'steel' else 0.98)
            segs.append(f'M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}')
    o.append(f'<path class="ln-thin" d="{" ".join(segs)}"/>')
    return ''.join(o)

def geom(c):
    fx = X(c['foh']); rx = X(c['foh'] + c['wb'])
    ra = c['ra'] * S; cy = G - c['rt'] * S; sy = Y(c['hs'])
    dx = math.sqrt(max(ra * ra - (sy - cy) ** 2, 1))
    return fx, rx, ra, cy, sy, dx

def car_group(c):
    fx, rx, ra, cy, sy, dx = geom(c)
    body = smooth(c['top'], c.get('sig', 95)) + f' L{rx+dx:.1f},{sy} A{ra:.1f},{ra:.1f} 0 1 0 {rx-dx:.1f},{sy} L{fx+dx:.1f},{sy} A{ra:.1f},{ra:.1f} 0 1 0 {fx-dx:.1f},{sy} Z'
    o = [f'<g id="d-{c["id"]}">', f'<path class="ln body-line" pathLength="1" d="{body}"/>']
    for g in c['glass']: o.append(f'<path class="ln-thin" d="{smooth(g, 42)}"/>')
    for l in c['lines']: o.append(f'<path class="ln-thin" d="{smooth(l, 26)}"/>')
    for w in c.get('over', []):
        wx = fx if w == 'front' else rx; r2 = ra + 9; d2 = math.sqrt(r2 * r2 - (sy - 6 - cy) ** 2)
        o.append(f'<path class="ln-thin" d="M{wx-d2:.1f},{sy-6} A{r2:.1f},{r2:.1f} 0 1 1 {wx+d2:.1f},{sy-6}"/>')
    o.append(wheel(fx, c)); o.append(wheel(rx, c)); o.append('</g>')
    return ''.join(o)

def drawing(c):
    fx, rx, ra, cy, sy, dx = geom(c)
    xe = X(c['L']); ry = Y(c['H']); vw = xe + 110 - 40
    o = [f'<svg viewBox="40 26 {vw:.0f} 474" role="img" aria-label="{html.escape(c["subject"])} ({c["chassis"]}), side elevation line drawing with dimensions: length {c["L"]:,} mm, wheelbase {c["wb"]:,} mm, height {c["H"]:,} mm.">']
    o.append(f'<line class="ln-thin" x1="60" y1="{G}" x2="{xe+74}" y2="{G}"/>')
    o.append(f'<line class="ln-centre" x1="{fx}" y1="250" x2="{fx}" y2="462"/><line class="ln-centre" x1="{rx}" y1="250" x2="{rx}" y2="462"/>')
    for (x, h, w, hh) in c['hidden']:
        o.append(f'<rect class="ln-hidden" x="{X(x)}" y="{Y(h)}" width="{w*S:.0f}" height="{hh*S:.0f}" rx="3"/>')
    o.append(f'<use href="#d-{c["id"]}"/>')
    o.append(f'<path class="dm" d="M{X0},410 V486 M{xe},410 V486"/>')
    o.append(f'<line class="dm" x1="{fx}" y1="456" x2="{rx}" y2="456" marker-start="url(#arr)" marker-end="url(#arr)"/>')
    o.append(f'<text class="dm-text" x="{(fx+rx)/2:.0f}" y="450" text-anchor="middle">WHEELBASE {c["wb"]:,}</text>')
    o.append(f'<line class="dm" x1="{X0}" y1="480" x2="{xe}" y2="480" marker-start="url(#arr)" marker-end="url(#arr)"/>')
    o.append(f'<text class="dm-text" x="{(X0+xe)/2+24:.0f}" y="474" text-anchor="middle">OVERALL LENGTH {c["L"]:,}</text>')
    hx = xe + 56
    o.append(f'<path class="dm" d="M{X(c["L"]*0.62)},{ry} H{hx+10} M{xe+14},{G} H{hx+10}"/>')
    o.append(f'<line class="dm" x1="{hx}" y1="{ry}" x2="{hx}" y2="{G}" marker-start="url(#arr)" marker-end="url(#arr)"/>')
    my = (ry + G) / 2
    o.append(f'<text class="dm-text" x="{hx-6}" y="{my:.0f}" text-anchor="middle" transform="rotate(-90 {hx-6} {my:.0f})">HEIGHT {c["H"]:,}</text>')
    for i, (t, txt, tx, th, lx, row) in enumerate(c['call']):
        px, py = X(tx), Y(th); qx = X(lx)
        if row == 9:   # label below the sill line or beside the nose
            qy = py - 50 if lx < 0 else 425
        else:
            qy = ry - 34 - row * 30
        ang = math.atan2(py - qy, px - qx); ex = qx + math.cos(ang) * 12; ey = qy + math.sin(ang) * 12
        o.append(f'<g class="tag"><path class="lead" d="M{px},{py} L{ex:.1f},{ey:.1f}"/><circle cx="{qx}" cy="{qy:.1f}" r="12"/><text x="{qx}" y="{qy+4:.1f}">{i+1}</text></g>')
    o.append('</svg>')
    return ''.join(o)

def thumb(c):
    xe = X(c['L'])
    return f'<svg viewBox="90 90 {xe-60:.0f} 330" role="img" aria-label="Line drawing of the {html.escape(c["short"])}"><line class="ln-thin" x1="90" y1="{G}" x2="{xe+30}" y2="{G}"/><use href="#d-{c["id"]}"/></svg>'

e = html.escape
def yrs(c):
    a, b = c['years']; return str(a) if a == b else f'{a} to {b}'

def exhibit(c, i):
    n = f'{i+1:03d}'
    prev = CARS[i - 1]; nxt = CARS[(i + 1) % len(CARS)]
    call = ''.join(f'<li><span class="n">{k+1}</span><div><b>{e(t)}</b><span class="t">{e(txt)}</span></div></li>' for k, (t, txt, *_) in enumerate(c['call']))
    story = ''.join(f'<p>{e(p)}</p>' for p in c['story'])
    spec = ''.join(f'<tr><th scope="row">{e(a)}</th><td>{e(b)}</td></tr>' for a, b in c['spec'])
    rec = ''.join(f'<article><span class="mono">{e(d)}</span><h3>{e(t)}</h3><p>{e(x)}</p></article>' for d, t, x in c['rec'])
    lin = ''
    for (y, nm, code, cid) in (c.get('lin') or LINEAGE[c['hall']]):
        here = (cid == c['id']) or (code == 'Drawn here')
        inner = f'<span class="mono">{y}</span><b>{e(nm)}</b>' + (f'<span class="mono">{e(code)}</span>' if code else '')
        if cid and cid != c['id']: lin += f'<a class="lin" href="#{cid}">{inner}</a>'
        else: lin += f'<div class="lin{" here" if here else ""}">{inner}</div>'
    src = ''.join(f'<li><a href="{e(u)}">{e(t)}</a></li>' for t, u in c['src'])
    meta = ''.join(f'<span>{e(m)}</span>' for m in c['meta'])
    return f'''
<main id="view-{c["id"]}" data-view="{c["id"]}">
  <div class="ex-head">
    <div>
      <div class="mono">Exhibit {n} · {e(c["hall"])} hall</div>
      <h1{' lang="ja"' if c.get("ja") else ''}>{c["big"]}</h1>
      <p class="sub">{c["sub"]}</p>
    </div>
    <div class="ex-meta mono">{meta}</div>
  </div>
  <div class="drawing">
    <div class="drawing-scroll">{drawing(c)}</div>
    <div class="titleblock mono">
      <div>Drawing<b>UJ-{n} / Sheet 1 of 1</b></div>
      <div>Subject<b>{e(c["subject"])}</b></div>
      <div>Chassis<b>{e(c["chassis"])}</b></div>
      <div>Figures from<b>{e(c["figs"])}</b></div>
      <div>View<b>Side elevation, mm</b></div>
      <div>Status<b>Illustration, not to scale</b></div>
    </div>
  </div>
  <section>
    <div class="section-head"><span class="mono">Key to the drawing</span><h2>{e(c["call_h"])}</h2></div>
    <ol class="callouts">{call}</ol>
  </section>
  <section>
    <div class="two">
      <div class="stack">
        <div class="section-head"><span class="mono">The story</span><h2>{e(c["story_h"])}</h2></div>
        {story}
      </div>
      <table class="spec"><caption class="mono">Specification · {e(c["spec_cap"])}</caption><tbody>{spec}</tbody></table>
    </div>
  </section>
  <section>
    <div class="section-head"><span class="mono">{e(c["rec_tag"])}</span><h2>{e(c["rec_h"])}</h2></div>
    <div class="two" style="align-items:center">
      <div class="record">{rec}</div>
      <div><div class="big50 num">{e(c["bignum"])}</div><p class="mono" style="margin-top:8px">{e(c["bigcap"])}</p></div>
    </div>
  </section>
  <section>
    <div class="section-head"><span class="mono">Lineage</span><h2>Where it sits in the family</h2></div>
    <div class="lineage">{lin}</div>
    <p style="margin-top:18px">{e(c["close"])}</p>
  </section>
  <nav class="pager" aria-label="Exhibits">
    <a href="#{prev["id"]}"><span class="mono">← Previous</span><b>{e(prev["short"])}</b></a>
    <a href="#home"><span class="mono">Index</span><b>All exhibits</b></a>
    <a href="#{nxt["id"]}" class="r"><span class="mono">Next →</span><b>{e(nxt["short"])}</b></a>
  </nav>
  <footer>
    <span class="mono">Sources</span><ul>{src}</ul>
    <p>Drawings are original illustrations made for this site. They are not manufacturer drawings and are not dimensionally exact. Uncover JDM is a fan project with no link to any carmaker.</p>
    <p class="credit">Made by <a href="https://shihaaan.github.io/portfolio/">Shihan</a> · Part of The Uncover Project</p>
  </footer>
</main>'''

def home():
    halls = ''
    for h in HALLS:
        cards = ''
        for i, c in enumerate(CARS):
            if c['hall'] != h: continue
            cards += f'''<a class="card" href="#{c["id"]}"><div class="card-art">{thumb(c)}</div><div class="card-foot"><span class="mono">{i+1:03d} · {yrs(c)}</span><strong>{e(c["short"])}</strong></div></a>'''
        halls += f'<div class="hallrow"><h3>{e(h)}</h3><div class="cards">{cards}</div></div>'
    tl = ''
    for h in HALLS:
        tl += f'<div class="mono tl-group">{e(h)}</div>'
        for c in CARS:
            if c['hall'] != h: continue
            a, b = c['years']
            tl += f'<a class="tl-row" href="#{c["id"]}"><span class="name">{e(c["short"])}</span><div class="tl-track"><div class="tl-bar on" style="--s:{a};--e:{b}" title="{yrs(c)}"></div></div></a>'
    axis = ''.join(f'<span style="--y:{y}">{y}</span>' for y in (1965, 1975, 1985, 1995, 2005, 2015))
    f = CARS[0]
    return f'''
<main id="view-home" data-view="home">
  <div class="hero">
    <h1>Japan's legends, <em>on the drawing board.</em></h1>
    <div class="stack">
      <p class="lede">A museum of the cars Japan built for itself. Each exhibit is one drawing sheet: the shape, the numbers, and the story of why the car still matters.</p>
      <p class="mono">Fifteen exhibits · Six halls · Part of The Uncover Project</p>
    </div>
  </div>
  <a class="feature" href="#{f["id"]}" aria-label="Open exhibit 001, the Hakosuka">
    <div class="feature-body">{thumb(f)}</div>
    <div class="feature-foot">
      <div><div class="mono">Exhibit 001 · Skyline hall · 1969 to 1972</div><strong>ハコスカ Hakosuka, the first GT-R</strong></div>
      <span class="go">Start the tour →</span>
    </div>
  </a>
  <section>
    <div class="section-head"><span class="mono">Floor plan</span><h2>Six halls, fifteen drawings</h2></div>
    {halls}
  </section>
  <section>
    <div class="section-head"><span class="mono">Production years</span><h2>Half a century on one line</h2></div>
    <div class="timeline">{tl}
      <div class="tl-row"><span></span><div class="tl-axis">{axis}</div></div>
    </div>
  </section>
  <footer><p>Drawings are original illustrations made for this site. Sources are listed at the foot of each exhibit. Uncover JDM is a fan project with no link to any carmaker.</p><p class="credit">Made by <a href="https://shihaaan.github.io/portfolio/">Shihan</a> · Part of The Uncover Project</p></footer>
</main>'''

import os
if not os.path.exists('base.css'):
    old = open('index.html', encoding='utf-8').read()
    open('base.css', 'w', encoding='utf-8').write(old[old.index('<style>') + 7: old.index('</style>')])
css = open('base.css', encoding='utf-8').read()
css += '''
.hallrow { margin-top: 28px; display: flex; flex-direction: column; gap: 12px; }
.hallrow:first-of-type { margin-top: 0; }
.hallrow h3 { font-family: var(--font-display); font-size: 19px; }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 14px; }
.card { display: flex; flex-direction: column; border: 1px solid var(--line-faint); background: var(--sheet-deep); text-decoration: none; transition: border-color 0.2s; }
.card:hover { border-color: var(--dim); }
.card-art { padding: 10px 12px 2px; }
.card-art svg, .feature-body svg { display: block; width: 100%; height: auto; }
.card .body-line, .feature .body-line { animation: none; stroke-dasharray: none; }
.card-foot { border-top: 1px solid var(--line-faint); padding: 10px 12px; display: flex; flex-direction: column; gap: 2px; }
.card-foot strong { font-family: var(--font-display); font-weight: 400; font-size: 16px; }
a.tl-row { text-decoration: none; }
a.tl-row:hover .name { color: var(--dim); }
a.lin, div.lin { border: 1px solid var(--line-faint); padding: 10px 14px; display: flex; flex-direction: column; gap: 2px; min-width: 112px; flex: 1; text-decoration: none; }
a.lin:hover { border-color: var(--line-soft); }
.lin.here { border-color: var(--dim); }
.lin b { font-family: var(--font-display); font-weight: 400; font-size: 17px; }
.pager { margin-top: clamp(40px, 6vw, 72px); display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.pager a { border: 1px solid var(--line-faint); padding: 12px 14px; text-decoration: none; display: flex; flex-direction: column; gap: 2px; }
.pager a:hover { border-color: var(--dim); }
.pager a.r { text-align: right; }
.pager b { font-family: var(--font-display); font-weight: 400; font-size: 15px; }
.ex-head h1:not([lang]) { letter-spacing: 0.01em; }
.big50 { font-size: clamp(64px, 11vw, 150px); }
footer { margin-top: 28px; }
.credit { color: var(--line); font-family: var(--font-mono); font-size: 12px; letter-spacing: 0.1em; text-transform: uppercase; margin-top: 6px; }
.credit a { color: var(--dim); }
@media (max-width: 560px) { .pager { grid-template-columns: minmax(0, 1fr); } .pager a.r { text-align: left; } }
'''
css = css.replace('.lineage div { border: 1px solid var(--line-faint); padding: 10px 14px; display: flex; flex-direction: column; gap: 2px; min-width: 130px; flex: 1; }\n', '')
css = css.replace('.lineage div.here { border-color: var(--dim); }\n', '').replace('.lineage b { font-family: var(--font-display); font-weight: 400; font-size: 17px; }\n', '')

FAVICON = open('favicon.txt').read().strip()
defs = ''.join(car_group(c) for c in CARS)
page = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Uncover JDM</title>
<link rel="icon" type="image/jpeg" href="{FAVICON}">
<link rel="apple-touch-icon" href="{FAVICON}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Dela+Gothic+One&family=IBM+Plex+Mono:wght@400;500&family=Zen+Kaku+Gothic+New:wght@400;500;700&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs>
<marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,1.5 L9,5 L0,8.5" fill="none" stroke="#f3c552" stroke-width="1.2"/></marker>
{defs}</defs></svg>
<div class="sheet"><div class="frame">
<header class="top">
  <a class="brand" href="#home">UNCOVER <span>JDM</span></a>
  <nav aria-label="Site">
    <a href="#home" data-nav="home">Index</a>
    <a href="#hakosuka" data-nav="tour">Start the tour</a>
  </nav>
</header>
{home()}
{''.join(exhibit(c, i) for i, c in enumerate(CARS))}
</div></div>
<script>
(function () {{
  var views = document.querySelectorAll('[data-view]');
  function show() {{
    var name = (location.hash || '').replace('#', '');
    var found = false;
    views.forEach(function (v) {{ if (v.dataset.view === name) found = true; }});
    if (!found) name = 'home';
    views.forEach(function (v) {{ v.hidden = v.dataset.view !== name; }});
    var nav = document.querySelector('[data-nav="home"]');
    if (name === 'home') nav.setAttribute('aria-current', 'page'); else nav.removeAttribute('aria-current');
    window.scrollTo(0, 0);
  }}
  window.addEventListener('hashchange', show);
  show();
}})();
</script>
</body>
</html>
'''
open('index.html', 'w', encoding='utf-8').write(page)
print(len(page))
