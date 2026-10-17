"""
Shared result model for hardHats. Every success criterion a crew checks returns a
Finding, so the four crew leads (Perceivable, Operable, Understandable, Robust)
produce one uniform record and the runner can roll them up by principle.

A criterion is never silently skipped: it is PASS, FAIL, REVIEW (a representative
measurement ran but a human must confirm), or NA (not present on this page). That
is the Trusted Tester stance - every applicable criterion gets a recorded result.
"""
from __future__ import annotations

from dataclasses import dataclass, field

PASS, FAIL, REVIEW, NA = "PASS", "FAIL", "REVIEW", "NA"

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

    def __init__(self, doc, css: str = "", html: str = ""):
        self.doc = doc
        self.css = css or ""
        self.html = html or ""
        self.findings: list[Finding] = []

    def record(self, sc, level, name, topic, status, detail=None, measurement=""):
        self.findings.append(Finding(sc, level, name, topic, status,
                                     list(detail or []), measurement))

    def run(self) -> list[Finding]:
        for name in dir(self):
            if name.startswith("sc_"):
                getattr(self, name)()
        return self.findings
