"""Which colours actually land on which text.

I used to pair a text colour with a background only when one rule set
both. Real stylesheets never do that: `body` paints the background and
`.card p` sets the colour, and the browser resolves it through
inheritance. So I was measuring a handful of declared pairs and missing
every pair a person actually sees, and reporting some that never render
at all - the first run of this found `body: #000 on #008080` on my own
homepage, which is the desktop teal behind the window, with nothing on
it but a skip link that sets its own colours.

So this does the small amount of cascade needed to answer one question
honestly: for each piece of text, what colour is it, and what is behind
it?

  colour inherits, so I walk up until something sets it
  background does NOT inherit, but the backdrop a person sees is the
  nearest ancestor that paints one, so I walk up until something is not
  transparent

WHAT THIS DELIBERATELY DOES NOT DO, because half a cascade that pretends
to be a whole one is worse than none:

  @media blocks are not applied. I measure the default theme and report
  that dark mode and print were not measured.
  Pseudo-class rules (:hover, :focus) are skipped. They are states, not
  the resting page, and measuring them as default was wrong.
  Combinators other than descendant are not matched: >, + and ~ are
  treated as no match rather than guessed at.
  !important is not honoured, and neither is the shorthand `background`
  when it carries more than a colour.

Everything in that list is a reason to report REVIEW rather than PASS,
and the caller does.
"""
from __future__ import annotations

import re

from .color import composite, parse_rgba, ratio

# a selector I will not pretend to understand
_UNSUPPORTED = re.compile(r"[>+~]|::|:(?!root\b)")
_SIMPLE = re.compile(r"^([a-zA-Z][\w-]*)?((?:[.#][\w-]+)*)$")


def rules(css: str):
    """(selector, decls, order) for rules OUTSIDE any @media block.

    I strip at-rule blocks first. The old regex walked straight into
    them and yielded their contents as if they were default rules, so a
    dark-mode colour could be measured against a light background.
    """
    css = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)
    depth, out, buf = 0, [], []
    # drop @media/@supports/@container bodies, keep everything else
    i, n, kept = 0, len(css), []
    while i < n:
        m = re.compile(r"@(media|supports|container|print)\b").search(css, i)
        if not m:
            kept.append(css[i:])
            break
        kept.append(css[i:m.start()])
        j = css.find("{", m.start())
        if j < 0:
            break
        depth, k = 1, j + 1
        while k < n and depth:
            if css[k] == "{":
                depth += 1
            elif css[k] == "}":
                depth -= 1
            k += 1
        i = k
    flat = "".join(kept)

    order = 0
    for sel_raw, body in re.findall(r"([^{}]+)\{([^{}]*)\}", flat):
        decls = {}
        for part in body.split(";"):
            if ":" in part:
                k2, v = part.split(":", 1)
                decls[k2.strip().lower()] = v.strip()
        if not decls:
            continue
        for sel in sel_raw.split(","):
            sel = sel.strip()
            if sel and not _UNSUPPORTED.search(sel):
                out.append((sel, decls, order))
                order += 1
    return out


def specificity(sel: str):
    """(ids, classes, types). Good enough for the selectors I allow."""
    ids = len(re.findall(r"#[\w-]+", sel))
    cls = len(re.findall(r"\.[\w-]+", sel)) + len(re.findall(r"\[[^\]]*\]", sel))
    typ = len(re.findall(r"(?:^|\s)([a-zA-Z][\w-]*)", sel))
    return (ids, cls, typ)


def _matches_simple(node, part: str) -> bool:
    m = _SIMPLE.match(part)
    if not m:
        return False
    tag, rest = m.group(1), m.group(2) or ""
    if tag and tag != "*" and node.tag != tag.lower():
        return False
    classes = set((node.get("class") or "").split())
    for tok in re.findall(r"[.#][\w-]+", rest):
        if tok[0] == ".":
            if tok[1:] not in classes:
                return False
        elif node.get("id") != tok[1:]:
            return False
    return True


def matches(node, sel: str) -> bool:
    """Descendant combinators only, right to left."""
    if sel == ":root":
        return node.tag == "html"
    parts = sel.split()
    if not parts:
        return False
    if not _matches_simple(node, parts[-1]):
        return False
    cur = node.parent
    for part in reversed(parts[:-1]):
        while cur is not None and not _matches_simple(cur, part):
            cur = cur.parent
        if cur is None:
            return False
        cur = cur.parent
    return True


def declared(node, ruleset, prop: str):
    """The winning value of one property for one element, or None."""
    best, best_key = None, None
    for sel, decls, order in ruleset:
        if prop not in decls:
            continue
        if not matches(node, sel):
            continue
        key = specificity(sel) + (order,)
        if best_key is None or key > best_key:
            best, best_key = decls[prop], key
    return best


def _bg_of(node, ruleset):
    """(value, painted_image). The second half matters: if something in
    the chain paints a picture or a gradient, the colour underneath is
    not what the text sits on and nothing I can read from a stylesheet
    will tell me what is. That is a measurement I cannot make, not a
    failure, and I already drew that line elsewhere."""
    short = declared(node, ruleset, "background")
    img = bool(short and re.search(r"url\(|gradient", short, re.I))
    if not img:
        for prop in ("background-image",):
            s = declared(node, ruleset, prop)
            if s and re.search(r"url\(|gradient", s, re.I):
                img = True
    v = declared(node, ruleset, "background-color")
    if v is None and short and not img:
        v = short.strip().split()[0] if short.strip() else None
    return v, img


