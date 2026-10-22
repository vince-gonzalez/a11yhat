"""The cascade: which colour lands on which text.

Measuring contrast from rules that set a colour AND a background in the
same block measured 0 pairs on f-keys.com, 0 on poticas.com and 1 on
opticquiz.com, because no real stylesheet is written that way. These
tests pin the model that replaced it, and every one of them is a case
that was wrong before.

  python -m unittest discover -s tests
"""
import unittest

from a11yhat import cascade, sheets
from a11yhat.dom import parse

W = "<!doctype html><html lang=en><head><title>T</title>{}</head><body>{}</body></html>"


def rows(style, body):
    html = W.format("<style>%s</style>" % style, body)
    css, _l, _m, _r = sheets.collect_resolved(html, None)
    return cascade.text_pairs(parse(html), css)


def one(style, body, where=None):
    got = [r for r in rows(style, body)
           if where is None or r["where"].startswith(where)]
    return got[0] if got else None


class ColourInherits(unittest.TestCase):

    def test_colour_comes_from_an_ancestor(self):
        r = one("body{color:#000;background:#fff}", "<p>hello</p>", "p")
        self.assertEqual(r["verdict"], "measured")
        self.assertAlmostEqual(r["ratio"], 21.0, places=1)

    def test_the_nearest_rule_wins_over_a_further_one(self):
        r = one("body{color:#000;background:#fff}.q{color:#fff}",
                "<p class=q>hello</p>", "p")
        self.assertAlmostEqual(r["ratio"], 1.0, places=1)

    def test_specificity_beats_source_order(self):
        # the later, less specific rule must NOT win
        r = one("#x{color:#000}p{color:#fff}body{background:#fff}",
                "<p id=x>hello</p>", "p")
        self.assertAlmostEqual(r["ratio"], 21.0, places=1)


class BackgroundDoesNotInheritButTheBackdropIsReal(unittest.TestCase):

    def test_backdrop_comes_from_the_nearest_painted_ancestor(self):
        r = one("body{background:#fff}.dark{background:#000}.dark p{color:#fff}",
                "<div class=dark><p>hello</p></div>", "p")
        self.assertAlmostEqual(r["ratio"], 21.0, places=1)

    def test_translucent_layers_are_flattened_bottom_up(self):
        # a 50% white panel over black is mid grey, not white. Reading
        # only the first layer turned white text on a dark hero into
        # white on white.
        r = one("body{background:#000}"
                ".panel{background:rgba(255,255,255,0.5)}"
                ".panel p{color:#fff}",
                "<div class=panel><p>hello</p></div>", "p")
        # 50% white over black is mid grey, and white on mid grey is
        # 3.95:1 - a real AA failure. Reading only the first layer and
        # flattening it onto the page's white gave 1.00:1 instead, so
        # the number has to be this one and not either extreme.
        self.assertAlmostEqual(r["ratio"], 3.95, places=1)
        self.assertLess(r["ratio"], 4.5, "it still fails AA")

    def test_an_opaque_layer_stops_the_walk(self):
        r = one("body{background:#000}.card{background:#fff}.card p{color:#000}",
                "<div class=card><p>hello</p></div>", "p")
        self.assertAlmostEqual(r["ratio"], 21.0, places=1)


