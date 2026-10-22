"""
Robust - WCAG Principle 4 crew lead. Content must be robust enough for assistive
technology. Name/role/value is the heart of it, so the accessible name of every
interactive element is checked directly; parsing (duplicate ids) is deterministic;
status messages are flagged for the dynamic-content pass.
"""
from __future__ import annotations

from collections import Counter

from .base import FAIL, NA, PASS, REVIEW, Crew

NAMED_ROLE_NEEDS = {
    "checkbox": "aria-checked", "switch": "aria-checked", "radio": "aria-checked",
    "slider": "aria-valuenow", "combobox": "aria-expanded", "tab": "aria-selected",
}


class Robust(Crew):
    principle_num = "4"

    # ---- 4.1.1 Parsing (Topic 20) ----
    def sc_411_parsing(self):
        """4.1.1 WAS REMOVED IN WCAG 2.2, and this tool says 2.2 on the
        tin. Reporting it as a live 2.2 criterion is the kind of thing a
        reviewer catches, and a VPAT built on it is wrong in a way the
        reader cannot see.

        I keep the measurement, because a duplicated id really does
        break a label's for=, an aria-labelledby and a skip link, and
        that damage is real. It is reported against 4.1.2 Name, role,
        value, which is where the harm actually lands, and 4.1.1 itself
        now records what it is: obsolete, carried for 2.0 and 2.1 work.

        I could not reach w3.org from the machine that wrote this to
        confirm the removal at source. It is recorded here as my
        understanding, and before this tool is used for a conformance
        claim somebody should read the spec and settle it.
        """
        ids = [e.get("id") for e in self.doc.walk()
               if e.has("id") and e.get("id")]
        dups = [i for i, n in Counter(ids).items() if n > 1]
        detail = ["removed from WCAG 2.2 as obsolete; the measurement is kept "
                  "for 2.0 and 2.1 work, and a duplicated id is reported "
                  "against 4.1.2 where it actually does harm"]
        if dups:
            detail.append("duplicate id(s): %s" % ", ".join(dups[:6]))
        self.record("4.1.1", "A", "Parsing (obsolete in 2.2)",
                    "Topic 20 Parsing", NA, detail,
                    "%d ids, %d duplicated" % (len(ids), len(dups)))

    def _broken_id_refs(self):
        """The half of 4.1.1 that still bites, under the criterion that
        owns it. A duplicated id means a label's for=, an
        aria-labelledby or a skip link points at whichever element the
        browser happened to index first."""
        ids = [e.get("id") for e in self.doc.walk()
               if e.has("id") and e.get("id")]
        dups = {i for i, n in Counter(ids).items() if n > 1}
        if not dups:
            return
        referenced = set()
        for e in self.doc.walk():
            for attr in ("for", "aria-labelledby", "aria-describedby",
                         "aria-controls", "href"):
                v = (e.get(attr) or "").strip()
                if attr == "href":
                    if v.startswith("#"):
                        referenced.add(v[1:])
                else:
                    referenced.update(v.split())
        broken = sorted(dups & referenced)
        return broken

    # ---- 4.1.2 Name, role, value (Topics 4/5/6) ----
    def sc_412_namerolevalue(self):
        labels_for = {l.get("for") for l in self.doc.find("label") if l.has("for")}
        nameless, roleless_widget = [], []
        for el in self.doc.walk():
            if not el.is_interactive():
                continue
            name = (el.inner_text() or el.get("aria-label") or el.get("aria-labelledby")
                    or el.get("title") or el.get("alt") or el.get("value")
                    or el.get("placeholder") or "").strip()
            associated = el.get("id") in labels_for or (el.parent and el.parent.tag == "label")
            if not name and not associated:
                nameless.append(el.tag + (f"[{el.role()}]" if el.role() else ""))
            role = el.role()
            if role in NAMED_ROLE_NEEDS and not el.has(NAMED_ROLE_NEEDS[role]):
                roleless_widget.append(f"{role} missing {NAMED_ROLE_NEEDS[role]}")
        detail = []
        if nameless:
            detail.append(f"{len(nameless)} interactive element(s) with no accessible name: "
                          f"{', '.join(sorted(set(nameless))[:4])}")
        if roleless_widget:
            detail.append(f"custom widget(s) missing a required state: "
                          f"{', '.join(sorted(set(roleless_widget))[:4])}")
        broken = self._broken_id_refs()
        if broken:
            detail.append("duplicated id(s) that a for=, aria-labelledby, "
                          "aria-controls or skip link points at, so the "
                          "reference resolves to whichever one the browser "
                          "indexed first: " + ", ".join(broken))
        total = sum(1 for e in self.doc.walk() if e.is_interactive())
        if not total and not broken:
            self.record("4.1.2", "A", "Name, role, value", "Topic 5 Forms / 4 Controls", NA,
                        measurement="no interactive elements")
            return
        self.record("4.1.2", "A", "Name, role, value", "Topic 5 Forms / 4 Controls",
                    FAIL if detail else PASS, detail,
                    f"{total} interactive, {len(nameless)} unnamed")

    # ---- 4.1.3 Status messages (AA) ----
    def sc_413_status(self):
        live = [e for e in self.doc.walk()
                if e.has("aria-live") or e.role() in ("status", "alert", "log")]
        self.record("4.1.3", "AA", "Status messages", "Topic (dynamic content)", REVIEW,
                    [f"confirm dynamic updates (errors, cart counts, results) are announced via a "
                     f"live region ({len(live)} aria-live/status region(s) present)"],
                    f"{len(live)} live region(s)")
