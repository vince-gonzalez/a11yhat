"""
a11yhat.vpat - render an ITI VPAT 2.x Accessibility Conformance Report from a11yhat's
per-criterion findings. a11yhat is the gate (it decides the machine-decidable WCAG
criteria); this specializes that output into the recognized professional deliverable a
Section 508 / ADA conformance specialist produces.

Honest by construction. a11yhat PASS/FAIL/NA map to Supports / Does Not Support / Not
Applicable. Every criterion a parser cannot settle (REVIEW) or could not run (ERROR) is
marked "Not Evaluated", naming what a human Trusted Tester must confirm. An automated
report is not a certification, and the document says so in its own body.

  python -m a11yhat.vpat page.html
  python -m a11yhat.vpat https://example.com --product "Name 1.0" --md vpat.md
  cat page.html | python -m a11yhat.vpat -
"""
from __future__ import annotations

import datetime
import sys
import urllib.request

from .base import PASS, FAIL, REVIEW, NA, ERROR
from .run import audit

UA = "Mozilla/5.0 (compatible; a11yhat-vpat/0.1)"
MAX_HTML = 20_000_000

CONFORMANCE = {
    PASS: "Supports",
    FAIL: "Does Not Support",
    NA: "Not Applicable",
    REVIEW: "Not Evaluated",
    ERROR: "Not Evaluated",
}

TERMS = [
    ("Supports", "An automated check found no defect for this criterion. A human may still "
     "find one; equivalent facilitation and known defects are a human call."),
    ("Partially Supports", "Some functionality does not meet the criterion. (Set by a human; "
     "an automated pass does not split a criterion this finely.)"),
    ("Does Not Support", "The majority of functionality does not meet the criterion."),
    ("Not Applicable", "The criterion is not relevant to the product as evaluated."),
    ("Not Evaluated", "Not decided by this report. Used for every criterion an automated pass "
     "cannot settle; a human Trusted Tester must set the final level."),
]

# --- adjacency: each criterion an automated pass cannot settle routes to the next tool
# in the chain. ANDI (SSA's live-DOM Accessible Name & Description Inspector) owns most of
# it; a few rows route elsewhere on purpose, because pointing ANDI at a job it cannot do
# (flashing, keyboard operation, wording) would be the same overclaim this report avoids.
ANDI = "ANDI (SSA live-DOM inspector)"
KBD = "a manual keyboard pass"
PEAT = "PEAT (Photosensitive Epilepsy Analysis Tool)"
EYE = "a manual review"
ADJACENT = {
    "1.1.1": (ANDI, "gANDI: confirm every image's alt conveys its meaning"),
    "1.3.1": (ANDI, "sANDI / tANDI: confirm structure, headings and table associations"),
    "1.3.2": (ANDI, "sANDI, then disable CSS and read the DOM order"),
    "1.3.3": (EYE, "instructions must not rely on shape, position or colour alone"),
    "1.4.1": (ANDI, "cANDI, then confirm no state is signalled by colour alone"),
    "1.4.3": (ANDI, "cANDI measures contrast on the rendered pixels, including text over an image or gradient"),
    "1.4.5": (ANDI, "gANDI: confirm no image is a picture of text"),
    "1.4.11": (ANDI, "cANDI: measure control edges and focus indicators at 3:1"),
    "2.1.1": (KBD, "operate every control with Tab / Enter / Space; ANDI fED lists the focusable set"),
    "2.1.2": (KBD, "tab through the page; focus must never get stuck"),
    "2.1.4": (KBD, "each single-key shortcut must be switchable off, remappable, or active only on focus"),
    "2.2.1": (EYE, "confirm any session or interaction time limit is adjustable"),
    "2.2.2": (EYE, "anything moving over five seconds must be pausable"),
    "2.3.1": (PEAT, "record about thirty seconds and measure; nothing may flash over three times a second"),
    "2.4.3": (ANDI, "fED, then Tab through: focus order must follow the visual order"),
    "2.4.5": (EYE, "site level: confirm at least two ways to reach a page"),
    "2.4.6": (ANDI, "sANDI: confirm headings and labels describe their topic"),
    "3.1.2": (EYE, "a passage in another language needs its own lang attribute"),
    "3.2.2": (KBD, "confirm changing a setting does not auto-submit or navigate"),
    "3.2.3": (EYE, "cross-page: repeated navigation and components stay consistent"),
    "3.3.4": (EYE, "legal or financial: the user can review, reverse or confirm before committing"),
    "4.1.3": (ANDI, "live-region module: confirm dynamic updates are announced"),
}
DEFAULT_ADJ = (ANDI, "inspect the element's name, role, value and state")


def _load(src):
    if src.startswith(("http://", "https://")):
        req = urllib.request.Request(src, headers={"user-agent": UA})
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.read(MAX_HTML).decode("utf-8", "replace")
    if src == "-":
        return sys.stdin.read(MAX_HTML)
    with open(src, encoding="utf-8", errors="replace") as fh:
        return fh.read(MAX_HTML)


def _cell(s):
    """One markdown table cell, on one line, pipes escaped so the grid holds."""
    return " ".join(str(s).split()).replace("|", "\\|")


