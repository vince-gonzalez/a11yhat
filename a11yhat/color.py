"""WCAG contrast math. Relative luminance and ratio, per WCAG 2.x definitions."""
from __future__ import annotations

import re

_NAMED = {"black": (0, 0, 0), "white": (255, 255, 255), "red": (255, 0, 0),
          "green": (0, 128, 0), "blue": (0, 0, 255), "gray": (128, 128, 128),
          "grey": (128, 128, 128), "silver": (192, 192, 192), "navy": (0, 0, 128)}


def parse_rgba(value: str):
    """#rgb, #rrggbb, #rrggbbaa, rgb()/rgba(), or a named color
    -> (r, g, b, a) with a in 0.0-1.0, or None.

    ALPHA IS PART OF THE ANSWER. The first version of this threw it away,
    capturing three groups out of rgba() and nothing else, so
    rgba(0,0,0,0.04) was read as pure black. Against white that scores
    21:1 when the colour a person actually sees is about #f5f5f5, which
    is 1.09:1. The checker called unreadable text a pass. Alpha is
    returned here and composited by the caller, which is the only place
    that knows what the colour sits on.
    """
    v = value.strip().lower()
    if v in _NAMED:
        return _NAMED[v] + (1.0,)
    m = re.fullmatch(r"#([0-9a-f]{3})", v)
    if m:
        return tuple(int(c * 2, 16) for c in m.group(1)) + (1.0,)
    m = re.fullmatch(r"#([0-9a-f]{4})", v)
    if m:
        h = m.group(1)
        return (tuple(int(c * 2, 16) for c in h[:3])
                + (int(h[3] * 2, 16) / 255.0,))
    m = re.fullmatch(r"#([0-9a-f]{6})", v)
    if m:
        h = m.group(1)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (1.0,)
    m = re.fullmatch(r"#([0-9a-f]{8})", v)
    if m:
        h = m.group(1)
        return (tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
                + (int(h[6:8], 16) / 255.0,))
    m = re.match(r"rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)"
                 r"(?:[,/\s]+([\d.]+%?))?", v)
    if m:
        rgb = tuple(min(255, int(float(x))) for x in m.groups()[:3])
        a = m.group(4)
        if a is None:
            alpha = 1.0
        elif a.endswith("%"):
            alpha = float(a[:-1]) / 100.0
        else:
            alpha = float(a)
        return rgb + (max(0.0, min(1.0, alpha)),)
    return None


def composite(rgba, backdrop=(255, 255, 255)):
    """Flatten a possibly-translucent colour onto what is behind it.

    This is the 'over' operator: c = a*fg + (1-a)*bg, per channel. The
    backdrop defaults to white because that is what an unstyled page is,
    and the caller is expected to pass the real one when it knows it.
    """
    if rgba is None:
        return None
    r, g, b, a = rgba
    if a >= 1.0:
        return (r, g, b)
    br, bg_, bb = backdrop
    return (round(a * r + (1 - a) * br),
            round(a * g + (1 - a) * bg_),
            round(a * b + (1 - a) * bb))


def parse_color(value: str):
    """#rgb, #rrggbb, rgb()/rgba(), or a named color -> (r,g,b) or None.

    KEPT FOR CALLERS THAT ONLY WANT A HUE. It discards alpha, so it must
    NOT be used for contrast: see parse_rgba and composite for that.
    """
    c = parse_rgba(value)
    return None if c is None else c[:3]


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
