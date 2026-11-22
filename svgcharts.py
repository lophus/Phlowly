"""Static SVG charts for printed reports: light theme, crisp, no JavaScript, no dependencies.

Everything returns an SVG (or small HTML) string that scales to the width of its container,
so a report always fits the page. Layouts avoid flexbox/grid on purpose: tables and inline
blocks print the same in every browser.
"""
import math
from html import escape

INK, MUTED, GRID, AXIS = "#1D232B", "#5B6571", "#E3E7EC", "#AEB7C1"
FONT = "Inter, 'Helvetica Neue', Arial, sans-serif"
# darker than the on-screen palette so colours keep their contrast on paper
PAL = ["#4F77A8", "#4E8F6D", "#B58A3C", "#B05A5A", "#7A6FA6", "#4E9096", "#B8744A", "#7F9462", "#6B7785", "#98708F"]
INCOME, EXPENSE, NETWORTH, GOLD, TEAL, PURPLE = "#4E8F6D", "#B05A5A", "#4F77A8", "#B58A3C", "#4E9096", "#7A6FA6"
CUR = "€"


def esc(s) -> str:
    return escape(str(s)).replace("$", "&#36;")


def money(x, dec=2, sign=False, sym=None) -> str:
    sym = CUR if sym is None else sym
    sym = sym + (" " if len(sym) > 1 else "")
    x = round(float(x), dec)
    x = 0.0 if x == 0 else x          # no "-€0.00" from float noise
    pre = "-" if x < 0 else ("+" if sign and x > 0 else "")
    return f"{pre}{sym}{abs(x):,.{dec}f}"


def axis_money(v: float) -> str:
    a = abs(v)
    if a >= 1e6:
        s = f"{round(v / 1e6, 2):g}M"
    elif a >= 1e3:
        s = f"{round(v / 1e3, 1):g}k"
    else:
        s = f"{round(abs(v), 2):g}"
    if a >= 1e6:
        s = f"{round(a / 1e6, 2):g}M"
    elif a >= 1e3:
        s = f"{round(a / 1e3, 1):g}k"
    return f"{'-' if v < 0 else ''}{CUR}{s}"


def nice_ticks(lo: float, hi: float, n: int = 5):
    if hi <= lo:
        hi = lo + 1.0
    step0 = (hi - lo) / max(n, 1)
    mag = 10 ** math.floor(math.log10(step0))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= step0)
    v = math.floor(lo / step) * step
    ticks = []
    while v <= math.ceil(hi / step) * step + step * 1e-9:
        ticks.append(round(v, 10))
        v += step
    return ticks


def _text(x, y, s, size=10, fill=MUTED, anchor="start", weight=400, extra=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}" {extra}>{esc(s)}</text>')


def _legend_rows(items, x0, max_x, size=10):
    """Lay the legend out on as many rows as needed. Returns [[(item, x), ...], ...]."""
    rows, cur, cx = [], [], x0
    for it in items:
        w = (16 if it[2] == "box" else 19) + len(str(it[0])) * size * 0.56 + 14
        if cur and cx + w > max_x:
            rows.append(cur)
            cur, cx = [], x0
        cur.append((it, cx))
        cx += w
    if cur:
        rows.append(cur)
    return rows


def _legend(items, x, y, size=10, max_x=None, row_h=14):
    """items: (name, color, kind) with kind 'box' | 'line' | 'dash'. Returns (svg, rows)."""
    rows = _legend_rows(items, x, max_x if max_x else 10 ** 9, size)
    out = []
    for r, row in enumerate(rows):
        yy = y + r * row_h
        for (name, color, kind), cx in row:
            if kind == "box":
                out.append(f'<rect x="{cx:.1f}" y="{yy - 8:.1f}" width="9" height="9" rx="2" fill="{color}"/>')
            else:
                dash = ' stroke-dasharray="3 2"' if kind == "dash" else ""
                out.append(f'<line x1="{cx:.1f}" y1="{yy - 3.5:.1f}" x2="{cx + 12:.1f}" y2="{yy - 3.5:.1f}" '
                           f'stroke="{color}" stroke-width="2"{dash}/>')
            out.append(_text(cx + (16 if kind == "box" else 19), yy, name, size, INK))
    return "".join(out), max(len(rows), 1)


