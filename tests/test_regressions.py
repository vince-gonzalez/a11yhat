"""Two bugs that shipped, and the tests that keep them dead.

Both were false verdicts on correct markup or correct colour, which is
the worst failure mode a compliance tool has: the alpha one certified
unreadable text as a pass, and the canvas one failed a page that was
right. A VPAT written on either is wrong in a way the reader cannot see.

  python -m unittest discover -s tests
"""
import unittest

from a11yhat.color import composite, parse_rgba, ratio
from a11yhat.run import audit

WRAP = ("<!doctype html><html lang='en'><head><title>T</title>"
        "{head}</head><body>{body}</body></html>")


def status(html, sc):
    for f in audit(html):
        if f.sc == sc:
            return f.status
    return None


class AlphaIsNotIgnored(unittest.TestCase):
    """rgba() used to be parsed three groups wide, dropping the alpha, so
    rgba(0,0,0,0.04) was read as pure black and scored 21:1 against white.
    What a person actually sees is about #f5f5f5, which is 1.09:1."""

    def test_alpha_is_parsed(self):
        self.assertEqual(parse_rgba("rgba(0,0,0,0.04)"), (0, 0, 0, 0.04))
        self.assertEqual(parse_rgba("rgb(0,0,0)"), (0, 0, 0, 1.0))

    def test_modern_syntax(self):
        self.assertEqual(parse_rgba("rgb(0 0 0 / 50%)"), (0, 0, 0, 0.5))
        r, g, b, a = parse_rgba("#00000080")
        self.assertEqual((r, g, b), (0, 0, 0))
        self.assertAlmostEqual(a, 0.502, places=2)

    def test_composite_matches_what_the_eye_sees(self):
        self.assertEqual(composite((0, 0, 0, 0.04)), (245, 245, 245))
        self.assertEqual(composite((0, 0, 0, 1.0)), (0, 0, 0))
        # over a known backdrop, not the assumed white one
        self.assertEqual(composite((255, 255, 255, 0.5), (0, 0, 0)),
                         (128, 128, 128))

    def test_the_number_that_was_wrong(self):
        white = (255, 255, 255)
        faint = composite(parse_rgba("rgba(0,0,0,0.04)"))
        self.assertLess(ratio(faint, white), 1.5,
                        "4% black on white is unreadable and must score low")
        solid = composite(parse_rgba("#000000"))
        self.assertAlmostEqual(ratio(solid, white), 21.0, places=1)

    def test_translucent_text_is_not_reported_as_a_clean_pass(self):
        """It cannot be a FAIL either, because the real backdrop is not
        knowable from a stylesheet. It has to say so: REVIEW."""
        head = ("<style>.a{color:rgba(0,0,0,0.9);"
                "background-color:rgba(255,255,255,0.9)}</style>")
        html = WRAP.format(head=head, body="<p class=a>text</p>")
        self.assertEqual(status(html, "1.4.3"), "REVIEW")

    def test_opaque_colours_still_pass_cleanly(self):
        head = "<style>.a{color:#000000;background-color:#ffffff}</style>"
        html = WRAP.format(head=head, body="<p class=a>text</p>")
        self.assertEqual(status(html, "1.4.3"), "PASS")

    def test_a_real_failure_is_still_a_failure(self):
        head = "<style>.a{color:#cccccc;background-color:#ffffff}</style>"
        html = WRAP.format(head=head, body="<p class=a>text</p>")
        self.assertEqual(status(html, "1.4.3"), "FAIL")


class CanvasAcceptsAnAccessibleName(unittest.TestCase):
    """The check read inner text only, so a canvas carrying a correct
    role=img and aria-label was reported as having no text alternative.
    The svg check beside it already accepted aria-label."""

    def test_aria_label_names_a_canvas(self):
        good = ("<canvas role='img' aria-label='A musical staff showing the "
                "notes played'></canvas>")
        self.assertEqual(status(WRAP.format(head="", body=good), "1.1.1"),
                         "PASS")

    def test_fallback_content_still_names_a_canvas(self):
        good = "<canvas>A musical staff showing the notes played.</canvas>"
        self.assertEqual(status(WRAP.format(head="", body=good), "1.1.1"),
                         "PASS")

    def test_aria_labelledby_names_a_canvas(self):
        good = ("<h2 id='t'>The staff</h2>"
                "<canvas role='img' aria-labelledby='t'></canvas>")
        self.assertEqual(status(WRAP.format(head="", body=good), "1.1.1"),
                         "PASS")

    def test_a_decorative_canvas_needs_no_name(self):
        good = "<canvas aria-hidden='true'></canvas>"
        self.assertEqual(status(WRAP.format(head="", body=good), "1.1.1"),
                         "PASS")

    def test_a_genuinely_bare_canvas_still_fails(self):
        bad = "<canvas id='stage' width='800' height='600'></canvas>"
        self.assertEqual(status(WRAP.format(head="", body=bad), "1.1.1"),
                         "FAIL")

    def test_whitespace_is_not_a_text_alternative(self):
        bad = "<canvas>   \n  </canvas>"
        self.assertEqual(status(WRAP.format(head="", body=bad), "1.1.1"),
                         "FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
