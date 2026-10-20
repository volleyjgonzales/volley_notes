"""Light theme for the figures.

The figures are drawn once, in the dark palette of theme.py. This module derives the light theme from them:

  light(hex)          maps one dark-theme colour to its light-theme colour
  figures/light/*.svg a light copy of every figure (used by the site's <img> figures and the "SVG" links)
  figures/theme-map.json
                      every colour used by the figures and the deck, dark -> light (the deck builds its rules from it)
  site/src/styles/figures-light.css
                      CSS that recolours figures inlined in a page (the site's animated figures, the gallery viewer)
                      when the page is in light mode: html[data-theme=light], or no data-theme and a light OS setting

Mapping rules, in order:
  1. design tokens of theme.py map to hand-picked light tokens (same roles: canvas, card, text, accents darkened
     for contrast on white);
  2. a colour made with T.tint(fg, alpha, over=base) maps to T.tint(light(fg), alpha, light(base)), so tinted fills
     keep their meaning (a 15 % green wash stays a 15 % green wash, over white instead of navy);
  3. anything else: OKLab lightness is mirrored along a curve that sends dark surfaces to near-white and
     light text to dark slate, keeping hue and (gamut-clamped) chroma.

Run:  python3 scripts/diagrams/lightmode.py            (all figures)
      python3 scripts/diagrams/lightmode.py 26_ 118_   (only these figures; the map and CSS are always rebuilt)
      python3 scripts/diagrams/lightmode.py --map      (only the map and CSS)
build.py calls write_light_copies() for the figures it builds.
"""
from __future__ import annotations

import json
import re
import sys
from functools import lru_cache
from pathlib import Path

from theme import T

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "figures"
LIGHT_DIR = FIG / "light"
MAP_JSON = FIG / "theme-map.json"
SITE_CSS = ROOT / "site" / "src" / "styles" / "figures-light.css"
DECK_SRC = ROOT / "deck" / "src"
DECK_FIG = ROOT / "deck" / "figures"

TOKENS = {
    # surfaces
    T.bg: "#FFFFFF", T.bg_deep: "#F1F5F9", T.card: "#F8FAFC", T.card_hi: "#EEF2F7", T.muted_bg: "#E2E8F0",
    T.grid: "#E2E8F0", "#020617": "#F8FAFC", "#131C31": "#F1F5F9", "#162036": "#EEF2F7",
    # text
    T.fg: "#0F172A", "#E8EEF7": "#0F172A", "#E2E8F0": "#1E293B", T.fg2: "#334155", T.muted: "#475569", T.faint: "#64748B",
    # lines
    T.border: "#94A3B8", T.border_soft: "#CBD5E1",
    # accents (Tailwind 600/700 shades: >= 4.5:1 on white)
    T.green: "#15803D", T.sky: "#0369A1", T.violet: "#6D28D9", T.amber: "#B45309",
    T.red: "#B91C1C", T.teal: "#0F766E", T.pink: "#BE185D", "#7DD3FC": "#075985",
}
TOKENS = {k.upper(): v for k, v in TOKENS.items()}
ACCENTS = [T.green, T.sky, T.violet, T.amber, T.red, T.teal, T.pink]
NEUTRAL_FG = [T.fg, T.fg2, T.muted, T.faint, T.border, T.border_soft, T.card, T.muted_bg]
BASES = [T.bg, T.bg_deep, T.card, T.card_hi, "#020617"]


def _rgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def _hex(c):
    return "#" + "".join(f"{max(0, min(255, round(v))):02X}" for v in c)


def _tint(fg, a, over):
    f, b = _rgb(fg), _rgb(over)
    return _hex([b[i] + (f[i] - b[i]) * a for i in range(3)])


# ---- OKLab
def _lin(u):
    u /= 255
    return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4


def _gam(u):
    u = 12.92 * u if u <= 0.0031308 else 1.055 * u ** (1 / 2.4) - 0.055
    return u * 255


def _to_oklab(c):
    r, g, b = (_lin(v) for v in c)
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def _from_oklab(L, A, B):
    l = (L + 0.3963377774 * A + 0.2158037573 * B) ** 3
    m = (L - 0.1055613458 * A - 0.0638541728 * B) ** 3
    s = (L - 0.0894841775 * A - 1.2914855480 * B) ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    b = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return r, g, b


# dark-theme OKLab lightness -> light-theme lightness (surfaces -> near white, light text -> dark slate)
_CURVE = [(0.0, 1.0), (0.18, 0.995), (0.22, 0.985), (0.27, 0.965), (0.33, 0.93), (0.40, 0.87), (0.48, 0.78),
          (0.56, 0.66), (0.66, 0.56), (0.76, 0.50), (0.86, 0.40), (0.93, 0.30), (1.0, 0.21)]


def _curve(L):
    for (x0, y0), (x1, y1) in zip(_CURVE, _CURVE[1:]):
        if L <= x1:
            return y0 + (y1 - y0) * (L - x0) / (x1 - x0)
    return _CURVE[-1][1]