class XY:
    """Categorical x axis with bars, lines, bands and reference lines on up to two y axes."""

    def __init__(self, labels, width=720, height=250, y_fmt=axis_money, y2_fmt=axis_money, max_labels=None,
                 zero=True, pad_left=58, pad_right=14):
        self.labels, self.W, self.H = list(labels), width, height
        self.y_fmt, self.y2_fmt, self.max_labels, self.zero = y_fmt, y2_fmt, max_labels, zero
        self.l, self.r, self.t, self.b = pad_left, pad_right, 26, 28
        self.layers, self.legend = [], []

    # --- layers
    def bars(self, series):
        """series: [(name, values, color)] drawn side by side."""
        self.layers.append(("bars", series, "l"))
        self.legend += [(n, c, "box") for n, _, c in series]
        return self

    def line(self, name, values, color, dash=False, area=False, axis="l", markers=None, width=2.0, legend=True):
        self.layers.append(("line", (name, values, color, dash, area, markers, width), axis))
        if legend:
            self.legend.append((name, color, "dash" if dash else "line"))
        if axis == "r":
            self.r = max(self.r, 56)
        return self

    def band(self, lo, hi, color, opacity=0.14, name=None, axis="l"):
        self.layers.append(("band", (lo, hi, color, opacity), axis))
        if name:
            self.legend.append((name, color, "box"))
        return self

    def vmark(self, i, label="", color=MUTED):
        self.layers.append(("vmark", (i, label, color), "l"))
        return self

    def hline(self, y, label, color=MUTED, dash=True, axis="l"):
        self.layers.append(("hline", (y, label, color, dash), axis))
        return self

    # --- scales
    def _range(self, axis):
        vals = []
        for kind, data, ax in self.layers:
            if ax != axis:
                continue
            if kind == "bars":
                vals += [v for _, vs, _ in data for v in vs if v is not None]
            elif kind == "line":
                vals += [v for v in data[1] if v is not None]
            elif kind == "band":
                vals += [v for v in list(data[0]) + list(data[1]) if v is not None]
            elif kind == "hline":
                vals.append(data[0])
        if not vals:
            return None
        lo, hi = min(vals), max(vals)
        if self.zero or any(k == "bars" and a == axis for k, _, a in self.layers):
            lo, hi = min(lo, 0.0), max(hi, 0.0)
        if lo == hi:
            hi = lo + 1.0
        ticks = nice_ticks(lo, hi, 5)
        return ticks[0], ticks[-1], ticks

    def render(self, legend=True) -> str:
        W, H, n = self.W, self.H, max(len(self.labels), 1)
        L, R, T, B = self.l, self.r, self.t, self.b
        legend_rows = 1
        if legend and self.legend:
            legend_rows = len(_legend_rows(self.legend, L, W - R))
            T += 14 * (legend_rows - 1)
        pw, ph = W - L - R, H - T - B
        if self.max_labels is None:                      # as many labels as fit without touching
            longest = max([len(str(x)) for x in self.labels if x] or [1])
            self.max_labels = max(2, int(pw / (longest * 5.6 + 12)))
        out = [f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" '
               f'style="display:block;max-width:100%">']
        ranges = {a: self._range(a) for a in ("l", "r")}

        def Y(v, ax="l"):
            lo, hi, _ = ranges[ax]
            return T + (1 - (v - lo) / (hi - lo)) * ph

        def X(i):
            return L + (i + 0.5) * pw / n

        if legend and self.legend:
            svg, _ = _legend(self.legend, L, 12, max_x=W - R)
            out.append(svg)
        if ranges["l"]:                                   # grid + left axis
            lo, hi, ticks = ranges["l"]
            for tk in ticks:
                y = Y(tk)
                out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W - R}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>')
                out.append(_text(L - 6, y + 3.5, self.y_fmt(tk), 9.5, MUTED, "end"))
            if lo < 0 < hi:
                out.append(f'<line x1="{L}" y1="{Y(0):.1f}" x2="{W - R}" y2="{Y(0):.1f}" stroke="{AXIS}" stroke-width="1"/>')
        if ranges["r"]:                                   # right axis labels
            for tk in ranges["r"][2]:
                out.append(_text(W - R + 6, Y(tk, "r") + 3.5, self.y2_fmt(tk), 9.5, MUTED, "start"))
        step = max(1, math.ceil(n / self.max_labels))     # x labels
        for i, lab in enumerate(self.labels):
            if i % step == 0:
                out.append(_text(X(i), H - 10, lab, 9.5, MUTED, "middle"))
        out.append(f'<line x1="{L}" y1="{T + ph:.1f}" x2="{W - R}" y2="{T + ph:.1f}" stroke="{AXIS}" stroke-width="1"/>')

        for kind, data, ax in self.layers:                # drawing order: bands, bars, lines, reference lines
            if kind != "band":
                continue
            lo_v, hi_v, color, op = data
            pts = [(X(i), Y(v, ax)) for i, v in enumerate(hi_v)] + [(X(i), Y(v, ax)) for i, v in reversed(list(enumerate(lo_v)))]
            out.append(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="{color}" fill-opacity="{op}"/>')
        for kind, data, ax in self.layers:
            if kind != "bars":
                continue
            ns, band = len(data), pw / n
            group = band * 0.72
            bw = group / ns
            for si, (_, vs, color) in enumerate(data):
                for i, v in enumerate(vs):
                    if v is None:
                        continue
                    x = X(i) - group / 2 + si * bw
                    y0, y1 = Y(0), Y(v)
                    out.append(f'<rect x="{x + 0.5:.1f}" y="{min(y0, y1):.1f}" width="{max(bw - 1, 1):.1f}" '
                               f'height="{max(abs(y1 - y0), 0.6):.1f}" fill="{color}"/>')
        for kind, data, ax in self.layers:
            if kind != "line":
                continue
            name, vs, color, dash, area, markers, width = data
            pts = [(X(i), Y(v, ax)) for i, v in enumerate(vs) if v is not None]
            if len(pts) < 1:
                continue
            if area and len(pts) > 1:
                base = Y(max(ranges[ax][0], 0.0), ax)
                poly = f"{pts[0][0]:.1f},{base:.1f} " + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f" {pts[-1][0]:.1f},{base:.1f}"
                out.append(f'<polygon points="{poly}" fill="{color}" fill-opacity="0.12"/>')
            d = ' stroke-dasharray="4 3"' if dash else ""
            out.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="none" stroke="{color}" '
                       f'stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"{d}/>')
            if markers is True or (markers is None and len(pts) <= 24):
                out += [f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="#fff" stroke="{color}" stroke-width="1.6"/>' for x, y in pts]
        for kind, data, ax in self.layers:
            if kind != "vmark":
                continue
            i, label, color = data
            out.append(f'<line x1="{X(i):.1f}" y1="{T}" x2="{X(i):.1f}" y2="{T + ph:.1f}" stroke="{color}" stroke-width="1.2" stroke-dasharray="4 3"/>')
            if label:
                out.append(_text(X(i) + 4, T + 10, label, 9.5, INK, "start", 600))
        for kind, data, ax in self.layers:
            if kind != "hline":
                continue
            yv, label, color, dash = data
            y = Y(yv, ax)
            d = ' stroke-dasharray="4 3"' if dash else ""
            out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W - R}" y2="{y:.1f}" stroke="{color}" stroke-width="1.2"{d}/>')
            if label:
                out.append(_text(W - R - 4, y - 4, label, 9.5, color, "end", 600))
        out.append("</svg>")
        return "".join(out)