class ThingsIRefuseToGuess(unittest.TestCase):

    def test_text_over_an_image_is_unmeasurable(self):
        r = one(".hero{background:url(x.png)}.hero p{color:#888}",
                "<div class=hero><p>hello</p></div>", "p")
        self.assertEqual(r["verdict"], "unmeasurable")

    def test_a_gradient_is_also_unmeasurable(self):
        r = one(".hero{background:linear-gradient(#000,#fff)}.hero p{color:#888}",
                "<div class=hero><p>hello</p></div>", "p")
        self.assertEqual(r["verdict"], "unmeasurable")

    def test_an_inactive_component_is_exempt(self):
        r = one("body{background:#d4d0c8;color:#808080}",
                "<button disabled>Forward</button>", "button")
        self.assertEqual(r["verdict"], "exempt")

    def test_aria_disabled_counts_too(self):
        r = one("body{background:#d4d0c8;color:#808080}",
                "<span aria-disabled=true>Forward</span>", "span")
        self.assertEqual(r["verdict"], "exempt")

    def test_a_visually_disabled_span_is_NOT_exempt(self):
        # If it only looks disabled it is not disabled, and that gap is
        # itself worth reporting rather than excusing.
        r = one("body{background:#d4d0c8}.off{color:#808080}",
                "<span class=off>Forward</span>", "span")
        self.assertEqual(r["verdict"], "measured")
        self.assertLess(r["ratio"], 4.5)

    def test_media_queries_are_not_applied(self):
        # the dark-mode rule must not be measured against the light page
        r = one("body{background:#fff;color:#000}"
                "@media (prefers-color-scheme:dark){body{color:#fff}}",
                "<p>hello</p>", "p")
        self.assertAlmostEqual(r["ratio"], 21.0, places=1)

    def test_hover_states_are_not_measured_as_resting(self):
        r = one("body{background:#fff;color:#000}a:hover{color:#eee}",
                "<a href=#>link</a>", "a")
        self.assertAlmostEqual(r["ratio"], 21.0, places=1)

    def test_elements_with_no_text_are_not_measured(self):
        got = [r for r in rows("body{background:#fff}.box{color:#eee}",
                               "<div class=box><span>x</span></div>")
               if r["where"].startswith("div")]
        self.assertEqual(got, [], "a div holding no text of its own is not text")

    def test_display_none_is_not_measured(self):
        # a sign-in modal and an easter-egg panel are display:none at
        # rest; text nobody can see has no contrast to fail
        r = one("body{background:#fff;color:#eee}.modal{display:none}",
                "<div class=modal><p>hidden</p></div>", "p")
        self.assertEqual(r["verdict"], "exempt")

    def test_opacity_zero_IS_still_measured(self):
        # that is how I write a scroll reveal, and it does appear
        r = one("body{background:#fff;color:#eee}.reveal{opacity:0}",
                "<div class=reveal><p>shown later</p></div>", "p")
        self.assertEqual(r["verdict"], "measured")

    def test_a_colour_emoji_is_exempt(self):
        r = one("body{background:#3b2314;color:#2a1a0e}",
                "<span>🌰</span>", "span")
        self.assertEqual(r["verdict"], "exempt")

    def test_a_typographic_symbol_is_NOT_exempt(self):
        # U+2726 takes a CSS colour, so it still has to pass
        r = one("body{background:#ede5d4;color:#c9922a}",
                "<span>✦</span>", "span")
        self.assertEqual(r["verdict"], "measured")

    def test_a_glyph_beside_real_words_is_still_real_words(self):
        r = one("body{background:#3b2314;color:#2a1a0e}",
                "<span>🌰 Pantry</span>", "span")
        self.assertEqual(r["verdict"], "measured")



class CustomPropertiesResolve(unittest.TestCase):

    def test_a_token_is_substituted(self):
        r = one(":root{--ink:#000;--bg:#fff}"
                "body{color:var(--ink);background:var(--bg)}",
                "<p>hello</p>", "p")
        self.assertAlmostEqual(r["ratio"], 21.0, places=1)

    def test_a_fallback_is_used_when_the_token_is_missing(self):
        r = one("body{color:var(--nope,#000);background:#fff}",
                "<p>hello</p>", "p")
        self.assertAlmostEqual(r["ratio"], 21.0, places=1)

    def test_a_redefined_token_is_reported(self):
        css = ":root{--ink:#000}@media (prefers-color-scheme:dark){:root{--ink:#fff}}"
        _vals, redefined = sheets.custom_properties(css)
        self.assertIn("--ink", redefined,
                      "dark mode redefines this and the report must say so")


class Stylesheets(unittest.TestCase):

    def test_a_linked_sheet_is_reported_missing_without_a_base(self):
        html = W.format('<link rel=stylesheet href="/x.css">', "<p>hi</p>")
        _css, loaded, missed = sheets.collect(html, None)
        self.assertEqual(loaded, [])
        self.assertTrue(missed, "a sheet I did not look for is not a sheet "
                                "that was not there")

    def test_rel_token_is_matched_not_equality(self):
        html = W.format('<link href="/x.css" rel="alternate stylesheet">', "")
        self.assertEqual(sheets.stylesheet_hrefs(html), ["/x.css"])

    def test_attribute_order_does_not_matter(self):
        html = W.format('<link href="/a.css" rel="stylesheet">'
                        '<link rel="stylesheet" href="/b.css">', "")
        self.assertEqual(sheets.stylesheet_hrefs(html), ["/a.css", "/b.css"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
