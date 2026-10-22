"""
Self-test for the hardHats WCAG machine. Every deterministic check must catch its
defect (FAIL on bad input) AND clear on good input (PASS). A compliance tool that
cannot be shown to fail is not trustworthy.

  python -m unittest discover -s tests
"""
import unittest

from a11yhat.run import audit


def status(html, sc):
    for f in audit(html):
        if f.sc == sc:
            return f.status
    return None


WRAP = "<!doctype html><html lang='en'><head><title>T</title></head><body>{}</body></html>"


class DeterministicChecks(unittest.TestCase):

    def one(self, sc, bad_body, good_body, bad="FAIL", good="PASS"):
        self.assertEqual(status(WRAP.format(bad_body), sc), bad, f"{sc} should {bad} on bad input")
        self.assertEqual(status(WRAP.format(good_body), sc), good, f"{sc} should {good} on good input")

    def test_111_img_alt(self):
        self.one("1.1.1", "<img src=a.png>", "<img src=a.png alt='A red barn at dusk'>")

    def test_131_heading_skip(self):
        self.one("1.3.1", "<h1>a</h1><h3>b</h3>", "<h1>a</h1><h2>b</h2>")

    def test_143_contrast(self):
        self.one("1.4.3",
                 "<p style='color:#777;background:#fff'>x</p>",
                 "<p style='color:#000;background:#fff'>x</p>")

    def test_143_text_over_an_image_is_never_a_pass(self):
        # Text whose BACKDROP is a picture: nothing in the stylesheet says
        # what colour is behind it, so a person has to measure the pixels.
        #
        # I rewrote this fixture on 2026-10-22. It used to put
        # background:#fff on the <p> itself and still expect REVIEW,
        # which only passed because the old check scanned the whole
        # stylesheet for a url() and had no idea what was behind what.
        # An opaque white on the paragraph hides the card's image
        # completely, so that markup is genuinely 21:1 and the old
        # verdict was a false positive. The case below is the one the
        # test was always named for.
        self.one("1.4.3",
                 "<style>.card{background:url(board.png) center/contain}"
                 ".card p{color:#000}</style><div class=card><p>x</p></div>",
                 "<style>p{color:#000;background:#fff}</style>"
                 "<div class=card><p>x</p></div>",
                 bad="REVIEW", good="PASS")

    def test_143_an_opaque_background_hides_the_image_behind_it(self):
        # The counterpart, stated on purpose: if the text's own box is
        # opaque, what the container paints underneath cannot be seen and
        # must not drag the verdict down.
        self.one("1.4.3",
                 "<style>.card{background:url(b.png)}.card p{color:#777;"
                 "background:#fff}</style><div class=card><p>x</p></div>",
                 "<style>.card{background:url(b.png)}.card p{color:#000;"
                 "background:#fff}</style><div class=card><p>x</p></div>",
                 bad="FAIL", good="PASS")

    def test_142_autoplay(self):
        self.one("1.4.2", "<video autoplay src=v.mp4></video>", "<video src=v.mp4></video>")

    def test_241_bypass(self):
        self.one("2.4.1", "<nav>n</nav><p>x</p>", "<main><p>x</p></main>")

    def test_242_title(self):
        # title lives in <head>; test full documents here
        self.assertEqual(status("<html lang=en><head></head><body>x</body></html>", "2.4.2"), "FAIL")
        self.assertEqual(status("<html lang=en><head><title>Hi</title></head><body>x</body></html>",
                                "2.4.2"), "PASS")

    def test_244_link_purpose(self):
        self.one("2.4.4", "<a href=/x></a>", "<a href=/x>Annual accessibility report</a>")

    def test_247_focus_visible(self):
        self.one("2.4.7",
                 "<style>:focus{outline:none}</style><a href=/x>x</a>",
                 "<style>:focus{outline:2px solid blue}</style><a href=/x>x</a>")

    def test_311_lang(self):
        self.assertEqual(status("<html><head><title>t</title></head><body>x</body></html>",
                                "3.1.1"), "FAIL")
        self.assertEqual(status("<html lang=en><head><title>t</title></head><body>x</body></html>",
                                "3.1.1"), "PASS")

    def test_332_labels(self):
        self.one("3.3.2",
                 "<form><input type=text name=q></form>",
                 "<form><label for=q>Search</label><input type=text id=q name=q></form>")

    def test_411_dup_id(self):
        self.one("4.1.1", "<span id=x></span><span id=x></span>", "<span id=x></span><span id=y></span>")

    def test_412_name_role_value(self):
        self.one("4.1.2", "<button></button>", "<button>Save</button>")

    def test_412_hidden_input_is_not_a_control(self):
        # a value holder must not fail 4.1.2, and it must not hide a real unnamed button beside it
        self.one("4.1.2", "<input type=hidden id=f><button></button>",
                 "<input type=hidden id=f><button>Save</button>")


class CleanPagePasses(unittest.TestCase):
    """A well-built page must produce zero FAIL findings."""

    CLEAN = """<!doctype html><html lang="en"><head><title>Accessible page</title>
    <style>body{color:#111;background:#fff} :focus{outline:2px solid #005fcc}</style></head>
    <body>
      <a href="#main">Skip to content</a>
      <nav>Navigation</nav>
      <main id="main">
        <h1>Welcome</h1>
        <h2>About</h2>
        <img src="barn.jpg" alt="A red barn at dusk">
        <form>
          <label for="email">Email address</label>
          <input type="text" id="email" name="email" required>
          <button type="submit">Subscribe</button>
        </form>
        <a href="/report">Read the annual accessibility report</a>
      </main>
    </body></html>"""

    def test_no_failures(self):
        fails = [f.sc for f in audit(self.CLEAN) if f.status == "FAIL"]
        self.assertEqual(fails, [], f"clean page should have no failures, got: {fails}")


if __name__ == "__main__":
    unittest.main()
