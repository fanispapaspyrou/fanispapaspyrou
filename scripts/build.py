#!/usr/bin/env python3
"""Generate the profile README and its SVG artwork (light and dark).

Standard library only. Run from anywhere:  python3 scripts/build.py
Change USER below after a username rename and run it again.
"""
import math
import pathlib
import random

USER = "fanispapaspyrou"
ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

THEMES = {
    "light": dict(
        bg="#F4F6F3", ink="#1D2A31", muted="#5B6871", contour="#B08260",
        contour_index="#8C5B36", route="#D42A2F", course="#B4317A",
        grid="#CCD5D8", dot="#97A3AA", frame="#C3CDD0",
        slope=["#F3D23C", "#EE8A2C", "#D42A2F", "#8A3F9E"], slope_op=0.62,
    ),
    "dark": dict(
        bg="#132029", ink="#E9EDE7", muted="#9AA8B1", contour="#6E5642",
        contour_index="#9A7758", route="#FF5B54", course="#E46BB0",
        grid="#253642", dot="#5F707B", frame="#2C3F4B",
        slope=["#C9AC2C", "#D4762A", "#D9423C", "#9A5AB5"], slope_op=0.8,
    ),
}

DISPLAY = "'DIN Condensed','Bahnschrift Condensed','Bahnschrift','Roboto Condensed','Arial Narrow',sans-serif"
TEXT = "'Avenir Next','Segoe UI','Helvetica Neue',Arial,sans-serif"


# --------------------------------------------------------------------------- geometry

def gauss(x, y, cx, cy, sx, sy, a, rot=0.0, power=2.0):
    """A hill. rot turns it (degrees); power < 2 makes it sharper, closer to a cone."""
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    u, v = (x - cx) * c + (y - cy) * s, -(x - cx) * s + (y - cy) * c
    return a * math.exp(-((((u / sx) ** 2 + (v / sy) ** 2) / 2) ** (power / 2)))


def sample(f, w, h, step):
    nx, ny = int(w / step) + 2, int(h / step) + 2
    return [[f(i * step, j * step) for i in range(nx)] for j in range(ny)], nx, ny


def marching_squares(grid, nx, ny, step, level):
    """Return contour polylines [(points, closed)] for one level."""
    pts, adj = {}, {}

    def point(key):
        if key not in pts:
            kind, i, j = key
            if kind == "h":
                a, b = grid[j][i], grid[j][i + 1]
                pts[key] = ((i + (level - a) / (b - a)) * step, j * step)
            else:
                a, b = grid[j][i], grid[j + 1][i]
                pts[key] = (i * step, (j + (level - a) / (b - a)) * step)
        return pts[key]

    def link(k1, k2):
        adj.setdefault(k1, []).append(k2)
        adj.setdefault(k2, []).append(k1)

    single = {1: ("L", "B"), 2: ("B", "R"), 3: ("L", "R"), 4: ("T", "R"), 6: ("T", "B"),
              7: ("L", "T"), 8: ("L", "T"), 9: ("T", "B"), 11: ("T", "R"), 12: ("L", "R"),
              13: ("B", "R"), 14: ("L", "B")}
    for j in range(ny - 1):
        for i in range(nx - 1):
            tl, tr = grid[j][i], grid[j][i + 1]
            br, bl = grid[j + 1][i + 1], grid[j + 1][i]
            c = (tl >= level) * 8 + (tr >= level) * 4 + (br >= level) * 2 + (bl >= level)
            if c in (0, 15):
                continue
            e = {"T": ("h", i, j), "B": ("h", i, j + 1), "L": ("v", i, j), "R": ("v", i + 1, j)}
            if c in (5, 10):
                high_centre = (tl + tr + br + bl) / 4 >= level
                if (c == 5) == high_centre:
                    pairs = [("L", "T"), ("B", "R")]
                else:
                    pairs = [("T", "R"), ("L", "B")]
            else:
                pairs = [single[c]]
            for a, b in pairs:
                link(e[a], e[b])

    seen, out = set(), []
    for start in sorted(adj, key=lambda k: len(adj[k])):
        if start in seen:
            continue
        chain, cur = [start], start
        seen.add(start)
        while True:
            nxt = [n for n in adj[cur] if n not in seen]
            if not nxt:
                break
            cur = nxt[0]
            seen.add(cur)
            chain.append(cur)
        closed = len(chain) > 2 and start in adj[chain[-1]]
        out.append(([point(k) for k in chain], closed))
    return out