def hbars(items, series, width=720, label_w=150, value_fmt=money, row_pad=9, bar_h=11):
    """Horizontal bars. items: [(label, [v1, v2, ...])]; series: [(name, color)] (legend when >1)."""
    ns = len(series)
    row_h = ns * bar_h + row_pad
    top = 18 if ns > 1 else 4
    H = top + row_h * len(items) + 4
    vmax = max([v for _, vs in items for v in vs if v is not None] + [1.0])
    plot_w = width - label_w - 78
    out = [f'<svg viewBox="0 0 {width} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" style="display:block;max-width:100%">']
    if ns > 1:
        svg, _ = _legend([(n, c, "box") for n, c in series], label_w, 11, max_x=width)
        out.append(svg)
    for r, (label, vs) in enumerate(items):
        y0 = top + r * row_h
        short = label if len(label) <= 24 else label[:23] + "…"
        out.append(_text(label_w - 8, y0 + ns * bar_h / 2 + 3.5, short, 10, INK, "end"))
        for si, v in enumerate(vs):
            if v is None:
                continue
            w = max(v / vmax * plot_w, 0.0)
            y = y0 + si * bar_h
            out.append(f'<rect x="{label_w}" y="{y:.1f}" width="{w:.1f}" height="{bar_h - 2}" rx="1.5" fill="{series[si][1]}"/>')
            out.append(_text(label_w + w + 5, y + bar_h - 3, value_fmt(v), 9, MUTED))
    out.append("</svg>")
    return "".join(out)