def _generic(h):
    L, A, B = _to_oklab(_rgb(h))
    L2 = _curve(L)
    k = 1.0
    for _ in range(40):  # clamp chroma into sRGB
        rgb = _from_oklab(L2, A * k, B * k)
        if all(-1e-4 <= v <= 1 + 1e-4 for v in rgb):
            break
        k *= 0.9
    return _hex([_gam(max(0.0, min(1.0, v))) for v in rgb])


def _as_tint(h):
    """(fg, alpha, base) with T.tint(fg, alpha, base) == h (within 2/255), accents preferred; else None."""
    c = _rgb(h)
    for group in (ACCENTS, NEUTRAL_FG):
        best = None
        for base in BASES:
            b = _rgb(base)
            for fg in group:
                f = _rgb(fg)
                num = sum((c[i] - b[i]) * (f[i] - b[i]) for i in range(3))
                den = sum((f[i] - b[i]) ** 2 for i in range(3))
                if den < 300:
                    continue
                a = num / den
                if not 0.02 <= a <= 0.98:
                    continue
                err = max(abs(b[i] + (f[i] - b[i]) * a - c[i]) for i in range(3))
                if err <= 2.01 and (best is None or err < best[0]):
                    best = (err, fg, a, base)
        if best:
            return best[1:]
    return None


@lru_cache(maxsize=None)
def light(h: str) -> str:
    h = h.upper()
    if len(h) == 4:
        h = "#" + "".join(ch * 2 for ch in h[1:])
    if h in TOKENS:
        return TOKENS[h]
    t = _as_tint(h)
    if t:
        fg, a, base = t
        return _tint(TOKENS[fg.upper()], a, TOKENS[base.upper()])
    return _generic(h)


# ---- files
HEX = re.compile(r"(?<!url\()(?<!href=\")#([0-9A-Fa-f]{6})(?![0-9A-Za-z_-])")


def recolor_text(s: str) -> str:
    """Recolour every #RRGGBB in an SVG (attributes, style attributes, <style> and the viewer script)."""
    return HEX.sub(lambda m: light("#" + m.group(1)), s)


def write_light_copies(names=None):
    LIGHT_DIR.mkdir(exist_ok=True)
    n = 0
    for f in sorted(FIG.glob("*.svg")):
        if names and not any(f.stem.startswith(p) for p in names):
            continue
        (LIGHT_DIR / f.name).write_text(recolor_text(f.read_text()))
        n += 1
    for f in LIGHT_DIR.glob("*.svg"):  # drop copies of figures that no longer exist
        if not (FIG / f.name).exists():
            f.unlink()
    return n


def _colors_in(paths):
    seen = set()
    for p in paths:
        s = p.read_text()
        s = re.sub(r"base64,[A-Za-z0-9+/=]+", "", s)
        seen.update(("#" + m.group(1)).upper() for m in HEX.finditer(s))
    return seen


def write_map_and_css():
    figs = list(FIG.glob("*.svg"))
    cols = _colors_in(figs) | _colors_in(list(DECK_SRC.glob("*.html")) + list(DECK_SRC.glob("*.css"))
                                         + list(DECK_FIG.glob("*.svg")))
    cols |= set(TOKENS)
    m = {c: light(c) for c in sorted(cols)}
    MAP_JSON.write_text(json.dumps(m, indent=0) + "\n")
    # CSS for figures inlined in a page. Presentation attributes lose to any CSS rule; the text halos are in style
    # attributes, so those rules need !important. Only (attribute, colour) pairs that occur get a rule.
    used = set()
    for f in figs:
        s = re.sub(r"<script>[\s\S]*?</script>", "", f.read_text())
        used.update((a, c.upper()) for a, c in re.findall(r'\b(fill|stroke|stop-color)="(#[0-9A-Fa-f]{6})"', s))
        used.update(("style", c.upper()) for c in re.findall(r'style="[^"]*?stroke:(#[0-9A-Fa-f]{6})', s))
    rules = []
    for a, c in sorted(used):
        lc = m[c]
        if lc == c:
            continue
        if a == "style":
            rules.append(f'S [style*="stroke:{c}" i]{{stroke:{lc}!important}}')
        else:
            rules.append(f'S [{a}="{c}" i]{{{a}:{lc}}}')
    body = "\n".join(rules)
    scope = "svg[data-figure]"
    css = (
        "/* GENERATED by scripts/diagrams/lightmode.py: light-theme colours for figures inlined in the page. */\n"
        + body.replace("S ", f":root[data-theme='light'] {scope} ")
        + "\n@media (prefers-color-scheme: light) {\n"
        + body.replace("S ", f":root:not([data-theme]) {scope} ")
        + "\n}\n"
    )
    SITE_CSS.write_text(css)
    return len(m), len(rules)


def main(argv):
    if argv == ["--map"]:  # colour map and page CSS only (the deck build calls this)
        k, r = write_map_and_css()
        print(f"lightmode: {k} colours mapped, {r} CSS rules")
        return
    n = write_light_copies(argv or None)
    k, r = write_map_and_css()
    print(f"lightmode: {n} light figure copies, {k} colours mapped, {r} CSS rules")


if __name__ == "__main__":
    main(sys.argv[1:])
