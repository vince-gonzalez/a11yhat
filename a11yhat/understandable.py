"""
Understandable - WCAG Principle 3 crew lead. Content and operation must be
understandable. Language is checked deterministically; predictability and input
assistance are confirmed by a representative measurement (what forms/controls
exist, what is required) plus the human check each one needs.
"""
from __future__ import annotations

import re

from .base import FAIL, NA, PASS, REVIEW, Crew


class Understandable(Crew):
    principle_num = "3"

    # ---- 3.1.1 Language of page (Topic 11) ----
    def sc_311_lang(self):
        m = re.search(r'<html\b[^>]*\blang\s*=\s*["\']?([a-zA-Z][a-zA-Z-]*)', self.html, re.I)
        self.record("3.1.1", "A", "Language of page", "Topic 11 Language",
                    PASS if m else FAIL,
                    ([] if m else ["<html> has no lang attribute; set e.g. lang=\"en\""]),
                    f'lang="{m.group(1) if m else "(none)"}"')

    # ---- 3.1.2 Language of parts (Topic 11, AA) ----
    def sc_312_langparts(self):
        tagged = len(re.findall(r'<[a-z0-9]+[^>]*\blang\s*=', self.html, re.I)) - 1  # minus <html>
        self.record("3.1.2", "AA", "Language of parts", "Topic 11 Language", REVIEW,
                    [f"confirm any passage in another language carries its own lang attribute "
                     f"({max(0, tagged)} non-root element(s) already tagged)"],
                    f"{max(0, tagged)} tagged parts")

    # ---- 3.2.1 / 3.2.2 Predictable (on focus / on input) ----
    def sc_321_onfocus(self):
        risk = len(re.findall(r"onfocus\s*=|onchange\s*=\s*[\"'][^\"']*(submit|location|open)", self.html, re.I))
        self.record("3.2.1", "A", "On focus", "Topic (predictable)",
                    REVIEW if risk else PASS,
                    (["focusing a control must not change context (submit, navigate, open a "
                      f"window); {risk} onfocus/onchange handler(s) to check"] if risk else []),
                    f"{risk} focus/change handler(s)")

    def sc_322_oninput(self):
        selects_submit = len(re.findall(r"onchange\s*=\s*[\"'][^\"']*(submit|location)", self.html, re.I))
        self.record("3.2.2", "A", "On input", "Topic (predictable)",
                    FAIL if selects_submit else REVIEW,
                    ([f"{selects_submit} control(s) change context on input (auto-submit/navigate) "
                      "without warning"] if selects_submit
                     else ["confirm changing a setting does not auto-submit or navigate unexpectedly"]),
                    f"{selects_submit} auto-context-change")

    # ---- 3.2.3 / 3.2.4 Consistent navigation & identification (AA) ----
    def sc_323_consistency(self):
        self.record("3.2.3", "AA", "Consistent navigation & identification",
                    "Topic (predictable)", REVIEW,
                    ["across the site, repeated navigation must keep the same order and repeated "
                     "components the same name (a multi-page check)"], "cross-page")

    # ---- 3.3.1 Error identification (Topic 5) ----
    def sc_331_errorid(self):
        forms = self.doc.find("form")
        required = [c for c in self.doc.find("input", "select", "textarea")
                    if c.has("required") or c.get("aria-required") == "true"]
        if not forms and not required:
            self.record("3.3.1", "A", "Error identification", "Topic 5 Forms", NA,
                        measurement="no forms")
            return
        self.record("3.3.1", "A", "Error identification", "Topic 5 Forms", REVIEW,
                    [f"{len(forms)} form(s), {len(required)} required field(s): submit with bad "
                     "input and confirm each error is named in text (not color alone)"],
                    f"{len(forms)} forms, {len(required)} required")

    # ---- 3.3.2 Labels or instructions (Topic 5) ----
    def sc_332_labels(self):
        controls = [c for c in self.doc.find("input", "select", "textarea")
                    if c.get("type", "").lower() not in ("hidden", "submit", "button", "reset")]
        labels_for = {l.get("for") for l in self.doc.find("label") if l.has("for")}
        missing = [c for c in controls if not (
            c.has("aria-label") or c.has("aria-labelledby") or c.has("title")
            or c.has("placeholder") or c.get("id") in labels_for
            or (c.parent and c.parent.tag == "label"))]
        if not controls:
            self.record("3.3.2", "A", "Labels or instructions", "Topic 5 Forms", NA,
                        measurement="no input controls")
            return
        self.record("3.3.2", "A", "Labels or instructions", "Topic 5 Forms",
                    FAIL if missing else PASS,
                    ([f"{len(missing)} control(s) with no visible label or instruction"] if missing
                     else []), f"{len(controls)} controls, {len(missing)} without label")

    # ---- 3.3.3 / 3.3.4 Error suggestion & prevention (AA) ----
    def sc_334_prevention(self):
        legal = re.search(r"(password|credit\s*card|payment|purchase|checkout|delete|confirm)",
                          self.html, re.I)
        self.record("3.3.4", "AA", "Error prevention (legal/financial)", "Topic 5 Forms", REVIEW,
                    ["for legal, financial, or data-deletion submissions, confirm the user can "
                     "review/reverse/confirm before committing"
                     + (" - this page mentions one" if legal else "")],
                    f"legal/financial context={bool(legal)}")
