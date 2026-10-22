"""
Shared result model for hardHats. Every success criterion a crew checks returns a
Finding, so the four crew leads (Perceivable, Operable, Understandable, Robust)
produce one uniform record and the runner can roll them up by principle.

A criterion is never silently skipped: it is PASS, FAIL, REVIEW (a representative
measurement ran but a human must confirm), or NA (not present on this page). That
is the Trusted Tester stance - every applicable criterion gets a recorded result.
"""
from __future__ import annotations

import re

from dataclasses import dataclass, field

PASS, FAIL, REVIEW, NA = "PASS", "FAIL", "REVIEW", "NA"
# A check that fell over. NOT a pass and NOT a fail: the criterion was
# not decided, and a report that quietly drops it reads as a pass.
ERROR = "ERROR"


def _sc_from_method(name):
    """sc_143_contrast -> 1.4.3, for naming a crashed check."""
    m = re.match(r"sc_(\d)(\d)(\d+)", name)
    return "%s.%s.%s" % m.groups() if m else name


PRINCIPLE = {"1": "Perceivable", "2": "Operable", "3": "Understandable", "4": "Robust"}


@dataclass
class Finding:
    sc: str                 # "1.1.1"
    level: str              # "A" / "AA"
    name: str               # short criterion name
    topic: str              # Trusted Tester topic reference
    status: str = REVIEW
    detail: list = field(default_factory=list)   # specific problems or notes
    measurement: str = ""   # the number/evidence the check produced

    @property
    def principle(self) -> str:
        return PRINCIPLE[self.sc[0]]


class Crew:
    """A principle's crew lead. Each check() appends one Finding per criterion."""

    principle_num = ""

    def __init__(self, doc, css: str = "", html: str = "",
                 css_missed=None, css_redefined=None):
        self.doc = doc
        self.css = css or ""
        self.html = html or ""
        # Stylesheets I could not read. If this is non-empty then any
        # colour I measured is a subset of the colours on the page, and
        # a clean result over a subset is not a clean result.
        self.css_missed = list(css_missed or [])
        # Tokens that carry more than one value - my dark mode. If this
        # is non-empty I measured the default theme and not the other
        # one, and I say so rather than implying I checked both.
        self.css_redefined = list(css_redefined or [])
        self.findings: list[Finding] = []

    def record(self, sc, level, name, topic, status, detail=None, measurement=""):
        self.findings.append(Finding(sc, level, name, topic, status,
                                     list(detail or []), measurement))

    def run(self) -> list[Finding]:
        """Every check runs, and one of them falling over does not take
        the report with it.

        Without this, a single malformed stylesheet or a surprise in the
        markup raised out of one check and the whole audit produced
        nothing at all - no report, no partial answer, a traceback. A
        tool somebody runs before they ship has to degrade to "this one
        check broke" rather than to silence.

        A crashed check records an ERROR, never a pass. I would rather
        the report say a criterion could not be decided than imply it
        was decided and came back clean.
        """
        for name in sorted(dir(self)):
            if not name.startswith("sc_"):
                continue
            try:
                getattr(self, name)()
            except Exception as e:                           # noqa: BLE001
                self.findings.append(Finding(
                    _sc_from_method(name), "A", name, "internal", ERROR,
                    ["this check raised %s: %s. The criterion was NOT "
                     "decided and is not a pass."
                     % (type(e).__name__, str(e)[:120])],
                    "check crashed"))
        return self.findings