def simplify(points, eps):
    """Ramer-Douglas-Peucker."""
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        s, e = stack.pop()
        (x1, y1), (x2, y2) = points[s], points[e]
        dx, dy = x2 - x1, y2 - y1
        norm = math.hypot(dx, dy) or 1e-9
        best, idx = 0.0, None
        for k in range(s + 1, e):
            px, py = points[k]
            d = abs(dy * px - dx * py + x2 * y1 - y2 * x1) / norm
            if d > best:
                best, idx = d, k
        if idx is not None and best > eps:
            keep[idx] = True
            stack += [(s, idx), (idx, e)]
    return [p for p, k in zip(points, keep) if k]


def fmt(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def poly_d(points, closed=False):
    d = "M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in points)
    return d + ("Z" if closed else "")


def contour_layer(f, w, h, step, levels, index_every, t, opacity=1.0, eps=0.7):
    grid, nx, ny = sample(f, w, h, step)
    thin, thick = [], []
    for n, level in enumerate(levels):
        for pts, closed in marching_squares(grid, nx, ny, step, level):
            pts = simplify(pts, eps)
            if len(pts) < 3:
                continue
            (thick if n % index_every == index_every - 1 else thin).append(poly_d(pts, closed))
    return (
        f'<g fill="none" stroke-linejoin="round" stroke-linecap="round" opacity="{opacity}">'
        f'<path d="{"".join(thin)}" stroke="{t["contour"]}" stroke-width="1"/>'
        f'<path d="{"".join(thick)}" stroke="{t["contour_index"]}" stroke-width="1.7"/></g>'
    ), grid, nx, ny


def argmax(grid, step):
    best = max((v, i, j) for j, row in enumerate(grid) for i, v in enumerate(row))
    return best[1] * step, best[2] * step


def switchback(start, end, legs, amp):
    """A skin track: zig-zags with rounded kick turns, returns (path d, length)."""
    (sx, sy), (ex, ey) = start, end
    dx, dy = ex - sx, ey - sy
    length = math.hypot(dx, dy)
    px, py = -dy / length, dx / length
    pts = []
    for k in range(legs + 1):
        t = k / legs
        off = 0 if k in (0, legs) else (-1) ** k * amp * (1 - 0.65 * t)
        pts.append((sx + dx * t + px * off, sy + dy * t + py * off))
    mids = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(pts, pts[1:])]
    d = f"M{fmt(pts[0][0])} {fmt(pts[0][1])} L{fmt(mids[0][0])} {fmt(mids[0][1])}"
    samples = [pts[0], mids[0]]
    for k in range(1, legs):
        c, m = pts[k], mids[k]
        d += f" Q{fmt(c[0])} {fmt(c[1])} {fmt(m[0])} {fmt(m[1])}"
        p0 = samples[-1]
        for s in range(1, 9):
            u = s / 8
            samples.append(((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * c[0] + u * u * m[0],
                            (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * c[1] + u * u * m[1]))
    d += f" L{fmt(pts[-1][0])} {fmt(pts[-1][1])}"
    samples.append(pts[-1])
    total = sum(math.dist(a, b) for a, b in zip(samples, samples[1:]))
    return d, total


def summit_marker(x, y, t, label, size=12):
    h = size * 0.9
    return (f'<path d="M{fmt(x)} {fmt(y - h * 0.66)} L{fmt(x + size / 2)} {fmt(y + h / 3)} '
            f'L{fmt(x - size / 2)} {fmt(y + h / 3)}Z" fill="{t["ink"]}"/>'
            f'<text x="{fmt(x + size * 0.9)}" y="{fmt(y + 5)}" class="d halo" font-size="{size * 1.75:.0f}" '
            f'fill="{t["ink"]}">{label}</text>')


def styles(t, extra=""):
    return (f"<style>.d{{font-family:{DISPLAY};font-weight:700}}.t{{font-family:{TEXT}}}"
            f".halo{{paint-order:stroke;stroke:{t['bg']};stroke-width:7px;stroke-linejoin:round}}"
            f"{extra}</style>")


# --------------------------------------------------------------------------- hero

def hero(t):
    W, H = 1200, 420

    def f(x, y):
        return (gauss(x, y, 905, 165, 210, 140, 1.0, -15, 1.15)
                + gauss(x, y, 760, 250, 230, 50, 0.42, -35, 1.4)
                + gauss(x, y, 1060, 95, 170, 48, 0.42, -25, 1.4)
                + gauss(x, y, 1110, 305, 110, 85, 0.5, 20, 1.25)
                + gauss(x, y, 600, 345, 170, 90, 0.24)
                + 0.035 * math.sin(x / 41 + y / 67) + 0.03 * math.sin(x / 23 - y / 37)
                + 0.02 * math.sin((x + y) / 17))

    levels = [0.08 + 0.045 * k for k in range(30)]
    layer, grid, _, _ = contour_layer(f, W, H, 6, levels, 5, t)
    sx, sy = argmax(grid, 6)
    route, length = switchback((660, 440), (sx - 4, sy + 16), 8, 62)
    L = f"{math.ceil(length) + 12}"  # + cap width, so no dot shows before the draw
    css = (f".draw{{stroke-dasharray:{L} {L};stroke-dashoffset:0;"
           f"animation:draw 2.8s cubic-bezier(.45,0,.2,1) .4s both}}"
           f"@keyframes draw{{from{{stroke-dashoffset:{L}}}}}"
           f".pin{{animation:pin .6s ease-out 3.1s both}}"
           f"@keyframes pin{{from{{opacity:0;transform:translateY(-8px)}}}}"
           f"@media (prefers-reduced-motion:reduce){{.draw,.pin{{animation:none}}}}")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="title">
<title id="title">Theofanis Papaspyrou. Tech enthusiast building AI agents and web tools. Management Science and Technology at AUEB, Athens.</title>
{styles(t, css)}
<defs>
<linearGradient id="fg" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="#383838"/><stop offset=".44" stop-color="#424242"/><stop offset=".64" stop-color="#fff"/></linearGradient>
<mask id="fade" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><rect width="{W}" height="{H}" fill="url(#fg)"/></mask>
<mask id="track" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><path class="draw" d="{route}" fill="none" stroke="#fff" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/></mask>
</defs>
<rect width="{W}" height="{H}" fill="{t['bg']}"/>
<g mask="url(#fade)">{layer}</g>
<g mask="url(#track)"><path d="{route}" fill="none" stroke="{t['route']}" stroke-width="3.2" stroke-dasharray="11 7" stroke-linejoin="round"/></g>
<g class="pin">{summit_marker(sx, sy, t, "2918", 14)}</g>
<g fill="{t['ink']}">
<text x="64" y="176" class="d halo" font-size="108" letter-spacing="1">Theofanis</text>
<text x="64" y="276" class="d halo" font-size="108" letter-spacing="1">Papaspyrou</text>
<text x="66" y="334" class="t halo" font-size="27" font-weight="600">Tech enthusiast building AI agents and web tools.</text>
<text x="66" y="370" class="t halo" font-size="22" fill="{t['muted']}">Management Science and Technology at AUEB, Athens</text>
</g>
<rect x="12.5" y="12.5" width="{W - 25}" height="{H - 25}" fill="none" stroke="{t['frame']}"/>
</svg>
"""


# --------------------------------------------------------------------------- project cards

CW, CH, IH = 600, 380, 214  # card size, illustration height


def card(t, title, lines, stack, art, alt):
    body = "".join(
        f'<text x="34" y="{292 + 28 * k}" class="t" font-size="20" fill="{t["ink"]}">{line}</text>'
        for k, line in enumerate(lines))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CW} {CH}" width="{CW}" height="{CH}" role="img" aria-labelledby="title">
<title id="title">{alt}</title>
{styles(t)}
<defs><clipPath id="art"><rect x="1" y="1" width="{CW - 2}" height="{IH}"/></clipPath></defs>
<rect width="{CW}" height="{CH}" fill="{t['bg']}"/>
<g clip-path="url(#art)">{art}</g>
<line x1="1" x2="{CW - 1}" y1="{IH + 0.5}" y2="{IH + 0.5}" stroke="{t['frame']}"/>
<text x="32" y="260" class="d" font-size="{42 if len(title) < 14 else 36}" fill="{t['ink']}">{title}</text>
{body}
<text x="34" y="355" class="t" font-size="16" fill="{t['muted']}">{stack}</text>
<rect x=".5" y=".5" width="{CW - 1}" height="{CH - 1}" fill="none" stroke="{t['frame']}"/>
</svg>
"""


def art_alpenguard(t):
    def f(x, y):
        return (gauss(x, y, 330, 112, 120, 78, 1.0) + gauss(x, y, 480, 55, 85, 55, 0.62)
                + gauss(x, y, 150, 175, 110, 60, 0.36)
                + 0.03 * math.sin(x / 29 + y / 43) + 0.02 * math.sin(x / 17 - y / 23))

    step, scale = 5, 105  # height gradient to tan(slope), tuned so most terrain is 25-45 degrees
    rects = [[] for _ in t["slope"]]
    for j in range(0, IH // step + 1):
        y = j * step
        run_cls, run_x = None, 0
        for i in range(0, CW // step + 2):
            x = i * step
            cx, cy = x + step / 2, y + step / 2
            gx = (f(cx + 1, cy) - f(cx - 1, cy)) / 2
            gy = (f(cx, cy + 1) - f(cx, cy - 1)) / 2
            deg = math.degrees(math.atan(math.hypot(gx, gy) * scale))
            cls = None if deg < 30 else min(3, int((deg - 30) // 5))
            if cls != run_cls:
                if run_cls is not None:
                    rects[run_cls].append(f"M{run_x} {y}h{x - run_x}v{step}h-{x - run_x}Z")
                run_cls, run_x = cls, x
        if run_cls is not None:
            rects[run_cls].append(f"M{run_x} {y}h{CW + step - run_x}v{step}h-{CW + step - run_x}Z")
    slope = "".join(f'<path d="{"".join(r)}" fill="{c}"/>' for r, c in zip(rects, t["slope"]))
    layer, grid, _, _ = contour_layer(f, CW, IH, 5, [0.06 + 0.06 * k for k in range(17)], 5, t)
    sx, sy = argmax(grid, 5)
    route, _ = switchback((90, 230), (sx - 3, sy + 12), 5, 34)
    return (f'<rect width="{CW}" height="{IH}" fill="{t["bg"]}"/>'
            f'<g opacity="{t["slope_op"]}">{slope}</g>{layer}'
            f'<path d="{route}" fill="none" stroke="{t["bg"]}" stroke-width="6" stroke-linejoin="round"/>'
            f'<path d="{route}" fill="none" stroke="{t["route"]}" stroke-width="2.6" stroke-dasharray="9 6"/>'
            f'{summit_marker(sx, sy, t, "", 11)}')


def art_hackscout(t):
    rng = random.Random(11)
    grid = "".join(f"M{x} 0V{IH}" for x in range(30, CW, 60)) + "".join(f"M0 {y}H{CW}" for y in range(17, IH, 60))
    cx, cy = 236, 108
    rings = "".join(
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{t["muted"]}" stroke-width="1.2" '
        f'stroke-dasharray="3 5" opacity="{op}"/>' for r, op in ((48, .9), (96, .65), (144, .4)))
    dots, hits = [], []
    while len(dots) + len(hits) < 52:
        x, y = rng.uniform(18, CW - 18), rng.uniform(16, IH - 16)
        if math.dist((x, y), (cx, cy)) < 20:
            continue
        inside = math.dist((x, y), (cx, cy)) < 140
        if inside and len(hits) < 6 and rng.random() < 0.45:
            hits.append((x, y))
        else:
            dots.append((x, y))
    d = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2"/>' for x, y in dots)
    h = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6"/>' for x, y in hits)
    return (f'<path d="{grid}" stroke="{t["grid"]}" stroke-width="1"/>{rings}'
            f'<g fill="{t["dot"]}">{d}</g>'
            f'<g fill="{t["route"]}" stroke="{t["bg"]}" stroke-width="2.5">{h}</g>'
            f'<path d="M{cx - 9} {cy}h18M{cx} {cy - 9}v18" stroke="{t["ink"]}" stroke-width="2"/>')


def art_agent(t):
    def f(x, y):
        return (gauss(x, y, 420, 40, 160, 90, 0.8) + gauss(x, y, 120, 210, 140, 80, 0.55)
                + 0.04 * math.sin(x / 31 + y / 47) + 0.03 * math.sin(x / 19 - y / 29))

    layer, *_ = contour_layer(f, CW, IH, 6, [0.08 + 0.07 * k for k in range(12)], 5, t, opacity=0.45)
    c = t["course"]
    start = (62, 160)
    controls = [((172, 68), "map_site"), ((300, 148), "scrape_page"),
                ((410, 60), "web_search"), ((468, 166), "validate")]
    finish = (548, 92)
    nodes = [start] + [p for p, _ in controls] + [finish]
    radius = [17] + [16] * len(controls) + [17]
    legs = ""
    for (a, ra), (b, rb) in zip(zip(nodes, radius), zip(nodes[1:], radius[1:])):
        d = math.dist(a, b)
        ux, uy = (b[0] - a[0]) / d, (b[1] - a[1]) / d
        legs += f"M{a[0] + ux * ra:.1f} {a[1] + uy * ra:.1f}L{b[0] - ux * rb:.1f} {b[1] - uy * rb:.1f}"
    s = 30
    tri = (f"M{start[0]} {start[1] - s * 0.6}L{start[0] + s / 2} {start[1] + s * 0.3}"
           f"L{start[0] - s / 2} {start[1] + s * 0.3}Z")
    circles = "".join(f'<circle cx="{x}" cy="{y}" r="16"/>' for (x, y), _ in controls)
    labels = "".join(
        f'<text x="{x + 20}" y="{y - 14}" class="d halo" font-size="24" fill="{c}">{n}</text>'
        f'<text x="{x}" y="{y + 36}" class="t halo" font-size="14" fill="{t["muted"]}" text-anchor="middle">{name}</text>'
        for n, ((x, y), name) in enumerate(controls, 1))
    fin = (f'<circle cx="{finish[0]}" cy="{finish[1]}" r="17"/><circle cx="{finish[0]}" cy="{finish[1]}" r="11"/>'
           f'<text x="{finish[0]}" y="{finish[1] + 38}" class="t halo" font-size="14" fill="{t["muted"]}" '
           f'text-anchor="middle" stroke-width="7">profile</text>')
    return (f'<rect width="{CW}" height="{IH}" fill="{t["bg"]}"/>{layer}'
            f'<g fill="none" stroke="{c}" stroke-width="2.6"><path d="{legs}{tri}"/>{circles}{fin}</g>{labels}')


def art_subtrack(t):
    x0, x1, y = 46, 554, 128
    seg = (x1 - x0) / 12
    bar = "".join(
        f'<rect x="{x0 + k * seg:.1f}" y="{y}" width="{seg:.1f}" height="9" '
        f'fill="{t["ink"] if k % 2 == 0 else t["bg"]}"/>' for k in range(12))
    months = "".join(
        f'<text x="{x0 + (k + 0.5) * seg:.1f}" y="{y + 34}" class="t" font-size="14" '
        f'fill="{t["muted"]}" text-anchor="middle">{m}</text>' for k, m in enumerate("JFMAMJJASOND"))
    marks = [(0.9, "€9.99", 62), (2.4, "€4.99", 88), (4.1, "€11.99", 52), (6.9, "€9.99", 78), (9.6, "€29", 58)]
    stems = "".join(
        f'<path d="M{x0 + m * seg:.1f} {top}V{y - 4}" stroke="{t["ink"]}" stroke-width="1.6"/>'
        f'<path d="M{x0 + m * seg - 5:.1f} {y - 10}h10l-5 7z" fill="{t["ink"]}"/>'
        f'<text x="{x0 + m * seg + 7:.1f}" y="{top + 11}" class="t" font-size="15" fill="{t["ink"]}">{label}</text>'
        for m, label, top in marks)
    tx = x0 + 8.15 * seg
    trial = (f'<path d="M{tx:.1f} 34V{y - 4}" stroke="{t["route"]}" stroke-width="2.2"/>'
             f'<path d="M{tx - 6:.1f} {y - 11}h12l-6 8z" fill="{t["route"]}"/>'
             f'<text x="{tx + 8:.1f}" y="46" class="t" font-size="15" font-weight="600" fill="{t["route"]}">trial ends in 3 days</text>')
    return (f'<rect width="{CW}" height="{IH}" fill="{t["bg"]}"/>{stems}{trial}'
            f'<g stroke="{t["ink"]}" stroke-width="1.4">{bar}</g>{months}')


PROJECTS = [
    dict(slug="hackscout", title="hackscout", art=art_hackscout,
         lines=["Daily scout for hackathons and tech events.",
                "Filters them by my criteria, alerts me on Telegram."],
         stack="TypeScript, Claude, Cloudflare Workers, Turso, Telegram"),
    dict(slug="alpenguard", title="alpenguard", art=art_alpenguard,
         lines=["Avalanche safety map for ski touring with the",
                "bulletin, slope angles and trip reports in 3D."],
         stack="TypeScript, React, Three.js, MapLibre, Vite"),
    dict(slug="company_lookup_agent", title="company_lookup_agent", art=art_agent,
         lines=["Researches a company from its URL and writes a",
                "sourced profile. Hand-written tool-calling loop."],
         stack="Python, Gemini, Firecrawl, Pydantic, Streamlit"),
    dict(slug="subtrack", title="subtrack", art=art_subtrack,
         lines=["Command-line tracker for subscriptions,",
                "renewal dates and free trials. Tested in CI."],
         stack="Python, pytest, GitHub Actions"),
]


# --------------------------------------------------------------------------- README

def picture(name, alt, width=None):
    w = f' width="{width}"' if width else ""
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/{name}-dark.svg">'
            f'<img src="assets/{name}-light.svg" alt="{alt}"{w}></picture>')


def readme():
    cards = []
    for p in PROJECTS:
        alt = f"{p['title']}: {' '.join(p['lines'])} Built with {p['stack']}."
        cards.append(f'<a href="https://github.com/{USER}/{p["slug"]}">{picture(p["slug"], alt, "49%")}</a>')
    grid = f"<p>\n{cards[0]}\n{cards[1]}\n</p>\n<p>\n{cards[2]}\n{cards[3]}\n</p>"
    hero_alt = ("Theofanis Papaspyrou. Tech enthusiast building AI agents and web tools. "
                "A contour map with a ski-touring track climbing to a summit.")
    return f"""{picture("hero", hero_alt)}

I'm Fanis, a tech enthusiast in my first year of Management Science and Technology at AUEB in Athens. I learn by building: small AI agents and web tools in Python and TypeScript, usually for a problem I actually have. Long term, I want to start a company.

### Projects

{grid}

alpenguard runs live at [alpenguard-theta.vercel.app](https://alpenguard-theta.vercel.app).

### What I build with

- **Python** for agents, command-line tools and Streamlit apps
- **TypeScript and React** with Vite, Tailwind, GSAP, Three.js and MapLibre
- **AI tooling:** Claude Code, Gemini function calling, MCP, Firecrawl
- **Shipping:** GitHub Actions, Cloudflare Workers, Vercel

### Away from the keyboard

- Led my school's CanSat team in 2024. We designed, built and launched a can-sized satellite prototype in the Greek national competition.
- Skiing every winter since ski academy as a kid, which is where alpenguard came from. I also run: 5 km in 20:40.
- On the sponsors team at FSDET, the DMST student conference.

Right now I'm working through CS50x and went to my first hackathon in November 2026. I'm looking for teammates for the next ones: find me on [LinkedIn](https://www.linkedin.com/in/fanis-papaspyrou).
"""


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    for name, t in THEMES.items():
        (ASSETS / f"hero-{name}.svg").write_text(hero(t), encoding="utf-8")
        for p in PROJECTS:
            alt = f"{p['title']}: {' '.join(p['lines'])}"
            svg = card(t, p["title"], p["lines"], p["stack"], p["art"](t), alt)
            (ASSETS / f"{p['slug']}-{name}.svg").write_text(svg, encoding="utf-8")
    (ROOT / "README.md").write_text(readme(), encoding="utf-8")
    for f in sorted(ASSETS.iterdir()):
        print(f"{f.name:34} {f.stat().st_size / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
