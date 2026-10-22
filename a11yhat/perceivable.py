"""
Perceivable - WCAG Principle 1 crew lead. Information and UI components must be
presentable in ways users can perceive. Every applicable criterion gets a result;
contrast (1.4.3) is measured, the rest are checked structurally or flagged for
confirmation with the specific thing to look at.
"""
from __future__ import annotations

import re

from .base import FAIL, NA, PASS, REVIEW, Crew
from . import cascade
from .color import composite, parse_rgba, ratio

SENSORY = re.compile(r"\b(round|square|circular|the (left|right|top|bottom)|"
                     r"on the (left|right)|above|below|the (green|red|blue) (button|box|link))\b", re.I)


def css_rules(css: str):
    """Yield (selector, {prop: value}) for each rule block in a stylesheet."""
    for block in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        sel, body = block[0].strip(), block[1]
        decls = {}
        for part in body.split(";"):
            if ":" in part:
                k, v = part.split(":", 1)
                decls[k.strip().lower()] = v.strip()
        if decls:
            yield sel, decls


from .extra import MorePerceivable


class Perceivable(MorePerceivable, Crew):
    principle_num = "1"

    # ---- 1.1.1 Non-text content (Topic 7) ----
    def sc_111_images(self):
        imgs = self.doc.find("img")
        no_alt = [i for i in imgs if not i.has("alt")]
        bad_alt = []
        for i in imgs:
            alt = i.get("alt", "").strip()
            if alt and (re.search(r"\.(png|jpe?g|gif|svg|webp)$", alt, re.I)
                        or re.fullmatch(r"(image|img|photo|picture|icon|logo)\d*", alt, re.I)):
                bad_alt.append(alt[:40])
        svg_unnamed = [s for s in self.doc.find("svg")
                       if s.role() == "img" and not (s.has("aria-label") or s.find("title"))]
        # A canvas is named by aria-label or aria-labelledby just as well
        # as by fallback content, and one marked decorative needs no name
        # at all. Reading inner text alone reported a canvas carrying a
        # correct role="img" and aria-label as having no text
        # alternative - a false FAIL on markup that is right. The svg
        # check two lines up and the control check below already accept
        # aria-label; this one simply did not.
        canvas_bare = [c for c in self.doc.find("canvas")
                       if not (c.inner_text().strip()
                               or c.has("aria-label")
                               or c.has("aria-labelledby")
                               or c.has("aria-hidden")
                               or c.role() == "presentation"
                               or c.role() == "none")]
        detail = []
        if no_alt:
            detail.append(f"{len(no_alt)} <img> without an alt attribute")
        if bad_alt:
            detail.append(f"alt looks like a filename/label: {', '.join(bad_alt[:3])}")
        if svg_unnamed:
            detail.append(f"{len(svg_unnamed)} role=img <svg> with no title/aria-label")
        if canvas_bare:
            detail.append(f"{len(canvas_bare)} <canvas> with no text alternative")
        if not imgs and not self.doc.find("svg", "canvas"):
            self.record("1.1.1", "A", "Non-text content", "Topic 7 Images", NA,
                        measurement="no images on the page")
            return
        status = FAIL if (no_alt or svg_unnamed or canvas_bare) else (REVIEW if bad_alt else PASS)
        self.record("1.1.1", "A", "Non-text content", "Topic 7 Images", status, detail,
                    f"{len(imgs)} img, {len(no_alt)} missing alt")

    # ---- 1.2.x Time-based media (Topics 16, 17) ----
    def sc_12_media(self):
        av = self.doc.find("audio", "video")
        if not av:
            self.record("1.2.1", "A", "Audio/video alternatives", "Topic 16/17 Media", NA,
                        measurement="no audio or video elements")
            return
        tracks = sum(1 for v in av for t in v.find("track") if t.get("kind") == "captions")
        self.record("1.2.2", "A", "Captions & transcripts", "Topic 17 Synchronized media", REVIEW,
                    [f"{len(av)} media element(s); confirm captions, transcript, and audio "
                     f"description (found {tracks} caption track(s))"],
                    f"{len(av)} media, {tracks} caption tracks")

    # ---- 1.3.1 Info and relationships (Topics 10, 14, 5) ----
    def sc_131_structure(self):
        detail = []
        # headings do not skip levels
        levels = [int(h.tag[1]) for h in self.doc.find("h1", "h2", "h3", "h4", "h5", "h6")]
        prev = 0
        for lv in levels:
            if prev and lv > prev + 1:
                detail.append(f"heading jumps from h{prev} to h{lv}")
            prev = lv
        # form controls have a programmatic label
        unlabeled = []
        labels_for = {l.get("for") for l in self.doc.find("label") if l.has("for")}
        for ctl in self.doc.find("input", "select", "textarea"):
            if ctl.get("type", "").lower() in ("hidden", "submit", "button", "reset", "image"):
                continue
            named = (ctl.has("aria-label") or ctl.has("aria-labelledby")
                     or ctl.has("title") or ctl.get("id") in labels_for
                     or (ctl.parent and ctl.parent.tag == "label"))
            if not named:
                unlabeled.append(ctl.get("name") or ctl.get("id") or ctl.tag)
        # data tables have header cells
        headerless = [t for t in self.doc.find("table")
                      if t.find("td") and not (t.find("th") or any(
                          c.get("scope") for c in t.find("td")))]
        if unlabeled:
            detail.append(f"{len(unlabeled)} form control(s) without a label")
        if headerless:
            detail.append(f"{len(headerless)} data table(s) without <th> header cells")
        status = FAIL if detail else PASS
        self.record("1.3.1", "A", "Info and relationships", "Topic 10/14/5 Structure", status,
                    detail, f"{len(levels)} headings, "
                    f"{len(self.doc.find('input','select','textarea'))} controls, "
                    f"{len(self.doc.find('table'))} tables")

    # ---- 1.3.2 Meaningful sequence (Topic 15) ----
    def sc_132_sequence(self):
        reorder = len(re.findall(r"\b(order\s*:\s*-?\d|float\s*:\s*(left|right)|"
                                 r"position\s*:\s*absolute|direction\s*:\s*rtl)\b", self.css, re.I))
        self.record("1.3.2", "A", "Meaningful sequence", "Topic 15 CSS content & positioning",
                    REVIEW if reorder else PASS,
                    ([f"{reorder} CSS rule(s) reorder/position content - confirm the DOM order "
                      f"still reads correctly with CSS off"] if reorder else []),
                    f"{reorder} reordering rules")

    # ---- 1.3.3 Sensory characteristics (Topic 13) ----
    def sc_133_sensory(self):
        hits = set(m.group(0) for m in SENSORY.finditer(self.doc.inner_text()))
        self.record("1.3.3", "A", "Sensory characteristics", "Topic 13 Sensory & contrast",
                    REVIEW if hits else PASS,
                    ([f"instructions may rely on shape/position/color alone: "
                      f"{', '.join(list(hits)[:4])}"] if hits else []),
                    f"{len(hits)} sensory phrase(s)")

    # ---- 1.4.1 Use of color (Topic 13) ----
    def sc_141_color(self):
        links = self.doc.find("a")
        plain = [a for a in links if a.has("href") and "text-decoration" in self.css.lower()
                 and re.search(r"text-decoration\s*:\s*none", self.css, re.I)]
        self.record("1.4.1", "A", "Use of color", "Topic 13 Sensory & contrast", REVIEW,
                    ["confirm no information is conveyed by color alone (links, required fields, "
                     f"states); {('underlines removed via CSS' if plain else 'check in-text links')}"],
                    f"{len(links)} links")

    # ---- 1.4.2 Audio control (Topic 2) ----
    def sc_142_audio(self):
        autop = [m for m in self.doc.find("audio", "video")
                 if m.has("autoplay") and not m.has("muted")]
        self.record("1.4.2", "A", "Audio control", "Topic 2 Auto-playing content",
                    FAIL if autop else PASS,
                    ([f"{len(autop)} media element(s) autoplay sound with no control"] if autop else []),
                    f"{len(autop)} autoplaying")

    # ---- 1.4.3 Contrast (minimum) - MEASURED (Topic 13) ----
    def sc_143_contrast(self):
        """What each piece of text actually sits on.

        I used to measure only rules that set a colour AND a background
        in the same block, which real stylesheets never do, so on three
        of my own sites this measured 0, 0 and 1 pairs. It now resolves
        the cascade: colour inherits, background does not but the
        backdrop a person sees is the nearest ancestor that paints one,
        and translucent layers are flattened bottom-up the way a browser
        paints them.
        """
        rows = cascade.text_pairs(self.doc, self.css)
        if rows:
            return self._contrast_from_cascade(rows)
        return self._contrast_from_declared_pairs()

    def _contrast_from_cascade(self, rows):
        measured = [r for r in rows if r["verdict"] == "measured"]
        unmeasurable = [r for r in rows if r["verdict"] == "unmeasurable"]
        exempt = [r for r in rows if r["verdict"] == "exempt"]
        fails = [r for r in measured if r["ratio"] < r["needs"]]
        translucent = [r for r in measured if r["translucent"]]

        detail, seen = [], set()
        for r in sorted(fails, key=lambda x: x["ratio"]):
            key = (r["where"], r["fg"], r["bg"])
            if key in seen:
                continue
            seen.add(key)
            if len(seen) > 6:
                break
            detail.append("%s: %.2f:1 (%s on %s) at %gpx%s - needs %.1f:1"
                          % (r["where"], r["ratio"], r["fg"], r["bg"],
                             r["px"], " bold" if r["bold"] else "",
                             r["needs"]))
        if len(fails) > len(seen):
            detail.append("%d more text run(s) fail the same way"
                          % (len(fails) - len(seen)))
        for r in unmeasurable[:3]:
            detail.append("%s: not measurable - %s" % (r["where"], r["why"]))
        if translucent and not fails:
            detail.append("%d run(s) use a translucent colour, flattened onto "
                          "the layers behind them; if anything paints between "
                          "them the real ratio differs"
                          % len(translucent))
        if self.css_missed:
            detail.append("could not read %d stylesheet(s) (%s), so these "
                          "colours are a subset of the page's"
                          % (len(self.css_missed),
                             ", ".join(self.css_missed[:3])))
        if self.css_redefined:
            detail.append("%d colour token(s) are redefined elsewhere (%s): "
                          "this is the default theme, and dark mode was not "
                          "measured"
                          % (len(self.css_redefined),
                             ", ".join(self.css_redefined[:4])))
        # A pass is only a pass when nothing was left unresolved.
        unresolved = bool(unmeasurable or translucent or self.css_missed
                          or self.css_redefined)
        status = FAIL if fails else (REVIEW if unresolved else PASS)
        worst = min((r["ratio"] for r in measured), default=0)
        self.record("1.4.3", "AA", "Contrast (minimum)",
                    "Topic 13 Sensory & contrast", status, detail,
                    "%d text run(s) measured, lowest %.2f:1, %d below the bar, "
                    "%d not measurable, %d exempt"
                    % (len(measured), worst, len(fails), len(unmeasurable),
                       len(exempt)))

    def _contrast_from_declared_pairs(self):
        pairs = []        # (ratio, where, fg, bg)
        translucent = []  # where a colour was not opaque

        def measure(fg_raw, bg_raw, where):
            """Composite before measuring. A translucent colour is not the
            colour a person sees, and reading rgba() as if the alpha were
            1.0 scored rgba(0,0,0,0.04) on white at 21:1 when what is on
            the screen is about 1.09:1. The backdrop behind the declared
            background is not knowable from a stylesheet, so white is
            assumed, and the pair is recorded as translucent so the
            verdict can say so instead of claiming a pass it cannot
            support."""
            cf, cb = parse_rgba(fg_raw), parse_rgba(bg_raw)
            if not cf or not cb:
                return
            flat_bg = composite(cb)              # over the page's white
            flat_fg = composite(cf, flat_bg)     # over whatever it sits on
            if cf[3] < 1.0 or cb[3] < 1.0:
                translucent.append(where)
            pairs.append((ratio(flat_fg, flat_bg), where,
                          fg_raw.strip(), bg_raw.strip()))

        # inline styles that set both color and a background
        for el in self.doc.walk():
            st = el.get("style", "").lower()
            fg = re.search(r"(?<!-)color\s*:\s*([^;]+)", st)
            bg = re.search(r"background(?:-color)?\s*:\s*([^;]+)", st)
            if fg and bg:
                measure(fg.group(1), bg.group(1), f"<{el.tag} style>")
        # stylesheet rules that set both
        for sel, decls in css_rules(self.css):
            if "color" in decls and ("background" in decls or "background-color" in decls):
                measure(decls["color"],
                        decls.get("background-color") or decls.get("background", ""),
                        sel.strip()[:40])
        if not pairs:
            self.record("1.4.3", "AA", "Contrast (minimum)", "Topic 13 Sensory & contrast", REVIEW,
                        ["no element declares both text and background color; measure rendered "
                         "contrast with a tool (needs 4.5:1 normal, 3:1 large text)"], "0 pairs measured")
            return
        fails = [p for p in pairs if p[0] < 4.5]
        worst = min(pairs, key=lambda p: p[0])
        detail = [f"{w}: {r:.2f}:1 ({fg} on {bg}) - below 4.5:1"
                  for r, w, fg, bg in sorted(fails)[:5]]
        # text painted over an IMAGE cannot be measured from stylesheet colors: never call that a pass
        images = [sel.strip()[:40] for sel, decls in css_rules(self.css)
                  if re.search(r"url\(", (decls.get("background", "") + " " + decls.get("background-image", "")), re.I)]
        images += [f"<{el.tag} style>" for el in self.doc.walk()
                   if re.search(r"background(?:-image)?\s*:[^;]*url\(", el.get("style", ""), re.I)]
        status = FAIL if fails else (REVIEW if (images or translucent) else PASS)
        if images and not fails:
            detail.append(f"{len(images)} rule(s) paint a background image ({', '.join(images[:4])}): text over an image "
                          "cannot be measured from stylesheet colors; measure the rendered pixels")
        if translucent and not fails:
            # A composite over an ASSUMED white backdrop is a measurement
            # with an assumption in it. If the real backdrop is darker the
            # number moves, so this cannot be reported as a clean pass.
            detail.append(f"{len(translucent)} pair(s) use a translucent colour "
                          f"({', '.join(translucent[:4])}): measured by compositing over "
                          "white, which is what an unstyled page is. If anything darker sits "
                          "behind them the real ratio is lower - check the rendered pixels")
        self.record("1.4.3", "AA", "Contrast (minimum)", "Topic 13 Sensory & contrast",
                    status, detail,
                    f"{len(pairs)} pairs measured, lowest {worst[0]:.2f}:1, {len(fails)} below 4.5:1, "
                    f"{len(images)} image background(s), {len(translucent)} translucent")

    # ---- 1.4.4 Resize text (Topic 18) ----
    def sc_144_resize(self):
        detail = []
        vp = re.search(r'<meta[^>]+name=["\']viewport["\'][^>]*>', self.html, re.I)
        if vp and re.search(r"user-scalable\s*=\s*no|maximum-scale\s*=\s*(1(\.0)?|0)", vp.group(0), re.I):
            detail.append("viewport blocks zoom (user-scalable=no / maximum-scale<=1)")
        tiny = sorted(set(int(m.group(1)) for m in re.finditer(r"font-size\s*:\s*(\d+)px", self.css)
                          if int(m.group(1)) < 13))
        if tiny:
            detail.append(f"font-size below 13px floor: {', '.join(f'{p}px' for p in tiny)}")
        self.record("1.4.4", "AA", "Resize text", "Topic 18 Resize text",
                    FAIL if any("blocks zoom" in d for d in detail) else (REVIEW if tiny else PASS),
                    detail, f"zoom blocked: {bool(vp and 'detail' and any('blocks' in d for d in detail))}")

    # ---- 1.4.5 Images of text (Topic 7/13) ----
    def sc_145_imgtext(self):
        imgs = self.doc.find("img")
        if not imgs:
            self.record("1.4.5", "AA", "Images of text", "Topic 7 Images", NA,
                        measurement="no images")
            return
        self.record("1.4.5", "AA", "Images of text", "Topic 7 Images", REVIEW,
                    [f"confirm none of the {len(imgs)} images are pictures of text that could be "
                     "real text (logos are exempt)"], f"{len(imgs)} images to review")
