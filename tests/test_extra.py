"""The criteria I added on 2026-10-22, each proved from both sides.

A criterion that cannot FAIL is decoration, and one that cannot PASS is
noise that teaches people to ignore the report. Every check here is
shown doing both, and the ones that can only ever be REVIEW are shown
producing REVIEW rather than a quiet pass.

  python -m unittest discover -s tests
"""
import unittest

from a11yhat.run import audit

W = ("<!doctype html><html lang=en><head><title>T</title>{head}</head>"
     "<body>{body}</body></html>")


def status(head, body, sc):
    for f in audit(W.format(head=head, body=body)):
        if f.sc == sc:
            return f.status
    return None


class Orientation134(unittest.TestCase):

    def test_a_css_lock_fails(self):
        self.assertEqual(status(
            "<style>@media (orientation:portrait){body{display:none}}</style>",
            "<p>x</p>", "1.3.4"), "FAIL")

    def test_a_script_lock_fails(self):
        self.assertEqual(status(
            "<script>screen.orientation.lock('portrait')</script>",
            "<p>x</p>", "1.3.4"), "FAIL")

    def test_an_orientation_media_query_that_only_restyles_is_fine(self):
        self.assertEqual(status(
            "<style>@media (orientation:portrait){body{font-size:14px}}</style>",
            "<p>x</p>", "1.3.4"), "PASS")


class InputPurpose135(unittest.TestCase):

    def test_an_email_field_without_autocomplete_fails(self):
        self.assertEqual(status("", "<form><input name=email></form>",
                                "1.3.5"), "FAIL")

    def test_with_autocomplete_it_passes(self):
        self.assertEqual(status(
            "", "<form><input name=email autocomplete=email></form>",
            "1.3.5"), "PASS")

    def test_autocomplete_off_is_not_an_answer(self):
        self.assertEqual(status(
            "", "<form><input name=email autocomplete=off></form>",
            "1.3.5"), "FAIL")

    def test_a_field_that_is_not_about_the_user_is_not_applicable(self):
        self.assertEqual(status("", "<form><input name=recipe-id></form>",
                                "1.3.5"), "NA")


class NonTextContrast1411(unittest.TestCase):

    def test_a_faint_control_edge_fails(self):
        self.assertEqual(status(
            "<style>body{background:#fff}input{border-color:#eee}</style>",
            "<input name=q>", "1.4.11"), "FAIL")

    def test_a_dark_edge_is_not_a_failure(self):
        self.assertNotEqual(status(
            "<style>body{background:#fff}input{border-color:#333}</style>",
            "<input name=q>", "1.4.11"), "FAIL")

    def test_nothing_measurable_is_review_not_pass(self):
        self.assertEqual(status("<style>body{background:#fff}</style>",
                                "<p>no controls</p>", "1.4.11"), "REVIEW")


class CharacterShortcuts214(unittest.TestCase):

    def test_a_bare_single_key_handler_fails(self):
        self.assertEqual(status(
            "", "<script>addEventListener('keydown',e=>{if(e.key==='s')save()})"
                "</script>", "2.1.4"), "FAIL")

    def test_a_modifier_guarded_handler_is_review(self):
        self.assertEqual(status(
            "", "<script>addEventListener('keydown',e=>{"
                "if(e.ctrlKey&&e.key==='s')save()})</script>", "2.1.4"),
            "REVIEW")

    def test_no_shortcut_is_not_applicable(self):
        self.assertEqual(status("", "<p>x</p>", "2.1.4"), "NA")


class LabelInName253(unittest.TestCase):

    def test_an_aria_label_that_drops_the_visible_word_fails(self):
        self.assertEqual(status(
            "", "<button aria-label='Submit form'>Search</button>", "2.5.3"),
            "FAIL")

    def test_an_aria_label_that_contains_it_passes(self):
        self.assertEqual(status(
            "", "<button aria-label='Search the site'>Search</button>",
            "2.5.3"), "PASS")

    def test_case_and_punctuation_do_not_matter(self):
        self.assertEqual(status(
            "", "<button aria-label='SEARCH, the site'>Search</button>",
            "2.5.3"), "PASS")

    def test_no_control_with_both_is_not_applicable(self):
        self.assertEqual(status("", "<button>Search</button>", "2.5.3"), "NA")


class ConsistentHelp326(unittest.TestCase):

    def test_help_on_the_page_is_a_review_never_a_pass(self):
        # one page cannot settle a question about every page
        self.assertEqual(status("", "<a href=/help>Help</a>", "3.2.6"),
                         "REVIEW")

    def test_no_help_is_not_applicable(self):
        self.assertEqual(status("", "<p>x</p>", "3.2.6"), "NA")


class RedundantEntry337(unittest.TestCase):

    def test_asking_twice_is_flagged(self):
        self.assertEqual(status(
            "", "<form><input name=email><input name=billing_email></form>",
            "3.3.7"), "REVIEW")

    def test_a_confirm_field_is_the_allowed_case(self):
        self.assertEqual(status(
            "", "<form><input name=email><input name=confirm_email></form>",
            "3.3.7"), "PASS")

    def test_one_field_each_passes(self):
        self.assertEqual(status(
            "", "<form><input name=email><input name=phone></form>",
            "3.3.7"), "PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TheTwoOverReportsIFoundOnLiveSites(unittest.TestCase):
    """Both of these fired on a real page and were wrong. Pinned so they
    stay wrong only once."""

    def test_a_composite_widget_is_not_a_mislabelled_control(self):
        # a scroll container's CONTENT is not its label
        self.assertNotEqual(status(
            "", '<div tabindex=0 aria-label="Product examples, scroll">'
                '<a href=/a>Palette checker</a><a href=/b>Plates</a></div>',
            "2.5.3"), "FAIL")

    def test_a_brand_written_with_a_space_still_matches(self):
        # "OPTIC QUIZ" on screen, "OpticQuiz home" in the label
        self.assertEqual(status(
            "", '<a href=/ aria-label="OpticQuiz home">OPTIC QUIZ</a>',
            "2.5.3"), "PASS")

    def test_a_genuine_mismatch_still_fails(self):
        self.assertEqual(status(
            "", '<button aria-label="Close dialog">Save</button>', "2.5.3"),
            "FAIL")

    def test_a_faint_border_on_a_filled_control_is_not_a_failure(self):
        # the fill identifies the button; the border is decoration
        self.assertNotEqual(status(
            "<style>body{background:#fff}"
            "button{border-color:#eee;background-color:#1a4d8f}</style>",
            "<button>Go</button>", "1.4.11"), "FAIL")

    def test_a_faint_border_on_an_unfilled_control_still_fails(self):
        self.assertEqual(status(
            "<style>body{background:#fff}"
            "button{border-color:#eee;background-color:#fdfdfd}</style>",
            "<button>Go</button>", "1.4.11"), "FAIL")