def donut_svg(items, size=150, hole=0.64, center_title="", center_sub=""):
    """items: [(label, value, color)]; drawn with dashed circle strokes (renders everywhere)."""
    total = sum(v for _, v, _ in items if v > 0) or 1.0
    c = size / 2
    sw = size * (1 - hole) / 2
    r = c - sw / 2 - 1
    circ = 2 * math.pi * r
    out = [f'<svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">']
    off = 0.0
    for _, v, color in items:
        if v <= 0:
            continue
        ln = v / total * circ
        out.append(f'<circle cx="{c}" cy="{c}" r="{r:.2f}" fill="none" stroke="{color}" stroke-width="{sw:.2f}" '
                   f'stroke-dasharray="{max(ln - 1.2, 0.1):.2f} {circ - max(ln - 1.2, 0.1):.2f}" '
                   f'stroke-dashoffset="{-off:.2f}" transform="rotate(-90 {c} {c})"/>')
        off += ln
    if center_title:
        out.append(_text(c, c + (0 if center_sub else 4), center_title, 13.5, INK, "middle", 700))
    if center_sub:
        out.append(_text(c, c + 14, center_sub, 8.5, MUTED, "middle"))
    out.append("</svg>")
    return "".join(out)


def legend_table(items, value_fmt=money, total=None, style=""):
    """Colour-coded rows: name, share, amount. items: [(label, value, color)]."""
    total = total if total is not None else (sum(v for _, v, _ in items if v > 0) or 1.0)
    rows = "".join(
        f'<tr><td class="dot"><span style="background:{c}"></span></td><td class="nm">{esc(l)}</td>'
        f'<td class="num mut">{v / total * 100:.1f}%</td><td class="num">{value_fmt(v)}</td></tr>' for l, v, c in items)
    return f'<table class="rp-leg" style="{style}">{rows}</table>'


def donut_block(items, center_title="", center_sub="", value_fmt=money, size=150):
    """Donut on the left, legend table on the right (a layout table, not flexbox)."""
    items = [(l, v, c) for l, v, c in items if v > 0]
    return (f'<table class="rp-donut"><tr><td class="d">{donut_svg(items, size, center_title=center_title, center_sub=center_sub)}</td>'
            f'<td>{legend_table(items, value_fmt)}</td></tr></table>')


