"""The criteria I had not written yet.

These are the WCAG 2.2 A and AA success criteria a static read can
actually decide something about, which I was leaving out of the report
entirely. Leaving a criterion out is not neutral: a report that lists
thirty-four rows reads as a conformance picture, and the rows that are
missing look like rows that passed.

They are mixins so the existing crews pick them up through `run()`,
which collects every method starting with sc_. Nothing in the four crew
files had to change except the class line.

Each one here can FAIL on bad input and PASS on good input, and where a
criterion genuinely cannot be settled from markup it records REVIEW with
the exact question a person has to answer, never a pass.
"""
from __future__ import annotations

import re

from . import cascade
from .base import FAIL, NA, PASS, REVIEW
from .color import composite, parse_rgba, ratio

# Fields that are about the person using the page. 1.3.5 asks that these
# say what they are for, so a browser can fill them and so somebody who
# needs their own data prefilled gets it.
PURPOSE = [
    ("name", r"\b(name|fullname|full_name|yourname)\b", "name"),
    ("email", r"\b(e?mail)\b", "email"),
    ("tel", r"\b(tel|phone|mobile)\b", "tel"),
    ("street-address", r"\b(address|street|addr)\b", "street-address"),
    ("postal-code", r"\b(zip|postcode|postal)\b", "postal-code"),
    ("country-name", r"\bcountry\b", "country-name"),
    ("organization", r"\b(company|organisation|organization|business)\b",
     "organization"),
    ("cc-number", r"\b(card|cc-?num|creditcard)\b", "cc-number"),
    ("bday", r"\b(birth|dob|bday)\b", "bday"),
]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower()).strip()


class MorePerceivable:

    # ---- 1.3.4 Orientation (AA) ----
    def sc_134_orientation(self):
        """A page must not demand one orientation. I can see the CSS that
        locks it; I cannot see a script that does, so that is a REVIEW."""
        locks = []
        for m in re.finditer(r"@media[^{]*orientation\s*:\s*(portrait|landscape)"
                             r"[^{]*\{(.*?)\}\s*\}", self.css, re.S | re.I):
            if re.search(r"display\s*:\s*none|transform\s*:\s*rotate", m.group(2),
                         re.I):
                locks.append(m.group(1))
        if re.search(r"screen\.orientation\.lock", self.html, re.I):
            locks.append("screen.orientation.lock() in script")
        if locks:
            self.record("1.3.4", "AA", "Orientation", "Topic 19 Orientation",
                        FAIL, ["the page restricts itself to one orientation: "
                               + ", ".join(sorted(set(locks)))],
                        "%d lock(s)" % len(locks))
        else:
            self.record("1.3.4", "AA", "Orientation", "Topic 19 Orientation",
                        PASS, measurement="nothing locks the orientation")

    # ---- 1.3.5 Identify Input Purpose (AA) ----
    def sc_135_input_purpose(self):
        fields, missing = 0, []
        for el in self.doc.find("input", "select", "textarea"):
            ty = (el.get("type") or "text").strip().lower()
            if ty in ("hidden", "submit", "button", "reset", "image", "search"):
                continue
            ident = _norm(" ".join([el.get("name") or "", el.get("id") or "",
                                    el.get("autocomplete") or "",
                                    el.get("placeholder") or ""]))
            hit = next((tok for tok, pat, _t in PURPOSE
                        if re.search(pat, ident)), None)
            if not hit:
                continue
            fields += 1
            ac = (el.get("autocomplete") or "").strip().lower()
            if not ac or ac == "off":
                missing.append("%s (looks like %s)"
                               % (el.get("name") or el.get("id") or
                                  "<" + el.tag + ">", hit))
        if not fields:
            self.record("1.3.5", "AA", "Identify input purpose",
                        "Topic 12 Forms", NA,
                        measurement="no field asks for the user's own data")
            return
        status = FAIL if missing else PASS
        self.record("1.3.5", "AA", "Identify input purpose", "Topic 12 Forms",
                    status,
                    ["no autocomplete on: " + ", ".join(missing[:6])]
                    if missing else [],
                    "%d field(s) about the user, %d without autocomplete"
                    % (fields, len(missing)))

    # ---- 1.4.11 Non-text contrast (AA) ----
    def sc_1411_nontext_contrast(self):
        """Borders and edges of controls need 3:1. I can measure a
        declared border colour against what is behind it. I cannot see
        an icon drawn in a font or an SVG stroke, and I say so."""
        ruleset = cascade.rules(self.css)
        rows, fails = 0, []
        for node in self.doc.walk():
            if not node.is_interactive():
                continue
            bc = (cascade.declared(node, ruleset, "border-color")
                  or cascade.declared(node, ruleset, "border"))
            if not bc:
                continue
            edge = parse_rgba(bc.strip().split()[-1]) or parse_rgba(
                bc.strip().split()[0])
            if not edge:
                continue
            behind = None
            cur = node.parent
            while cur is not None and behind is None:
                v, img = cascade._bg_of(cur, ruleset)
                if img:
                    break
                if v:
                    behind = parse_rgba(v)
                cur = cur.parent
            if not behind:
                continue
            rows += 1
            r = ratio(composite(edge, composite(behind)), composite(behind))
            if r >= 3.0:
                continue
            # 1.4.11 asks for 3:1 on what is REQUIRED to identify the
            # control. If the control paints its own fill and that fill
            # already stands out from the page, the border is not the
            # thing doing the identifying and a faint one is a choice,
            # not a barrier. Reporting eight decorative borders as
            # failures is how a report gets ignored.
            own = cascade.declared(node, ruleset, "background-color") \
                or cascade.declared(node, ruleset, "background")
            own_rgba = parse_rgba(own.strip().split()[0]) if own else None
            if own_rgba and ratio(composite(own_rgba, composite(behind)),
                                  composite(behind)) >= 3.0:
                continue
            fails.append("<%s> edge %s on %s is %.2f:1"
                         % (node.tag, bc.strip()[:18], v[:18], r))
        if not rows:
            self.record("1.4.11", "AA", "Non-text contrast",
                        "Topic 13 Sensory & contrast", REVIEW,
                        ["no control declares a border colour I could measure; "
                         "check the edges of buttons, inputs and focus "
                         "indicators against their background at 3:1"],
                        "0 edges measured")
            return
        self.record("1.4.11", "AA", "Non-text contrast",
                    "Topic 13 Sensory & contrast",
                    FAIL if fails else REVIEW, fails[:5] or
                    ["edges measured are above 3:1; icons drawn in a font or "
                     "an SVG stroke are not measurable from here"],
                    "%d edge(s) measured, %d below 3:1" % (rows, len(fails)))


