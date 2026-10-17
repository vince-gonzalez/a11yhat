# hardHats

**coldHat is for play; hardHats are for work.** Where coldHat composes personas and
rules, a hardHat is a crew that does a job — and the first one is a full **WCAG 2.2
accessibility machine**, structured the way the work is actually organized: by the
four principles, **Perceivable · Operable · Understandable · Robust (POUR)**.

## The machine
Each principle is a **crew lead** — a module that owns its success criteria. Every
applicable criterion gets a recorded result; nothing is silently skipped:

- **PASS** — checked and met.
- **FAIL** — checked and failed, with the specific elements.
- **CHECK** — a representative measurement ran, a human must confirm the rest (the
  Trusted Tester stance: keyboard operation, caption quality, reading order, and
  anything a parser cannot judge alone).
- **NA** — not present on this page.

| Crew lead | Principle | Measured deterministically | Representative check + human confirm |
|---|---|---|---|
| `perceivable.py` | 1 | **contrast (1.4.3, luminance math)**, alt text (1.1.1), headings/labels/tables (1.3.1), autoplay (1.4.2), resize/zoom (1.4.4) | media captions (1.2.x), sensory wording (1.3.3), use of color (1.4.1), images of text (1.4.5) |
| `operable.py` | 2 | bypass (2.4.1), title (2.4.2), positive tabindex (2.4.3), link purpose (2.4.4), focus-visible suppression (2.4.7), mouse-only onclick (2.1.1) | keyboard operation, traps, timing, flashing, multiple ways |
| `understandable.py` | 3 | page language (3.1.1), auto-context-change on input (3.2.2), control labels (3.3.2) | language of parts, predictability, error identification/prevention |
| `robust.py` | 4 | duplicate ids (4.1.1), accessible name of every interactive element (4.1.2) | status-message live regions (4.1.3) |

Shared foundation: `dom.py` (a dependency-free DOM), `color.py` (WCAG luminance),
`base.py` (the uniform `Finding` record and the `Crew` base).

## Run it
```
python hardhats/run.py page.html            # full POUR report, exit 1 on any FAIL
python hardhats/run.py page.html --json      # machine-readable
cat page.html | python hardhats/run.py -     # from stdin
```

## Grounding
The criteria, topics, and pass/fail conditions follow the **DHS Trusted Tester for
Web (5.1.3)** process and reuse the logic from the F-Keys house gates (`contrast.py`,
`typefloor.py`, `a11y.py`). Standard library only — nothing is installed into the
environment. Automated checks catch the machine-decidable failures; the CHECK items
are the ones a tester must confirm, each with the exact thing to look at.

## Status
First hardHat. The WCAG machine runs clean across POUR on a 33-criterion page. Next:
more success criteria per facet, a self-test suite, and the crew framework
generalized so other hardHats (a grant crew, a compliance crew) are config, not code.