def segbar(items, width=720, h=12):
    """Stacked bar: items [(label, value, color)]."""
    total = sum(v for _, v, _ in items if v > 0) or 1.0
    out = [f'<svg viewBox="0 0 {width} {h}" width="100%" xmlns="http://www.w3.org/2000/svg" style="display:block;max-width:100%">']
    x = 0.0
    for _, v, c in items:
        if v <= 0:
            continue
        w = v / total * width
        out.append(f'<rect x="{x:.1f}" y="0" width="{max(w - 1.5, 0.5):.1f}" height="{h}" rx="2" fill="{c}"/>')
        x += w
    out.append("</svg>")
    return "".join(out)


def heatmap(counts, width=720):
    """Calendar of activity per day for the last 53 weeks. counts: Series date -> number."""
    import pandas as pd
    end = pd.Timestamp(counts.index.max()).normalize()
    start = end - pd.Timedelta(weeks=52)
    start -= pd.Timedelta(days=start.weekday())
    weeks = (end - start).days // 7 + 1
    left, top = 26, 16
    cell = (width - left) / weeks
    H = top + 7 * cell + 4
    vmax = max(float(counts.max()), 1.0)
    shades = ["#EEF1F4", "#C9D8E8", "#97B6D4", "#5F8DB8", "#2F5E8F"]
    out = [f'<svg viewBox="0 0 {width} {H:.0f}" width="100%" xmlns="http://www.w3.org/2000/svg" style="display:block;max-width:100%">']
    for r, d in enumerate(["Mon", "", "Wed", "", "Fri", "", "Sun"]):
        if d:
            out.append(_text(left - 4, top + r * cell + cell * 0.75, d, 8, MUTED, "end"))
    last_month, last_w = None, None
    for day in pd.date_range(start, end):
        w, r = (day - start).days // 7, day.weekday()
        v = float(counts.get(day, 0))
        shade = shades[0] if v <= 0 else shades[min(1 + int(v / vmax * 3.999), 4)]
        out.append(f'<rect x="{left + w * cell:.1f}" y="{top + r * cell:.1f}" width="{cell - 1.6:.1f}" height="{cell - 1.6:.1f}" rx="1.5" fill="{shade}"/>')
        if r == 0 and day.month != last_month:
            if last_w is None or w - last_w >= 3:
                out.append(_text(left + w * cell, 10, day.strftime("%b"), 8.5, MUTED))
                last_w = w
            last_month = day.month
    out.append("</svg>")
    return "".join(out)


def spark(values, color, w=110, h=22):
    vals = [float(v) for v in values if v == v and not math.isinf(v)]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    pts = [(i / (len(vals) - 1) * w, h - 3 - (v - lo) / span * (h - 6)) for i, v in enumerate(vals)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" height="{h}" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg" '
            f'style="display:block;margin-top:6px"><polygon points="0,{h} {line} {w},{h}" fill="{color}" fill-opacity="0.12"/>'
            f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="1.4" stroke-linejoin="round" '
            f'stroke-linecap="round" vector-effect="non-scaling-stroke"/></svg>')


ZONES = [(0, 6, "#C0504D"), (6, 12, "#C79A2B"), (12, 24, "#4E9A6B")]   # same bands as kpis.RUNWAY_BANDS


