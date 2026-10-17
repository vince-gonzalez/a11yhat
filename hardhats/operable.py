"""
Operable - WCAG Principle 2 crew lead. UI components and navigation must be
operable. Keyboard and focus-order "sense" can only be confirmed by a human, so
those criteria run a representative measurement (enumerate the controls, catch the
static giveaways) and flag the rest for the keyboard pass.
"""
from __future__ import annotations

import re

from base import FAIL, NA, PASS, REVIEW, Crew

VAGUE_LINK = {"click here", "here", "read more", "more", "link", "this", "learn more",
              "details", "continue", "go", "click", "download"}


class Operable(Crew):
    principle_num = "2"

    # ---- 2.1.1 Keyboard (Topic 4) ----
    def sc_211_keyboard(self):
        mouse_only = []
        for el in self.doc.walk():
            if el.has("onclick") and el.tag not in ("a", "button", "input", "select", "textarea") \
                    and not el.role() and not el.has("tabindex"):
                mouse_only.append(el.tag)
        interactive = [e for e in self.doc.walk() if e.is_interactive()]
        status = FAIL if mouse_only else REVIEW
        detail = []
        if mouse_only:
            detail.append(f"{len(mouse_only)} element(s) with onclick but no role/tabindex "
                          f"(keyboard cannot reach): {', '.join(sorted(set(mouse_only))[:4])}")
        detail.append(f"confirm all {len(interactive)} interactive elements work with Tab/Enter/Space")
        self.record("2.1.1", "A", "Keyboard", "Topic 4 Keyboard access & focus", status, detail,
                    f"{len(interactive)} interactive, {len(mouse_only)} mouse-only")

    # ---- 2.1.2 No keyboard trap (Topic 4) ----
    def sc_212_trap(self):
        self.record("2.1.2", "A", "No keyboard trap", "Topic 4 Keyboard access & focus", REVIEW,
                    ["tab through the page; focus must never get stuck in a widget or dialog"],
                    "manual")

    # ---- 2.2.1 / 2.2.2 Timing & moving content (Topics 8, 2) ----
    def sc_221_timing(self):
        refresh = re.search(r'<meta[^>]+http-equiv=["\']refresh["\'][^>]*content=["\'](\d+)', self.html, re.I)
        if refresh and int(refresh.group(1)) > 0:
            self.record("2.2.1", "A", "Timing adjustable", "Topic 8 Adjustable time limits", FAIL,
                        [f"meta refresh after {refresh.group(1)}s with no user control"],
                        f"refresh={refresh.group(1)}s")
        else:
            self.record("2.2.1", "A", "Timing adjustable", "Topic 8 Adjustable time limits", REVIEW,
                        ["no auto-refresh found; confirm any session/interaction time limits are "
                         "adjustable"], "no meta-refresh")

    def sc_222_moving(self):
        moving = len(self.doc.find("marquee", "blink"))
        anim = len(re.findall(r"@keyframes|animation\s*:", self.css, re.I))
        autop = len([m for m in self.doc.find("audio", "video") if m.has("autoplay")])
        n = moving + anim + autop
        self.record("2.2.2", "A", "Pause, stop, hide", "Topic 2 Auto-updating content",
                    FAIL if moving else (REVIEW if n else PASS),
                    ([f"moving/auto-updating content: {moving} marquee, {anim} CSS animation, "
                      f"{autop} autoplay - must be pausable if it runs over 5s"] if n else []),
                    f"{n} moving source(s)")

    # ---- 2.3.1 Three flashes (Topic 3) ----
    def sc_231_flash(self):
        risk = len(self.doc.find("video", "canvas")) + len(re.findall(r"@keyframes", self.css, re.I))
        self.record("2.3.1", "A", "Three flashes or below", "Topic 3 Flashing",
                    REVIEW if risk else PASS,
                    (["nothing may flash more than 3 times per second; review video/animation"]
                     if risk else []), f"{risk} animation/video source(s)")

    # ---- 2.4.1 Bypass blocks (Topic 9) ----
    def sc_241_bypass(self):
        skip = any("skip" in (a.inner_text() or "").lower() for a in self.doc.find("a") if a.has("href"))
        landmark = bool(self.doc.find("main") or any(e.role() == "main" for e in self.doc.walk()))
        ok = skip or landmark
        self.record("2.4.1", "A", "Bypass blocks", "Topic 9 Repetitive content",
                    PASS if ok else FAIL,
                    ([] if ok else ["no skip link and no <main>/role=main landmark to bypass "
                                    "repeated navigation"]),
                    f"skip-link={skip}, main={landmark}")

    # ---- 2.4.2 Page titled (Topic 12) ----
    def sc_242_title(self):
        t = self.doc.find("title")
        text = t[0].inner_text() if t else ""
        self.record("2.4.2", "A", "Page titled", "Topic 12 Page titles & frames",
                    PASS if text.strip() else FAIL,
                    ([] if text.strip() else ["missing or empty <title>"]),
                    f'title="{text[:40]}"')

    # ---- 2.4.3 Focus order (Topic 4) ----
    def sc_243_focusorder(self):
        pos = [int(e.get("tabindex")) for e in self.doc.walk()
               if e.get("tabindex", "").lstrip("-").isdigit() and int(e.get("tabindex")) > 0]
        self.record("2.4.3", "A", "Focus order", "Topic 4 Keyboard access & focus",
                    FAIL if pos else REVIEW,
                    ([f"{len(pos)} positive tabindex value(s) override natural order"] if pos
                     else ["confirm the tab order follows the visual/reading order"]),
                    f"{len(pos)} positive tabindex")

    # ---- 2.4.4 Link purpose (Topic 6) ----
    def sc_244_linkpurpose(self):
        empty, vague = [], []
        for a in self.doc.find("a"):
            if not a.has("href"):
                continue
            txt = (a.inner_text() or a.get("aria-label") or a.get("title") or "").strip().lower()
            if not txt:
                empty.append(a.get("href", "")[:30])
            elif txt in VAGUE_LINK:
                vague.append(txt)
        detail = []
        if empty:
            detail.append(f"{len(empty)} link(s) with no text/label")
        if vague:
            detail.append(f"non-descriptive link text: {', '.join(sorted(set(vague))[:5])}")
        self.record("2.4.4", "A", "Link purpose (in context)", "Topic 6 Links",
                    FAIL if empty else (REVIEW if vague else PASS), detail,
                    f"{len(self.doc.find('a'))} links, {len(empty)} empty, {len(vague)} vague")

    # ---- 2.4.5 Multiple ways (Topic 19) ----
    def sc_245_multiple(self):
        nav = len(self.doc.find("nav")) or sum(1 for e in self.doc.walk() if e.role() == "navigation")
        search = bool([i for i in self.doc.find("input") if i.get("type") == "search"]) \
            or "search" in self.html.lower()
        ways = (1 if nav else 0) + (1 if search else 0)
        self.record("2.4.5", "AA", "Multiple ways", "Topic 19 Multiple ways", REVIEW,
                    [f"confirm at least two ways to find pages (nav={bool(nav)}, search={search}); "
                     "a sitemap or site search counts"], f"{ways} way(s) detected")

    # ---- 2.4.6 Headings and labels (AA) ----
    def sc_246_headings(self):
        empty_h = [h.tag for h in self.doc.find("h1", "h2", "h3", "h4", "h5", "h6")
                   if not h.inner_text().strip()]
        self.record("2.4.6", "AA", "Headings and labels", "Topic 10 Content structure",
                    FAIL if empty_h else REVIEW,
                    ([f"{len(empty_h)} empty heading(s)"] if empty_h
                     else ["confirm headings and labels describe their topic or purpose"]),
                    f"{len(empty_h)} empty headings")

    # ---- 2.4.7 Focus visible (Topic 4, AA) ----
    def sc_247_focusvisible(self):
        blocks = re.findall(r"(:focus(?:-visible)?[^{]*)\{([^}]*)\}", self.css, re.I)
        if not blocks:
            self.record("2.4.7", "AA", "Focus visible", "Topic 4 Keyboard access & focus", REVIEW,
                        ["no :focus style found; confirm the browser default focus ring is visible "
                         "and not suppressed elsewhere"], "no :focus rule")
            return
        bad = []
        for sel, body in blocks:
            b = body.lower()
            removes = re.search(r"outline\s*:\s*(none|0)\b", b)
            replaces = (re.search(r"box-shadow\s*:\s*(?!none)", b)
                        or re.search(r"border(-[a-z]+)?\s*:\s*(?!none|0\b)\S", b)
                        or re.search(r"outline\s*:\s*(?!none|0\b)\S", b))
            if removes and not replaces:
                bad.append(sel.strip())
        self.record("2.4.7", "AA", "Focus visible", "Topic 4 Keyboard access & focus",
                    FAIL if bad else PASS,
                    ([f"focus outline removed with no visible replacement: {bad[0]}"] if bad else []),
                    f"{len(blocks)} focus rule(s), {len(bad)} suppressed")
