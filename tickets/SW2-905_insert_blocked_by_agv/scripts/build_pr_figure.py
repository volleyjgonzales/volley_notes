"""The PR figure (fig_pr of build_figures.py) in a light theme, rendered static for GitHub.

Usage: python3 scripts/build_pr_figure.py  ->  figures/06_pr_scenario_and_plan_light.svg
The kit's colours are captured as default arguments when its modules are imported, so the light
palette is applied to theme.T before anything else is imported.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TICKET = HERE.parent
sys.path.insert(0, str(TICKET.parents[1] / "presentations" / "scheduler_package" / "scripts" / "diagrams"))
import theme  # noqa: E402

LIGHT = dict(
    bg="#FFFFFF", bg_deep="#F1F5F9", card="#F8FAFC", card_hi="#E2E8F0", muted_bg="#E2E8F0", grid="#E2E8F0",
    fg="#0F172A", fg2="#334155", muted="#64748B", faint="#94A3B8", border="#94A3B8", border_soft="#CBD5E1",
    green="#15803D", sky="#0369A1", violet="#6D28D9", amber="#B45309", red="#B91C1C", teal="#0F766E",
    pink="#BE185D", yellow="#A16207", blue="#1D4ED8",
)
for name, value in LIGHT.items():
    setattr(theme.T, name, value)


def tint(hex_color: str, alpha: float, over: str = LIGHT["card"]) -> str:
    a = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(over[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(b[i] + (a[i] - b[i]) * alpha):02X}" for i in range(3))


theme.T.tint = staticmethod(tint)

sys.path.insert(0, str(HERE))
import build_figures as bf  # noqa: E402
from facility import EDGES, NODES, STALL_W, Map  # noqa: E402
from svgkit import BBox  # noqa: E402


def corridors(self: Map) -> None:
    """The kit draws the travel corridors in a hard-coded dark band; a light band here."""
    w = STALL_W * self.s
    for a, b in EDGES:
        A, B = NODES[a], NODES[b]
        if {A.type, B.type} <= {"Waypoint", "Bay"} and not (A.type == B.type == "Bay"):
            if not (self.visible(A, 3) or self.visible(B, 3)):
                continue
            x0, y0 = self.P(a)
            x1, y1 = self.P(b)
            self.d.path(f"M{x0} {y0} L{x1} {y1}", stroke="#DCE3EC", sw=w, cap="square", layer="bg",
                        bbox=BBox(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))


Map.corridors = corridors

if __name__ == "__main__":
    doc = bf.fig_pr()
    out = TICKET / "figures" / "06_pr_scenario_and_plan_light.svg"
    out.write_text(doc.render(interactive=False), encoding="utf-8")
    overlaps = doc.text_overlaps()
    print(f"{out.name} {doc.canvas.w:.0f} x {doc.canvas.h:.0f}" + (f"  !! overlaps: {overlaps[:4]}" if overlaps else ""))
    sys.exit(1 if overlaps else 0)