def _sckey(sc):
    try:
        return tuple(int(x) for x in sc.split("."))
    except ValueError:
        return (99,)


def _remark(f):
    if f.status == REVIEW:
        lead = "Automated check ran; a human Trusted Tester must confirm this criterion. "
    elif f.status == ERROR:
        lead = "The automated check could not run, so this criterion was not decided. "
    elif f.status == PASS and not f.measurement and not f.detail:
        lead = "Meets the automated check. "
    else:
        lead = ""
    bits = [f.measurement] + list(f.detail)
    body = ". ".join(b.strip().rstrip(".") for b in bits if b and b.strip())
    text = (lead + body).strip()
    if f.status in (REVIEW, ERROR):
        tool, how = ADJACENT.get(f.sc, DEFAULT_ADJ)
        text += " Confirm with: %s - %s." % (tool, how)
    return _cell(text or "See the evaluation method above.")


def _table(findings, level):
    rows = sorted([f for f in findings if f.level == level], key=lambda f: _sckey(f.sc))
    out = ["| Criteria | Conformance Level | Remarks and Explanations |", "|---|---|---|"]
    for f in rows:
        out.append("| %s | %s | %s |" % (_cell("%s %s" % (f.sc, f.name)),
                                         CONFORMANCE.get(f.status, "Not Evaluated"),
                                         _remark(f)))
    if len(out) == 2:
        out.append("| (no Level %s criteria evaluated on this page) |  |  |" % level)
    return "\n".join(out)


def build(findings, product, source, contact):
    date = datetime.date.today().isoformat()
    counts = {}
    for f in findings:
        counts[f.status] = counts.get(f.status, 0) + 1
    tally = ", ".join("%d %s" % (counts[k], CONFORMANCE.get(k, k))
                      for k in (PASS, FAIL, NA, REVIEW, ERROR) if counts.get(k))
    md = [
        "# Accessibility Conformance Report",
        "### VPAT 2.x (ITI) - WCAG 2.2 and Revised Section 508 edition", "",
        "**Name of Product / Version:** %s" % (product or source), "",
        "**Report Date:** %s" % date, "",
        "**Product Description:** %s" % source, "",
        "**Contact Information:** %s" % (contact or "(add a contact)"), "",
        "**Evaluation Methods Used:** a11yhat, an automated WCAG 2.2 A/AA machine grounded "
        "in the DHS Trusted Tester for Web (5.1.3) process. This pass is AUTOMATED ONLY: it "
        "decides the machine-decidable criteria and marks every criterion a parser cannot "
        "settle as Not Evaluated, naming what a human must confirm. An automated report is "
        "not a certification.", "",
        "**Applicable Standards / Guidelines:** WCAG 2.2 Level A and Level AA; Revised "
        "Section 508 (36 CFR 1194).", "",
        "## Conformance terms",
    ]
    md += ["- **%s** - %s" % (t, d) for t, d in TERMS]
    md += [
        "", "## WCAG 2.2 Report", "",
        "Automated tally: %d criteria evaluated - %s." % (len(findings), tally), "",
        "### Table 1: Success Criteria, Level A", "", _table(findings, "A"), "",
        "### Table 2: Success Criteria, Level AA", "", _table(findings, "AA"), "",
        "## Scope and honesty",
        "- Rows marked **Not Evaluated** are the human 20 percent: a Trusted Tester must "
        "operate the page (keyboard, screen reader, media, reading order) and set the final "
        "level. This is a draft until a person decides those rows.",
        "- Any WCAG 2.2 A/AA criterion not listed above was not assessed by this automated "
        "pass and must be evaluated manually.",
        "- The Revised Section 508 chapters for hardware, software platform, authored output "
        "and support documentation are out of scope for a page scan and need separate "
        "evaluation.",
        "- Each Not Evaluated row names the adjacent tool that settles it: ANDI (SSA's "
        "live-DOM inspector) for names, roles, contrast and structure; PEAT for flashing; a "
        "manual keyboard pass for operation. ANDI is a separate tool a tester runs in the "
        "browser; it is not bundled with this report.",
    ]
    return "\n".join(md) + "\n"


def main():
    args = sys.argv[1:]

    def opt(flag):
        return args[args.index(flag) + 1] if flag in args else None

    product, contact, md_out = opt("--product"), opt("--contact"), opt("--md")
    taken = {product, contact, md_out, "--product", "--contact", "--md"}
    pos = [a for a in args if a not in taken and not a.startswith("--")]
    if not pos:
        print(__doc__.strip())
        return 2
    src = pos[0]
    try:
        html = _load(src)
    except Exception as e:  # noqa: BLE001 - one line, not a traceback
        print("a11yhat.vpat: could not read %s (%s)" % (src, e), file=sys.stderr)
        return 2
    if not html.strip():
        print("a11yhat.vpat: %s is empty, nothing to report" % src, file=sys.stderr)
        return 2
    findings = audit(html, None if src == "-" else src)
    report = build(findings, product, src, contact)
    if md_out:
        with open(md_out, "wb") as fh:          # bytes: force LF, no CRLF surprise
            fh.write(report.encode("utf-8"))
        print("wrote %s (%d criteria)" % (md_out, len(findings)))
    else:
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
        print(report)
    return 1 if any(f.status == FAIL for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
