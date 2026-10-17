"""
hardHats WCAG machine - runner. Parses an HTML page, deploys the four crew leads
(Perceivable, Operable, Understandable, Robust), and reports every applicable
success criterion with its result and the measurement behind it.

  python hardhats/run.py page.html
  python hardhats/run.py page.html --json
  cat page.html | python hardhats/run.py -
"""
from __future__ import annotations

import json
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

from .base import FAIL, NA, PASS, REVIEW
from .dom import parse
from .operable import Operable
from .perceivable import Perceivable
from .robust import Robust
from .understandable import Understandable

CREWS = [Perceivable, Operable, Understandable, Robust]
MARK = {PASS: "PASS", FAIL: "FAIL", REVIEW: "CHECK", NA: " -- "}
ORDER = {PASS: 1, FAIL: 0, REVIEW: 2, NA: 3}


def audit(html: str):
    css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html, re.I | re.S))
    doc = parse(html)
    findings = []
    for crew in CREWS:
        findings += crew(doc, css, html).run()
    return findings


def text_report(findings) -> int:
    print("=" * 72)
    print(" hardHats - WCAG 2.2 A/AA machine (POUR)")
    print("=" * 72)
    fails = reviews = 0
    for crew in CREWS:
        pnum = crew.principle_num
        rows = sorted([f for f in findings if f.sc[0] == pnum],
                      key=lambda f: (ORDER[f.status], f.sc))
        head = {"1": "PERCEIVABLE", "2": "OPERABLE", "3": "UNDERSTANDABLE", "4": "ROBUST"}[pnum]
        nf = sum(1 for f in rows if f.status == FAIL)
        nc = sum(1 for f in rows if f.status == REVIEW)
        print(f"\n[{pnum}] {head}  —  crew lead: {crew.__name__}  "
              f"({nf} fail, {nc} to check, {len(rows)} criteria)")
        print("-" * 72)
        for f in rows:
            print(f"  {MARK[f.status]}  {f.sc:<6} {f.level:<2} {f.name}")
            if f.measurement:
                print(f"         └ {f.measurement}")
            for d in f.detail:
                print(f"           • {d}")
        fails += nf
        reviews += nc
    total = len(findings)
    print("\n" + "=" * 72)
    verdict = "FAIL" if fails else ("NEEDS HUMAN REVIEW" if reviews else "PASS (automated)")
    print(f" VERDICT: {verdict}  —  {fails} failing, {reviews} to confirm, "
          f"{total} criteria across all four principles")
    print("=" * 72)
    return 1 if fails else 0


def main():
    args = sys.argv[1:]
    as_json = "--json" in args
    args = [a for a in args if a != "--json"]
    src = args[0] if args else "-"
    html = sys.stdin.read() if src == "-" else open(src, encoding="utf-8", errors="replace").read()
    findings = audit(html)
    if as_json:
        print(json.dumps([{"sc": f.sc, "level": f.level, "principle": f.principle,
                           "name": f.name, "topic": f.topic, "status": f.status,
                           "measurement": f.measurement, "detail": f.detail}
                          for f in findings], indent=1))
        return 1 if any(f.status == FAIL for f in findings) else 0
    return text_report(findings)


if __name__ == "__main__":
    sys.exit(main())
