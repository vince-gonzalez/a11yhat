"""
Robust - WCAG Principle 4 crew lead. Content must be robust enough for assistive
technology. Name/role/value is the heart of it, so the accessible name of every
interactive element is checked directly; parsing (duplicate ids) is deterministic;
status messages are flagged for the dynamic-content pass.
"""
from __future__ import annotations

from collections import Counter

from base import FAIL, NA, PASS, REVIEW, Crew

NAMED_ROLE_NEEDS = {
    "checkbox": "aria-checked", "switch": "aria-checked", "radio": "aria-checked",
    "slider": "aria-valuenow", "combobox": "aria-expanded", "tab": "aria-selected",
}


class Robust(Crew):
    principle_num = "4"

    # ---- 4.1.1 Parsing / duplicate ids (Topic 20) ----
    def sc_411_parsing(self):
        ids = [e.get("id") for e in self.doc.walk() if e.has("id") and e.get("id")]
        dups = [i for i, n in Counter(ids).items() if n > 1]
        self.record("4.1.1", "A", "Parsing (unique ids)", "Topic 20 Parsing",
                    FAIL if dups else PASS,
                    ([f"duplicate id(s): {', '.join(dups[:6])}"] if dups else []),
                    f"{len(ids)} ids, {len(dups)} duplicated")

    # ---- 4.1.2 Name, role, value (Topics 4/5/6) ----
    def sc_412_namerolevalue(self):
        nameless, roleless_widget = [], []
        for el in self.doc.walk():
            if not el.is_interactive():
                continue
            name = (el.inner_text() or el.get("aria-label") or el.get("aria-labelledby")
                    or el.get("title") or el.get("alt") or el.get("value")
                    or el.get("placeholder") or "").strip()
            if not name:
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
        total = sum(1 for e in self.doc.walk() if e.is_interactive())
        if not total:
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
