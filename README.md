# a11yhat

An open-source **WCAG 2.2 accessibility machine**, structured the way the work is
organized — by the four principles, **Perceivable · Operable · Understandable ·
Robust (POUR)**. One crew in the **hardHats** family (hardHats is the framework;
a11yhat is a crew built with it).

## How it works
Each principle is a **crew lead** — a module that owns its success criteria. Every
applicable criterion gets a recorded result; nothing is silently skipped:

- **PASS** — checked and met.
- **FAIL** — checked and failed, with the specific elements.
- **CHECK** — a representative measurement ran; a human must confirm the rest
  (keyboard operation, caption quality, reading order — anything a parser can't
  judge alone). Each CHECK names the exact thing to look at.
- **NA** — not present on this page.

| Crew lead | Principle | Measured deterministically | Representative check + human confirm |
|---|---|---|---|
| `perceivable.py` | 1 | **contrast (1.4.3, luminance math)**, alt text (1.1.1), headings/labels/tables (1.3.1), autoplay (1.4.2), resize/zoom (1.4.4) | media captions (1.2.x), sensory wording (1.3.3), use of color (1.4.1), images of text (1.4.5) |
| `operable.py` | 2 | bypass (2.4.1), title (2.4.2), positive tabindex (2.4.3), link purpose (2.4.4), focus-visible suppression (2.4.7), mouse-only onclick (2.1.1) | keyboard operation, traps, timing, flashing, multiple ways |
| `understandable.py` | 3 | page language (3.1.1), auto-context-change on input (3.2.2), control labels (3.3.2) | language of parts, predictability, error identification/prevention |
| `robust.py` | 4 | duplicate ids (4.1.1), accessible name of every interactive element (4.1.2) | status-message live regions (4.1.3) |

Shared foundation: `dom.py` (a dependency-free DOM), `color.py` (WCAG luminance),
`base.py` (the uniform `Finding` record and the `Crew` base).

## Install & run
```
pip install a11yhat            # once on PyPI
python -m a11yhat page.html    # full POUR report, exit 1 on any FAIL
python -m a11yhat page.html --json
cat page.html | python -m a11yhat -
```

## Grounding
Criteria, topics, and pass/fail conditions follow the **DHS Trusted Tester for Web
(5.1.3)** process. Standard library only — nothing is installed into your
environment. Automated checks catch the machine-decidable failures; the CHECK
items are the ones a tester must confirm, each with the exact thing to review. It
is an honest tool: it does the fast 80% and tells you precisely what the human 20%
is — it does not pretend a scanner can certify a page.

## License
MIT. Copyright Vincent Gonzalez / F-Keys Creative LLC.

## Tests
`python -m unittest discover -s tests` — every deterministic check is proven to
catch its defect and to clear on good input, and a clean page produces zero
failures.
