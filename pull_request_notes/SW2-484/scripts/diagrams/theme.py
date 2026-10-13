"""Design tokens for every figure.

Palette: ui-ux-pro-max-skill  colors.csv row 81 "Developer Tool / IDE"
  (background #0F172A, card #1B2336, muted #272F42, foreground #F8FAFC,
   muted-foreground #94A3B8, border #475569, accent #22C55E, destructive #EF4444)
extended with the vivid accent set of the skill's "Dark Mode (OLED)" style for categorical
encodings (sky / violet / amber), all checked for >= 4.5:1 contrast on the card colour.

Typography: ui-ux-pro-max-skill typography.csv row 9 "Developer Mono"
  JetBrains Mono for code identifiers, IBM Plex Sans for prose/UI text.
"""
from pathlib import Path

FONT_DIR = Path(__file__).parent / "fonts"


class T:
    # surfaces
    bg = "#0F172A"          # page / canvas
    bg_deep = "#0B1222"     # inset panels (map floor)
    card = "#1B2336"        # boxes
    card_hi = "#222B40"     # header bands, hovered
    muted_bg = "#272F42"    # chips, lanes
    grid = "#1E293B"        # subtle grid lines
    # text
    fg = "#F8FAFC"
    fg2 = "#CBD5E1"         # secondary text (members)
    muted = "#94A3B8"       # captions, axis labels
    faint = "#64748B"       # tertiary / hints
    # lines
    border = "#475569"
    border_soft = "#334155"
    # semantic accents
    green = "#22C55E"       # primary action / response / AGV route
    sky = "#38BDF8"         # request / abstract / information
    violet = "#A78BFA"      # state snapshot / resource transitions
    amber = "#F59E0B"       # trays / commands / blocking
    red = "#EF4444"         # conflict / destructive
    teal = "#2DD4BF"        # utility types
    pink = "#F472B6"        # payload

    @staticmethod
    def tint(hex_color: str, alpha: float, over: str = "#1B2336") -> str:
        """Blend `hex_color` over `over` at `alpha` -> opaque hex (keeps SVGs free of opacity stacking)."""
        a = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
        b = [int(over[i:i + 2], 16) for i in (1, 3, 5)]
        c = [round(b[i] + (a[i] - b[i]) * alpha) for i in range(3)]
        return "#" + "".join(f"{v:02X}" for v in c)


# type scale (px in the SVG's own coordinate system; figures are <= ~1000 px wide so they
# render close to 1:1 in a Markdown preview column)
class S:
    title = 21
    subtitle = 13.5
    h = 14            # box headers / class names
    body = 12.5       # members, labels
    small = 11.5      # edge labels, axis ticks
    tiny = 10.5       # stereotypes
