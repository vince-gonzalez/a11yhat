"""What happens when the input is not what I hoped for.

Every case here is something a real page or a real stylesheet can
contain, and each one of them used to be a way for the audit to produce
nothing instead of an answer. A tool somebody runs before they ship has
to degrade to "this one check broke" and never to a traceback.

The rule these enforce: a criterion is PASS, FAIL, REVIEW, NA or ERROR.
It is never silently absent, because a row that is missing from a report
reads exactly like a row that passed.

  python -m unittest discover -s tests
"""
import unittest

from a11yhat.base import ERROR
from a11yhat.run import audit
from a11yhat import cascade, sheets
from a11yhat.dom import parse

EXPECTED_MIN = 34          # criteria the report must always carry


class MalformedInputDoesNotStopTheAudit(unittest.TestCase):

    def check(self, html):
        f = audit(html)
        self.assertGreaterEqual(len(f), EXPECTED_MIN,
                                "the report lost criteria on this input")
        broke = [x.sc for x in f if x.status == ERROR]
        self.assertEqual(broke, [], "checks crashed: %s" % broke)
        return f

    def test_empty_document(self):
        self.check("")

    def test_only_whitespace(self):
        self.check("   \n\t  ")

    def test_not_html_at_all(self):
        self.check("{\"this\": \"is json\"}")

    def test_unclosed_tags(self):
        self.check("<html><body><div><p>text<span>more")

    def test_stray_angle_brackets(self):
        self.check("<html><body><p>5 < 6 > 4 and <<<>>> </p></body></html>")

    def test_a_tag_that_never_closes_its_attribute(self):
        self.check('<html><body><a href="/x class=y>text</a></body></html>')

    def test_unbalanced_css_braces(self):
        self.check("<html><head><style>body{color:#000;"
                   ".x{background:#fff}</style></head><body><p>x</p></body>")

    def test_css_that_is_not_css(self):
        self.check("<html><head><style>}}{{;;::##</style></head>"
                   "<body><p>x</p></body></html>")

    def test_an_unterminated_media_block(self):
        self.check("<html><head><style>@media screen{body{color:#000}"
                   "</style></head><body><p>x</p></body></html>")

    def test_a_comment_that_never_closes(self):
        self.check("<html><head><style>/* body{color:#000}</style></head>"
                   "<body><p>x</p></body></html>")

    def test_very_deep_nesting_does_not_blow_the_stack(self):
        depth = 800
        body = "<div>" * depth + "text" + "</div>" * depth
        self.check("<html lang=en><head><title>t</title></head><body>"
                   + body + "</body></html>")

    def test_a_huge_class_list(self):
        cls = " ".join("c%d" % i for i in range(400))
        self.check('<html><body><p class="%s">x</p></body></html>' % cls)

    def test_many_elements(self):
        body = "".join("<p class=a>t%d</p>" % i for i in range(1500))
        self.check("<html lang=en><head><title>t</title>"
                   "<style>.a{color:#777;background:#fff}</style></head>"
                   "<body>%s</body></html>" % body)


class CssEdgeCases(unittest.TestCase):

    def test_circular_variables_terminate(self):
        css = ":root{--a:var(--b);--b:var(--a)}"
        out = sheets.expand_vars(css)
        self.assertIsInstance(out, str)

    def test_a_variable_pointing_at_a_variable_resolves(self):
        css = ":root{--a:var(--b);--b:#fff}p{color:var(--a)}"
        self.assertIn("#fff", sheets.expand_vars(css))

    def test_a_missing_variable_without_a_fallback_is_left_alone(self):
        css = "p{color:var(--nope)}"
        self.assertIn("var(--nope)", sheets.expand_vars(css))

    def test_unsupported_selectors_are_skipped_not_guessed(self):
        got = [s for s, _d, _o in cascade.rules("a > b{color:red}"
                                                "c d{color:blue}")]
        self.assertEqual(got, ["c d"])

    def test_a_pseudo_element_is_skipped(self):
        got = [s for s, _d, _o in cascade.rules("p::before{color:red}"
                                                "p{color:blue}")]
        self.assertEqual(got, ["p"])

    def test_media_bodies_are_removed_entirely(self):
        got = [s for s, _d, _o in cascade.rules(
            "@media print{p{color:red}}p{color:blue}")]
        self.assertEqual(got, ["p"])

    def test_a_selector_list_becomes_separate_rules(self):
        got = [s for s, _d, _o in cascade.rules("h1, h2 , h3{color:red}")]
        self.assertEqual(got, ["h1", "h2", "h3"])

    def test_matching_against_a_detached_node_does_not_raise(self):
        doc = parse("<html><body><p>x</p></body></html>")
        node = doc.find("p")[0]
        self.assertFalse(cascade.matches(node, "nothing .here"))


class TheReportNeverQuietlyDropsACriterion(unittest.TestCase):

    def test_every_criterion_appears_exactly_once(self):
        f = audit("<!doctype html><html lang=en><head><title>t</title></head>"
                  "<body><p>x</p></body></html>")
        seen = [x.sc for x in f]
        self.assertEqual(len(seen), len(set(seen)),
                         "a criterion was recorded twice")

    def test_a_crashing_check_reports_ERROR_and_not_a_pass(self):
        from a11yhat.base import Crew
        class Boom(Crew):
            principle_num = "1"
            def sc_111_fine(self):
                self.record("1.1.1", "A", "fine", "t", "PASS")
            def sc_143_boom(self):
                raise ValueError("synthetic")
        out = Boom(None).run()
        statuses = {x.sc: x.status for x in out}
        self.assertEqual(statuses["1.4.3"], ERROR)
        self.assertEqual(statuses["1.1.1"], "PASS",
                         "the other checks must still run")


if __name__ == "__main__":
    unittest.main(verbosity=2)
