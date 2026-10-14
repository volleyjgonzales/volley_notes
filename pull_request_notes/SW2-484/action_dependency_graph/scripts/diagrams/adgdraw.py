"""Swim-lane drawing of an Action Dependency Graph.

One lane per robot, one column per time step t, one box per action. Type-1 edges run along a
lane; type-2 edges are routed orthogonally through the gaps between columns and the channels
between lanes, so an arrow never passes underneath an action box.
"""
from __future__ import annotations

from collections import defaultdict

from components import connect, label_pill
from svgkit import BBox, Doc, text_width
from theme import T, S

ARROW = "→"


class Lanes:
    def __init__(self, doc: Doc, x0, y0, robots, colors, tmax, *, col_w=184, box_w=106, box_h=50, lane_h=88,
                 lane_gap=12, label_w=104, lane_labels=None, axis=True, axis_label="time step t"):
        self.d, self.x0, self.y0 = doc, x0, y0
        self.robots, self.colors, self.tmax = robots, colors, tmax
        self.col_w, self.box_w, self.box_h, self.lane_h, self.lane_gap = col_w, box_w, box_h, lane_h, lane_gap
        self.label_w = label_w
        self.boxes: dict = {}
        self.pills: list[BBox] = []
        self.lane_labels = lane_labels or {r: f"AGV {r}" for r in robots}
        W = self.label_w + (tmax + 1) * col_w - (col_w - box_w) + 22
        self.W = W
        for i, r in enumerate(robots):
            y = self.lane_y(i)
            c = colors[r]
            doc.rect(x0, y, W, lane_h, rx=10, fill=T.tint(c, 0.05, T.bg), stroke=T.tint(c, 0.28, T.bg), sw=1,
                     layer="bg")
            doc.text(x0 + 16, y + lane_h / 2, self.lane_labels[r], size=13.5, weight=600, fill=c)
        self.y1 = self.lane_y(len(robots)) - lane_gap
        if axis:
            ay = self.y1 + 16
            for t in range(tmax + 1):
                cx = self.col_x(t) + box_w / 2
                doc.line(cx, ay - 4, cx, ay + 4, stroke=T.border, sw=1)
                doc.text(cx, ay + 17, f"t = {t}", size=S.small, family="mono", fill=T.muted, anchor="middle")
            doc.line(self.col_x(0), ay, self.col_x(tmax) + box_w, ay, stroke=T.border, sw=1)
            doc.text(x0 + 16, ay + 17, axis_label, size=S.small, fill=T.muted)
            self.y1 = ay + 26

    # ---- geometry -----------------------------------------------------------------------
    def lane_y(self, i):
        return self.y0 + i * (self.lane_h + self.lane_gap)

    def col_x(self, t):
        return self.x0 + self.label_w + t * self.col_w

    def lane_of(self, a):
        return self.robots.index(a.R)

    def box_of(self, a) -> BBox:
        x = self.col_x(a.t)
        y = self.lane_y(self.lane_of(a)) + (self.lane_h - self.box_h) / 2
        return BBox(x, y, x + self.box_w, y + self.box_h)

    # ---- nodes --------------------------------------------------------------------------
    def action(self, a, style="normal", note: str | None = None):
        """style: normal | wait | ghost (removed) | focus | dim"""
        d = self.d
        bb = self.box_of(a)
        c = self.colors[a.R]
        if style == "focus":
            d.rect(bb.x0 - 5, bb.y0 - 5, bb.w + 10, bb.h + 10, rx=11, fill="none", stroke=T.tint(c, 0.7, T.bg),
                   sw=1.4, dash="3 3")
        op = 0.38 if style in ("ghost", "dim") else None
        dash = "5 4" if style in ("wait", "ghost") or (a.wait and style != "normal") else None
        if a.wait and style == "normal":
            dash = "5 4"
        fill = T.bg if (a.wait or style == "ghost") else T.card
        d.rect(bb.x0, bb.y0, bb.w, bb.h, rx=8, fill=fill, stroke=c, sw=1.5, dash=dash, opacity=op)
        d.text(bb.x0 + 10, bb.y0 + 15, a.id, size=11.5, family="mono", weight=700, fill=c, opacity=op)
        lab = f"wait {a.s}" if a.wait else f"{a.s} {ARROW} {a.g}"
        d.text(bb.x0 + 10, bb.y0 + 35, lab, size=12.5, family="mono", fill=T.fg if not op else T.muted,
               opacity=op)
        if note:
            d.text(bb.x1 - 8, bb.y0 + 15, note, size=10, family="mono", weight=600, fill=c, anchor="end",
                   opacity=op)
        self.boxes[a] = bb
        return bb

    # ---- edges --------------------------------------------------------------------------
    def type1(self, a, b, color=None, dash=None, sw=1.6):
        A, B = self.box_of(a), self.box_of(b)
        connect(self.d, [(A.x1, A.cy), (B.x0, B.cy)], kind="flow", color=color or self.colors[a.R], size=8,
                sw=sw, dash=dash)

    def type2(self, edges, *, style=None, pill=True):
        """edges: iterable of (c, a). style(c, a) -> dict(color, sw, dash, pill_color)."""
        style = style or (lambda c, a: {})
        edges = sorted(edges, key=lambda e: (e[0].t, self.lane_of(e[0]), e[1].t, self.lane_of(e[1])))
        # --- classify and collect track / port demands
        plan = []
        gap_users = defaultdict(list)       # gap index -> edges using a vertical in that gap
        chan_users = defaultdict(list)      # channel index (between lane i and i+1) -> edges
        port_users = defaultdict(list)      # (action, side) -> edges
        for c, a in edges:
            lc, la = self.lane_of(c), self.lane_of(a)
            if c.t == a.t and abs(lc - la) == 1:
                kind = "vert"
                port_users[(c, "bottom" if la > lc else "top")].append((c, a))
                port_users[(a, "top" if la > lc else "bottom")].append((c, a))
            else:
                gi = c.t                                  # leave c to the right
                if a.t <= c.t + 1:
                    kind = "gap"
                    gap_users[gi].append((c, a))
                    port_users[(c, "right")].append((c, a))
                    port_users[(a, "left" if a.t == c.t + 1 else "right")].append((c, a))
                else:
                    kind = "chan"
                    ch = lc if la > lc else lc - 1        # channel below / above c's lane
                    gap_users[gi].append((c, a))
                    gap_users[a.t - 1].append((c, a, "in"))
                    chan_users[ch].append((c, a))
                    port_users[(c, "right")].append((c, a))
                    port_users[(a, "left")].append((c, a))
            plan.append((c, a, kind))

        def gap_x(gi, key):
            users = gap_users[gi]
            n = len(users)
            g0 = self.col_x(gi) + self.box_w
            gw = self.col_w - self.box_w
            k = users.index(key)
            return g0 + gw * (k + 1) / (n + 1)

        def chan_y(ch, key):
            users = chan_users[ch]
            n = len(users)
            y0 = self.lane_y(ch) + (self.lane_h + self.box_h) / 2
            y1 = self.lane_y(ch + 1) + (self.lane_h - self.box_h) / 2
            k = users.index(key)
            return y0 + (y1 - y0) * (k + 1) / (n + 1)

        def other_end(e, act):
            c, a = e
            o = a if act == c else c
            return self.box_of(o)

        def port(act, side, e):
            users = port_users[(act, side)]
            bb = self.box_of(act)
            if side in ("top", "bottom"):
                users = sorted(users, key=lambda u: other_end(u, act).cx)
                n = len(users)
                k = users.index(e)
                x = bb.x0 + bb.w * (k + 1) / (n + 1) if n > 1 else bb.cx
                return (x, bb.y0 if side == "top" else bb.y1)
            users = sorted(users, key=lambda u: other_end(u, act).cy)
            n = len(users)
            k = users.index(e)
            slots = [bb.y0 + 9 + (bb.h - 18) * (j + 0.5) / n for j in range(n)] if n > 1 else [bb.cy - 11]
            if n == 1 and side == "right":
                slots = [bb.cy + (11 if other_end(e, act).cy > bb.cy else -11)]
            if n == 1 and side == "left":
                slots = [bb.cy + (11 if other_end(e, act).cy > bb.cy else -11)]
            return (bb.x0 if side == "left" else bb.x1, slots[k])

        for c, a, kind in plan:
            st = style(c, a)
            col = st.get("color", T.fg2)
            e = (c, a)
            if kind == "vert":
                down = self.lane_of(a) > self.lane_of(c)
                p = port(c, "bottom" if down else "top", e)
                q = port(a, "top" if down else "bottom", e)
                pts = [p, (p[0], q[1])] if abs(p[0] - q[0]) < 1 else [p, (p[0], (p[1] + q[1]) / 2),
                                                                      (q[0], (p[1] + q[1]) / 2), q]
                vseg = (pts[0], pts[-1])
            elif kind == "gap":
                p = port(c, "right", e)
                gx = gap_x(c.t, e)
                if a.t == c.t + 1:
                    q = port(a, "left", e)
                else:
                    q = port(a, "right", e)
                pts = [p, (gx, p[1]), (gx, q[1]), q]
                vseg = ((gx, p[1]), (gx, q[1]))
            else:
                p = port(c, "right", e)
                gx1 = gap_x(c.t, e)
                ch = self.lane_of(c) if self.lane_of(a) > self.lane_of(c) else self.lane_of(c) - 1
                cy = chan_y(ch, e)
                gx2 = gap_x(a.t - 1, (c, a, "in"))
                q = port(a, "left", e)
                pts = [p, (gx1, p[1]), (gx1, cy), (gx2, cy), (gx2, q[1]), q]
                vseg = ((gx2, cy), (gx2, q[1]))
            connect(self.d, pts, kind="flow", color=col, size=8, sw=st.get("sw", 1.5), dash=st.get("dash"),
                    radius=6)
            if pill and st.get("pill", True):
                self._pill(vseg, c.s, st.get("pill_color", col))

    def _pill(self, seg, s, color):
        (x0, y0), (x1, y1) = seg
        w = text_width(s, 10.5, "mono", 600) + 10
        h = 16
        for f in (0.5, 0.38, 0.62, 0.26, 0.74, 0.15, 0.85):
            x = x0 + (x1 - x0) * f
            y = y0 + (y1 - y0) * f
            bb = BBox(x - w / 2, y - h / 2, x + w / 2, y + h / 2)
            if not any(bb.intersects(p, -1) for p in self.pills) and \
                    not any(bb.intersects(b, -1) for b in self.boxes.values()):
                break
        self.pills.append(bb)
        self.d.rect(bb.x0, bb.y0, w, h, rx=8, fill=T.bg, stroke=T.tint(color, 0.6, T.bg), sw=1, layer="labels")
        self.d.text(x, y, s, size=10.5, family="mono", weight=600, fill=color, anchor="middle", layer="top")