def gauge(value, max_v=24.0):
    """Semi-circular gauge for months of runway, light theme."""
    W, H, cx, cy, R, sw = 320, 176, 160, 150, 108, 12

    def pt(v, r):
        th = math.pi * (1 - min(max(v, 0.0), max_v) / max_v)
        return cx + r * math.cos(th), cy - r * math.sin(th)

    def arc(v0, v1, r):
        x0, y0 = pt(v0, r)
        x1, y1 = pt(v1, r)
        return f"M {x0:.2f} {y0:.2f} A {r} {r} 0 0 1 {x1:.2f} {y1:.2f}"

    val = min(max(value, 0.0), max_v)
    g = 0.18
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" style="display:block;max-width:300px;margin:0 auto">']
    for a, b, c in ZONES:
        out.append(f'<path d="{arc(a + (g if a > 0 else 0.0), b - (g if b < max_v else 0.0), R)}" fill="none" '
                   f'stroke="{c}" stroke-opacity="0.25" stroke-width="{sw}"/>')
    for a, b, c in ZONES:
        if val > a:
            out.append(f'<path d="{arc(a + (g if a > 0 else 0.0), min(val, b - (g if b < max_v else 0.0)), R)}" fill="none" '
                       f'stroke="{c}" stroke-width="{sw}"/>')
    kx, ky = pt(val, R)
    out.append(f'<circle cx="{kx:.2f}" cy="{ky:.2f}" r="7" fill="{INK}" stroke="#fff" stroke-width="3"/>')
    for v in (0, 6, 12, max_v):
        x, y = pt(v, R + 22)
        out.append(_text(x, y + 4, f"{v:g}", 10, MUTED, "middle", 500))
    out.append(_text(cx, cy - 20, f"{value:,.2f}", 36, INK, "middle", 700, 'letter-spacing="-1"'))
    out.append(_text(cx, cy - 2, "MONTHS", 9.5, MUTED, "middle", 600, 'letter-spacing="2.2"'))
    out.append("</svg>")
    return "".join(out)


def _wrap(label, n=14):
    words, lines, cur = str(label).split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > n:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    return lines + [cur] if cur else lines


def waterfall(steps, width=380, height=230):
    """From baseline to plan. steps: (label, value, 'absolute'|'relative'|'total')."""
    bases, vals, cols, run = [], [], [], 0.0
    for _, v, kind in steps:
        if kind == "relative":
            bases.append(run)
            run += v
            cols.append(INCOME if v >= 0 else EXPENSE)
        else:
            bases.append(0.0)
            run = v
            cols.append(NETWORTH)
        vals.append(v)
    lo = min([0.0] + [b for b in bases] + [b + v for b, v in zip(bases, vals)])
    hi = max([0.0] + [b for b in bases] + [b + v for b, v in zip(bases, vals)])
    ticks = nice_ticks(lo, hi, 4)
    lo, hi = ticks[0], ticks[-1]
    L, R, T, B = 58, 12, 22, 40
    pw, ph = width - L - R, height - T - B

    def Y(v):
        return T + (1 - (v - lo) / (hi - lo)) * ph

    n = len(steps)
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" xmlns="http://www.w3.org/2000/svg" style="display:block;max-width:100%">']
    for tk in ticks:
        out.append(f'<line x1="{L}" y1="{Y(tk):.1f}" x2="{width - R}" y2="{Y(tk):.1f}" stroke="{GRID}"/>')
        out.append(_text(L - 6, Y(tk) + 3.5, axis_money(tk), 9.5, MUTED, "end"))
    if lo < 0 < hi:
        out.append(f'<line x1="{L}" y1="{Y(0):.1f}" x2="{width - R}" y2="{Y(0):.1f}" stroke="{AXIS}"/>')
    bw = pw / n * 0.58
    for i, ((label, v, kind), b, c) in enumerate(zip(steps, bases, cols)):
        x = L + (i + 0.5) * pw / n
        y0, y1 = Y(b), Y(b + v)
        out.append(f'<rect x="{x - bw / 2:.1f}" y="{min(y0, y1):.1f}" width="{bw:.1f}" height="{max(abs(y1 - y0), 0.8):.1f}" fill="{c}"/>')
        top = min(y0, y1)
        out.append(_text(x, top - 4 if v >= 0 else max(y0, y1) + 11, money(v, 0, sign=(kind == "relative")), 9, INK, "middle", 600))
        for j, ln in enumerate(_wrap(label, max(int(pw / n / 5.2), 8))):
            out.append(_text(x, height - B + 14 + j * 10.5, ln, 8.8, MUTED, "middle"))
    out.append("</svg>")
    return "".join(out)
