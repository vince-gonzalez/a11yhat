"""
a11yhat - runner. Parses an HTML page, deploys the four crew leads (Perceivable,
Operable, Understandable, Robust), and reports every applicable success criterion
with its result and the measurement behind it. A crew in the hardHats family.

  python -m a11yhat page.html
  python -m a11yhat page.html --json
  cat page.html | python -m a11yhat -
"""
from __future__ import annotations

import os
import urllib.error
import json
import re
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

from .base import ERROR, FAIL, NA, PASS, REVIEW
from . import sheets
from .dom import parse
from .operable import Operable
from .perceivable import Perceivable
from .robust import Robust
from .understandable import Understandable

CREWS = [Perceivable, Operable, Understandable, Robust]
MARK = {PASS: "PASS", FAIL: "FAIL", REVIEW: "CHECK", NA: " -- ",
        ERROR: "ERR!"}
ORDER = {FAIL: 0, ERROR: 1, PASS: 2, REVIEW: 3, NA: 4}


def audit(html: str, base: str | None = None):
    """Audit one document.

    `base` is the path or URL the html came from, and it is what lets me
    resolve the stylesheets the page links. Without it I see only inline
    <style>, which is how the contrast check came to measure 0 pairs on
    f-keys.com, 0 on poticas.com and 1 on opticquiz.com.
    """
    css, _loaded, missed, redefined = sheets.collect_resolved(html, base)
    doc = parse(html)
    findings = []
    for crew in CREWS:
        findings += crew(doc, css, html, css_missed=missed,
                         css_redefined=redefined).run()
    return findings


def text_report(findings) -> int:
    print("=" * 72)
    print(" a11yhat - WCAG 2.2 A/AA machine (POUR)")
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
    # A tool somebody runs before they ship says what went wrong in one
    # line. It does not hand them a traceback and an exit code they have
    # to interpret. Every one of these was a traceback until I read it
    # back as a stranger would.
    MAX_HTML = 20_000_000
    try:
        if src.startswith(("http://", "https://")):
            # I audit live addresses now. Reading a file off disk never
            # saw the stylesheet a CDN serves, and a page is not its
            # source.
            req = urllib.request.Request(
                src,
                headers={"user-agent": "Mozilla/5.0 (compatible; a11yhat/0.1)"})
            with urllib.request.urlopen(req, timeout=40) as r:
                html = r.read(MAX_HTML).decode("utf-8", "replace")
        elif src == "-":
            html = sys.stdin.read(MAX_HTML)
        else:
            if not os.path.isfile(src):
                print("a11yhat: no such file: %s" % src, file=sys.stderr)
                return 2
            with open(src, encoding="utf-8", errors="replace") as fh:
                html = fh.read(MAX_HTML)
    except urllib.error.HTTPError as e:
        print("a11yhat: %s returned HTTP %s" % (src, e.code), file=sys.stderr)
        return 2
    except urllib.error.URLError as e:
        print("a11yhat: could not reach %s (%s)" % (src, e.reason),
              file=sys.stderr)
        return 2
    except OSError as e:
        print("a11yhat: could not read %s (%s)" % (src, e), file=sys.stderr)
        return 2
    if not html.strip():
        print("a11yhat: %s is empty, so nothing was checked and nothing "
              "passed" % src, file=sys.stderr)
        return 2
    findings = audit(html, None if src == "-" else src)
    if as_json:
        print(json.dumps([{"sc": f.sc, "level": f.level, "principle": f.principle,
                           "name": f.name, "topic": f.topic, "status": f.status,
                           "measurement": f.measurement, "detail": f.detail}
                          for f in findings], indent=1))
        return 1 if any(f.status == FAIL for f in findings) else 0
    return text_report(findings)


if __name__ == "__main__":
    sys.exit(main())