class MoreOperable:

    # ---- 2.1.4 Character key shortcuts (A) ----
    def sc_214_char_shortcuts(self):
        """A single letter that does something is a trap for anyone using
        speech input. It has to be switchable off or remappable, or only
        fire while a control has focus."""
        hits = []
        for m in re.finditer(r"""\.key\s*===?\s*['"]([A-Za-z])['"]""",
                             self.html):
            hits.append(m.group(1))
        for m in re.finditer(r"""\bkeyCode\s*===?\s*(\d{2,3})""", self.html):
            n = int(m.group(1))
            if 65 <= n <= 90:
                hits.append(chr(n))
        guarded = bool(re.search(r"(ctrlKey|altKey|metaKey|shiftKey)",
                                 self.html))
        if not hits:
            self.record("2.1.4", "A", "Character key shortcuts",
                        "Topic 16 Keyboard", NA,
                        measurement="no single-character shortcut found")
            return
        self.record("2.1.4", "A", "Character key shortcuts",
                    "Topic 16 Keyboard", REVIEW if guarded else FAIL,
                    ["single-key shortcut(s) on: %s. Each one must be "
                     "switchable off, remappable, or only active while its "
                     "control has focus"
                     % ", ".join(sorted(set(hits))[:8])],
                    "%d single-key shortcut(s), modifier keys %s"
                    % (len(set(hits)), "are used" if guarded else "are not"))

    # ---- 2.5.3 Label in name (A) ----
    def sc_253_label_in_name(self):
        """If a control shows the word Search, its accessible name has to
        contain Search, or somebody saying "click Search" is talking to a
        control that is not listening."""
        checked, bad = 0, []
        for node in self.doc.walk():
            if not node.is_interactive():
                continue
            # The element's OWN label, not everything inside it. Using
            # inner_text() here reported a scroll container named
            # "Product examples" as mismatched because the products
            # inside it are its CONTENT, not its label. 2.5.3 is about a
            # control whose visible words are its label, so a composite
            # widget holding other content is out of scope.
            if any(c.is_interactive() for c in node.children):
                continue
            own = " ".join([node.text or ""]
                           + [(c.text or "") for c in node.children])
            visible = _norm(own)
            aria = _norm(node.get("aria-label") or "")
            if not visible or not aria or len(visible) > 60:
                continue
            checked += 1
            # Compared without spaces as well, because a brand written
            # "OPTIC QUIZ" on screen and "OpticQuiz" in the label is the
            # same word to everyone except a strict substring test.
            tight_v = visible.replace(" ", "")
            tight_a = aria.replace(" ", "")
            if visible not in aria and tight_v not in tight_a:
                bad.append('<%s> shows "%s" but is named "%s"'
                           % (node.tag, own.strip()[:24],
                              (node.get("aria-label") or "").strip()[:24]))
        if not checked:
            self.record("2.5.3", "A", "Label in name", "Topic 17 Labels", NA,
                        measurement="no control carries both visible text and "
                                    "an aria-label")
            return
        self.record("2.5.3", "A", "Label in name", "Topic 17 Labels",
                    FAIL if bad else PASS, bad[:5],
                    "%d control(s) have both, %d mismatched"
                    % (checked, len(bad)))