def _is_hidden(node, ruleset) -> bool:
    """display:none anywhere up the chain means nothing renders.

    I was measuring a sign-in modal and an easter-egg panel that are
    display:none at rest and reporting their contrast as failures. Text
    nobody can see has no contrast to fail.

    visibility:hidden and opacity:0 are deliberately NOT treated the
    same. opacity:0 is how I write a scroll reveal, and that text does
    appear a moment later, so it still has to pass.
    """
    cur = node
    while cur is not None:
        if "display:none" in (cur.get("style") or "").replace(" ", ""):
            return True
        if cur.has("hidden"):
            return True
        v = declared(cur, ruleset, "display")
        if v and v.strip().lower() == "none":
            return True
        cur = cur.parent
    return False


def _is_colour_emoji(text: str) -> bool:
    """Text made only of characters the font paints in its own colours.

    A colour emoji ignores the CSS `color` property entirely, so
    measuring the inherited text colour against the background says
    nothing about whether anybody can see it. On poticas this reported
    thirteen failures for things like a wheat glyph and a package glyph.

    Deliberately narrow: the astral emoji planes, and anything carrying
    the emoji variation selector U+FE0F. A typographic symbol like the
    four-pointed star U+2726 DOES take a CSS colour, so it stays
    measured, and a label that mixes a glyph with real words is still
    real words and stays measured too.
    """
    s = text.strip()
    if not s:
        return False
    if "️" in s:
        s = s.replace("️", "").replace("‍", "")
        return bool(s) and all(ord(c) >= 0x2600 or c.isspace() for c in s)
    return all(ord(c) >= 0x1F000 or c.isspace() for c in s)


def _is_inactive(node) -> bool:
    """WCAG 1.4.3 does not apply to an inactive component. I check the
    attributes that actually mean it and not somebody's class name."""
    cur = node
    while cur is not None:
        if cur.has("disabled"):
            return True
        if (cur.get("aria-disabled") or "").strip().lower() == "true":
            return True
        if (cur.get("aria-hidden") or "").strip().lower() == "true":
            return True
        cur = cur.parent
    return False


def text_pairs(doc, css: str, assume=(255, 255, 255)):
    """What each piece of text is, and what it sits on.

    Returns a list of dicts with a `verdict` that is one of:

      measured     a real ratio for text that renders
      unmeasurable an image or gradient is in the way, or the text is
                   fully transparent at rest. Not a pass and not a fail;
                   somebody has to look at the pixels.
      exempt       an inactive or aria-hidden component, which 1.4.3
                   does not cover

    Only elements holding their own text are measured. A rule that sets
    a colour on something with no text in it describes nothing a person
    can read, and reporting those is how I got a failure on the desktop
    teal behind my own window.
    """
    ruleset = rules(css)
    out = []
    for node in doc.walk():
        if node.tag in ("script", "style", "head", "title", "meta", "link"):
            continue
        if not (node.text or "").strip():
            continue
        fg_raw = None
        cur = node
        while cur is not None and fg_raw is None:
            fg_raw = declared(cur, ruleset, "color")
            cur = cur.parent
        # EVERY layer, not the first one. A translucent panel over a dark
        # section is not the colour of the panel, and compositing the
        # first background I met onto an assumed white page turned a
        # white button on a dark hero into white-on-white. So I collect
        # the stack from the element up to the root and flatten it from
        # the bottom, which is the order a browser paints in.
        layers, over_image = [], False
        cur = node
        while cur is not None:
            v, img = _bg_of(cur, ruleset)
            if img:
                over_image = True
                break
            if v:
                c = parse_rgba(v)
                if c and c[3] > 0:
                    layers.append((v, c))
                    if c[3] >= 1.0:
                        break
            cur = cur.parent
        bg_raw, bg_rgba = None, None
        if layers:
            flat = composite(layers[-1][1], assume)
            for raw, c in reversed(layers[:-1]):
                flat = composite(c, flat)
            bg_raw = layers[0][0]
            bg_rgba = (flat[0], flat[1], flat[2], 1.0)
        if not fg_raw:
            continue
        fg_rgba = parse_rgba(fg_raw)
        if not fg_rgba:
            continue
        where = node.tag + (("." + (node.get("class") or "").split()[0])
                            if node.get("class") else "")
        row = dict(where=where, fg=fg_raw.strip(),
                   bg=(bg_raw or "").strip(), ratio=None,
                   translucent=False, verdict="unmeasurable", why="")
        if _is_inactive(node):
            row["verdict"] = "exempt"
            row["why"] = "inactive or aria-hidden component"
            out.append(row)
            continue
        if _is_hidden(node, ruleset):
            row["verdict"] = "exempt"
            row["why"] = "display:none at rest, so nothing renders"
            out.append(row)
            continue
        if _is_colour_emoji(node.text or ""):
            row["verdict"] = "exempt"
            row["why"] = ("a colour emoji, which the font paints and the "
                          "CSS colour does not reach")
            out.append(row)
            continue
        if over_image:
            row["why"] = "an image or gradient is painted behind this text"
            out.append(row)
            continue
        if fg_rgba[3] == 0:
            row["why"] = ("the text colour is fully transparent at rest, "
                          "which usually means it animates in")
            out.append(row)
            continue
        if not bg_rgba:
            row["why"] = "nothing in the chain declares a background colour"
            out.append(row)
            continue
        flat_bg = composite(bg_rgba, assume)
        flat_fg = composite(fg_rgba, flat_bg)
        row["ratio"] = ratio(flat_fg, flat_bg)
        row["translucent"] = fg_rgba[3] < 1.0 or bg_rgba[3] < 1.0
        row["verdict"] = "measured"
        out.append(row)
    return out
