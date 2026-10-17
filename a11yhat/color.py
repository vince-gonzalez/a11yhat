"""WCAG contrast math. Relative luminance and ratio, per WCAG 2.x definitions."""
from __future__ import annotations

import re

_NAMED = {"black": (0, 0, 0), "white": (255, 255, 255), "red": (255, 0, 0),
          "green": (0, 128, 0), "blue": (0, 0, 255), "gray": (128, 128, 128),
          "grey": (128, 128, 128), "silver": (192, 192, 192), "navy": (0, 0, 128)}


def parse_color(value: str):
    """#rgb, #rrggbb, rgb()/rgba(), or a few named colors -> (r,g,b) or None."""
    v = value.strip().lower()
    if v in _NAMED:
        return _NAMED[v]
    m = re.fullmatch(r"#([0-9a-f]{3})", v)
    if m:
        return tuple(int(c * 2, 16) for c in m.group(1))
    m = re.fullmatch(r"#([0-9a-f]{6})", v)
    if m:
        h = m.group(1)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    m = re.match(r"rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)", v)
    if m:
        return tuple(min(255, int(float(x))) for x in m.groups())
    return None


def _lin(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb) -> float:
    r, g, b = (_lin(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg, bg) -> float:
    l1, l2 = luminance(fg), luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)
