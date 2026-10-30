"""Tests for scripts/build.py and scripts/check_site.py (stdlib unittest).

Run: python3 -m unittest discover -s tests -v
"""

import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build  # noqa: E402
import check_site  # noqa: E402


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def run_checker(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = check_site.main([str(a) for a in args])
    return code, out.getvalue()


class BuildTests(unittest.TestCase):
    def test_repo_content_is_valid_and_docs_are_current(self):
        cfg = load("storefront.json")
        build.validate(cfg)
        for name, text in build.outputs(cfg).items():
            self.assertEqual((ROOT / "docs" / name).read_text(encoding="utf-8"), text,
                             f"docs/{name} is stale; run python3 scripts/build.py")

    def test_example_uses_every_field(self):
        cfg = load("examples/storefront.example.json")
        build.validate(cfg)
        used = {"": set(cfg), "site": set(cfg["site"]), "seo": set(cfg["seo"]),
                "hero": set(cfg["hero"]), "product": set(cfg["product"])}
        used["offer"] = set().union(*(o.keys() for o in cfg["product"]["offers"]))
        used["section"] = set().union(*(s.keys() for s in cfg["sections"]))
        used["action"] = set().union(*(a.keys() for a in cfg["hero"]["actions"]))
        used["link"] = set().union(*(a.keys() for s in cfg["sections"] for a in s.get("links", [])))
        used["faq"] = set().union(*(q.keys() for q in cfg["faq"]))
        used["footer"] = set().union(*(f.keys() for f in cfg["footer"]))
        for kind, keys in build.SCHEMA.items():
            self.assertEqual(keys - used[kind], set(), f"example is missing {kind or 'top-level'} fields")

    def test_rejects_unknown_and_bad_fields(self):
        base = load("storefront.json")
        cases = [
            lambda c: c["seo"].update(titel="typo"),
            lambda c: c["product"]["offers"][0].update(price="$99"),
            lambda c: c["product"]["offers"][0].update(currency="usd"),
            lambda c: c["site"].update(url="http://example.com"),
            lambda c: c["sections"][0].update(include="testimonials"),
            lambda c: c["hero"].pop("heading"),
        ]
        for mutate in cases:
            cfg = copy.deepcopy(base)
            mutate(cfg)
            with self.assertRaises(build.ContentError):
                build.validate(cfg)

    def test_text_is_escaped(self):
        cfg = load("storefront.json")
        cfg["hero"]["heading"] = "<script>alert(1)</script>"
        cfg["faq"][0]["answer"] = "</script><b>x</b>"
        html = build.render_page(cfg)
        self.assertNotIn("<script>alert", html)
        self.assertNotIn("</script><b>", html)
        self.assertEqual(html.count("</script>"), 1)

    def test_robots_only_for_domain_root(self):
        cfg = load("storefront.json")
        self.assertNotIn("robots.txt", build.outputs(cfg))
        cfg["site"]["url"] = "https://shop.example.com/"
        self.assertIn("Sitemap: https://shop.example.com/sitemap.xml", build.outputs(cfg)["robots.txt"])


class CheckerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        cfg = load("examples/storefront.example.json")
        with contextlib.redirect_stdout(io.StringIO()):
            build.main(["--config", str(ROOT / "examples/storefront.example.json"), "--out", str(self.dir)])
        (self.dir / "assets").mkdir()
        (self.dir / "assets/social-card.png").write_bytes(b"")
        (self.dir / "assets/hero.png").write_bytes(b"")
        self.cfg = cfg
        self.index = self.dir / "index.html"

    def tearDown(self):
        self.tmp.cleanup()

    def edit(self, old, new):
        html = self.index.read_text(encoding="utf-8")
        self.assertIn(old, html)
        self.index.write_text(html.replace(old, new, 1), encoding="utf-8")

    def test_published_docs_pass(self):
        code, out = run_checker(ROOT / "docs")
        self.assertEqual(code, 0, out)

    def test_rendered_example_passes(self):
        code, out = run_checker(self.dir)
        self.assertEqual(code, 0, out)

    def assertFails(self, needle):
        code, out = run_checker(self.dir)
        self.assertEqual(code, 1, out)
        self.assertIn(needle, out)

    def test_missing_meta(self):
        self.edit('<meta name="twitter:card"', '<meta name="x-card"')
        self.assertFails('missing <meta name="twitter:card">')

    def test_broken_internal_link_and_fragment(self):
        self.edit('href="#pricing"', 'href="nope.html"')
        self.assertFails("points to missing file")

    def test_broken_fragment(self):
        self.edit('href="#pricing"', 'href="#nowhere"')
        self.assertFails("missing #nowhere")

    def test_invalid_json_ld(self):
        self.edit('"@context"', '"@context":,')
        self.assertFails("does not parse")

    def test_json_ld_must_match_visible_text(self):
        self.edit("<p>A ZIP file with a README.</p>", "<p>Something else.</p>")
        self.assertFails("Answer.text is not visible")

    def test_price_must_be_visible(self):
        self.edit("$19 one-time", "one-time")
        self.assertFails("Offer price 19 USD is not visible")

    def test_heading_skip(self):
        self.edit("<h2 id=\"what-you-get-title\">What You Get</h2>", "<h4 id=\"what-you-get-title\">What You Get</h4>")
        self.assertFails("heading level skips")

    def test_sitemap_coverage(self):
        (self.dir / "extra.html").write_text(
            self.index.read_text(encoding="utf-8").replace(
                'rel="canonical" href="https://yourname.github.io/your-product/"',
                'rel="canonical" href="https://yourname.github.io/your-product/extra.html"').replace(
                'og:url" content="https://yourname.github.io/your-product/"',
                'og:url" content="https://yourname.github.io/your-product/extra.html"'),
            encoding="utf-8")
        self.assertFails("extra.html (canonical https://yourname.github.io/your-product/extra.html) is not listed")

    def test_sitemap_stale_entry(self):
        sm = self.dir / "sitemap.xml"
        sm.write_text(sm.read_text().replace("</urlset>", "  <url><loc>https://yourname.github.io/your-product/gone.html</loc></url>\n</urlset>"))
        self.assertFails("gone.html has no matching file")


if __name__ == "__main__":
    unittest.main()