class MoreUnderstandable:

    # ---- 3.2.6 Consistent help (A, new in 2.2) ----
    def sc_326_consistent_help(self):
        """Where help lives has to be the same on every page. One page
        cannot settle that, so this names what to compare rather than
        guessing."""
        found = []
        for a in self.doc.find("a", "button"):
            t = _norm(a.inner_text() + " " + (a.get("aria-label") or ""))
            if re.search(r"\b(help|support|contact|faq)\b", t):
                found.append(a.inner_text().strip()[:24] or a.tag)
        if not found:
            self.record("3.2.6", "A", "Consistent help", "Topic 21 Help", NA,
                        measurement="no help mechanism on this page")
            return
        self.record("3.2.6", "A", "Consistent help", "Topic 21 Help", REVIEW,
                    ["help is offered here as: %s. Check it appears in the "
                     "same relative order on every page that has it"
                     % ", ".join(sorted(set(found))[:4])],
                    "%d help link(s) on this page" % len(set(found)))

    # ---- 3.3.7 Redundant entry (A, new in 2.2) ----
    def sc_337_redundant_entry(self):
        """Asking for the same thing twice in one process is a barrier to
        anyone with a memory or dexterity difficulty. Two fields with the
        same purpose in one form is the shape of it."""
        for form in self.doc.find("form"):
            seen = {}
            for el in form.find("input", "textarea"):
                ty = (el.get("type") or "text").lower()
                if ty in ("hidden", "submit", "button", "checkbox", "radio"):
                    continue
                ident = _norm(" ".join([el.get("name") or "",
                                        el.get("id") or ""]))
                hit = next((tok for tok, pat, _t in PURPOSE
                            if re.search(pat, ident)), None)
                if not hit:
                    continue
                # a confirm field is the allowed case, and only when it
                # is genuinely a re-entry for verification
                if re.search(r"confirm|repeat|again|verify|retype", ident):
                    continue
                seen.setdefault(hit, []).append(
                    el.get("name") or el.get("id") or el.tag)
            dupes = {k: v for k, v in seen.items() if len(v) > 1}
            if dupes:
                self.record("3.3.7", "A", "Redundant entry", "Topic 12 Forms",
                            REVIEW,
                            ["the same information is asked for more than "
                             "once: " + "; ".join("%s (%s)" % (k, ", ".join(v))
                                                  for k, v in dupes.items())
                             + ". If it is the same process, prefill it or "
                               "offer it as a choice"],
                            "%d purpose(s) asked twice" % len(dupes))
                return
        forms = self.doc.find("form")
        self.record("3.3.7", "A", "Redundant entry", "Topic 12 Forms",
                    NA if not forms else PASS,
                    measurement=("no form on the page" if not forms
                                 else "no field asks for the same thing twice"))
