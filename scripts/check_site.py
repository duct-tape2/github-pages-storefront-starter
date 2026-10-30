#!/usr/bin/env python3
"""Check a static GitHub Pages site before it ships.

Python 3 standard library only. Usage:

    python3 scripts/check_site.py                 # checks docs/
    python3 scripts/check_site.py docs examples/free-storefront-lite.html
    python3 scripts/check_site.py --no-sitemap examples/rendered

For every HTML page it checks:
  * required meta tags (title, description, viewport, canonical, Open Graph,
    Twitter card) and that og:url matches the canonical URL
  * internal links, image/script/style sources and #fragments resolve
  * exactly one <h1>, no skipped heading levels, every <img> has alt text
  * every JSON-LD block parses; Product/Offer/FAQPage carry required fields
    and their text (names, prices, questions, answers) is visible on the page
For a directory it also checks sitemap.xml coverage in both directions.

Exits 1 when any FAIL is reported. WARN lines do not fail the run.
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

ROOT = Path(__file__).resolve().parent.parent
REQUIRED_META = [
    ("name", "description"),
    ("name", "viewport"),
    ("property", "og:type"),
    ("property", "og:title"),
    ("property", "og:description"),
    ("property", "og:url"),
    ("property", "og:image"),
    ("name", "twitter:card"),
    ("name", "twitter:title"),
    ("name", "twitter:description"),
    ("name", "twitter:image"),
]
SKIP_SCHEMES = {"mailto", "tel", "javascript", "data", "sms"}
CSS_URL = re.compile(r"""url\(\s*['"]?([^'")]+)['"]?\s*\)""")
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = None
        self.charset = False
        self.title = ""
        self.meta = {}
        self.canonical = None
        self.refs = []          # (kind, url)
        self.ids = set()
        self.headings = []
        self.images_missing_alt = []
        self.ld_json = []
        self.text = []
        self._stack = []
        self._in_title = False
        self._ld = None
        self._style = None

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "html":
            self.lang = a.get("lang")
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a" and "name" in a:
            self.ids.add(a["name"])
        if tag == "meta":
            if "charset" in a:
                self.charset = True
            for key in ("name", "property"):
                if key in a:
                    self.meta[(key, a[key].lower())] = a.get("content", "")
        elif tag == "link":
            rel = a.get("rel", "").lower().split()
            if "canonical" in rel:
                self.canonical = a.get("href")
            elif a.get("href"):
                self.refs.append(("link", a["href"]))
        elif tag == "a" and a.get("href") is not None:
            self.refs.append(("a", a["href"]))
        elif tag in ("img", "source", "script", "iframe", "video", "audio") and a.get("src"):
            self.refs.append((tag, a["src"]))
        if tag == "img" and "alt" not in a:
            self.images_missing_alt.append(a.get("src", "?"))
        if "style" in a:
            self.refs += [("css", u) for u in CSS_URL.findall(a["style"])]
        if re.fullmatch(r"h[1-6]", tag):
            self.headings.append(int(tag[1]))
        if tag == "title":
            self._in_title = True
        if tag == "script" and a.get("type", "").lower() == "application/ld+json":
            self._ld = []
        if tag == "style":
            self._style = []
        if tag not in ("meta", "link", "img", "br", "hr", "input", "source", "wbr"):
            self._stack.append(tag)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag == "script" and self._ld is not None:
            self.ld_json.append("".join(self._ld))
            self._ld = None
        if tag == "style" and self._style is not None:
            self.refs += [("css", u) for u in CSS_URL.findall("".join(self._style))]
            self._style = None
        if tag in self._stack:
            while self._stack and self._stack.pop() != tag:
                pass

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._ld is not None:
            self._ld.append(data)
        if self._style is not None:
            self._style.append(data)
        if not {"head", "script", "style", "noscript", "template"} & set(self._stack):
            self.text.append(data)

    def visible_text(self):
        return normalize(" ".join(self.text))


def normalize(s):
    return re.sub(r"\s+", " ", s).strip()


class Report:
    def __init__(self):
        self.fails = 0
        self.warns = 0

    def fail(self, where, msg):
        self.fails += 1
        print(f"FAIL {where}: {msg}")

    def warn(self, where, msg):
        self.warns += 1
        print(f"WARN {where}: {msg}")

    def ok(self, where, msg):
        print(f"PASS {where}: {msg}")


def parse(path):
    page = Page()
    page.feed(path.read_text(encoding="utf-8"))
    page.close()
    return page


def resolve_local(url, page_path, root, base_url):
    """Map an internal URL to (file path, fragment). None means external/skipped."""
    parsed = urlparse(url)
    if parsed.scheme in SKIP_SCHEMES:
        return None
    if parsed.scheme or parsed.netloc:
        if not base_url or not url.startswith(base_url):
            return None
        rel = unquote(urlparse(url).path)[len(urlparse(base_url).path):]
        target = root / rel
    elif parsed.path == "":
        target = page_path
    elif parsed.path.startswith("/"):
        # Root-relative paths break on project sites (user.github.io/repo/).
        base_path = urlparse(base_url).path if base_url else "/"
        if not parsed.path.startswith(base_path):
            return ("root-relative", parsed.fragment)
        target = root / unquote(parsed.path[len(base_path):])
    else:
        target = page_path.parent / unquote(parsed.path)
    if url.endswith("/") or target.is_dir():
        target = target / "index.html"
    elif not target.suffix and not target.exists():
        target = target.with_suffix(".html")
    return (target, parsed.fragment)


def walk_types(node, found):
    if isinstance(node, list):
        for x in node:
            walk_types(x, found)
    elif isinstance(node, dict):
        types = node.get("@type")
        for t in (types if isinstance(types, list) else [types]):
            if t:
                found.setdefault(t, []).append(node)
        for v in node.values():
            if isinstance(v, (dict, list)):
                walk_types(v, found)


def price_visible(price, currency, text):
    p = str(price)
    if float(p) == 0:
        return bool(re.search(r"\bfree\b", text, re.I)) or "0" in text
    variants = {p, p.rstrip("0").rstrip(".") if "." in p else p}
    return any(re.search(r"(?<![\d.])" + re.escape(v) + r"(?![\d])", text) for v in variants)


def check_ld(where, page, rep):
    before = rep.fails
    text = page.visible_text()
    if not page.ld_json:
        rep.fail(where, "no JSON-LD block")
        return
    found = {}
    for i, raw in enumerate(page.ld_json):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as err:
            rep.fail(where, f"JSON-LD block {i + 1} does not parse: {err}")
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and "schema.org" not in str(item.get("@context", "")):
                rep.fail(where, f"JSON-LD block {i + 1} has no schema.org @context")
        walk_types(data, found)

    def must_be_visible(label, value):
        if value and normalize(str(value)) not in text:
            rep.fail(where, f"JSON-LD {label} is not visible on the page: {value!r}")

    products = found.get("Product", [])
    if not products:
        rep.fail(where, "JSON-LD has no Product")
    for prod in products:
        if not prod.get("name"):
            rep.fail(where, "Product has no name")
        must_be_visible("Product.name", prod.get("name"))
        must_be_visible("Product.description", prod.get("description"))
        offers = prod.get("offers")
        offers = offers if isinstance(offers, list) else [offers] if offers else []
        if not offers:
            rep.fail(where, "Product has no offers")
        for off in offers:
            if off.get("price") in (None, "") or not off.get("priceCurrency"):
                rep.fail(where, f"Offer {off.get('name', '?')!r} needs price and priceCurrency")
                continue
            try:
                visible = price_visible(off["price"], off["priceCurrency"], text)
            except ValueError:
                rep.fail(where, f"Offer price is not a number: {off['price']!r}")
                continue
            if not visible:
                rep.fail(where, f"Offer price {off['price']} {off['priceCurrency']} is not visible on the page")
            must_be_visible("Offer.name", off.get("name"))
            must_be_visible("Offer.description", off.get("description"))
    faqs = found.get("FAQPage", [])
    if not faqs:
        rep.warn(where, "JSON-LD has no FAQPage (fine if the page has no FAQ)")
    for faq in faqs:
        questions = faq.get("mainEntity") or []
        if not questions:
            rep.fail(where, "FAQPage has no mainEntity questions")
        for q in questions if isinstance(questions, list) else [questions]:
            answer = (q.get("acceptedAnswer") or {}).get("text")
            if not q.get("name") or not answer:
                rep.fail(where, "FAQ Question needs name and acceptedAnswer.text")
            must_be_visible("Question.name", q.get("name"))
            must_be_visible("Answer.text", answer)
    if rep.fails == before:
        rep.ok(where, f"JSON-LD types: {', '.join(sorted(found)) or 'none'}")


def check_page(path, root, base_url, rep, cache):
    where = str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)
    page = cache.setdefault(path, parse(path))
    before = rep.fails

    if not page.lang:
        rep.fail(where, '<html> has no lang attribute')
    if not page.charset:
        rep.fail(where, "no <meta charset>")
    if not normalize(page.title):
        rep.fail(where, "empty or missing <title>")
    for key in REQUIRED_META:
        if not page.meta.get(key, "").strip():
            rep.fail(where, f'missing <meta {key[0]}="{key[1]}">')
    if not page.canonical or not page.canonical.startswith("https://"):
        rep.fail(where, "missing absolute https canonical link")
    elif page.meta.get(("property", "og:url")) and page.meta[("property", "og:url")] != page.canonical:
        rep.fail(where, "og:url does not match canonical")
    og_image = page.meta.get(("property", "og:image"), "")
    if og_image and not og_image.startswith(("https://", "http://")):
        rep.fail(where, "og:image must be an absolute URL")
    elif og_image:
        page.refs.append(("og:image", og_image))
    if not page.meta.get(("property", "og:image:alt")):
        rep.warn(where, "no og:image:alt")

    h1 = page.headings.count(1)
    if h1 != 1:
        rep.fail(where, f"expected exactly one <h1>, found {h1}")
    for prev, cur in zip(page.headings, page.headings[1:]):
        if cur > prev + 1:
            rep.fail(where, f"heading level skips from h{prev} to h{cur}")
            break
    for src in page.images_missing_alt:
        rep.fail(where, f"<img src={src!r}> has no alt attribute")

    checked = 0
    for kind, url in page.refs:
        target = resolve_local(url.strip(), path, root, base_url)
        if target is None:
            continue
        file, frag = target
        checked += 1
        if file == "root-relative":
            rep.fail(where, f"{kind} {url!r} is root-relative and breaks on project Pages sites")
            continue
        if not file.exists():
            rep.fail(where, f"{kind} {url!r} points to missing file {file}")
            continue
        if frag and file.suffix == ".html" and frag != "top":
            target_page = cache.setdefault(file, parse(file))
            if frag not in target_page.ids:
                rep.fail(where, f"{kind} {url!r} points to missing #{frag}")
    check_ld(where, page, rep)
    if rep.fails == before:
        rep.ok(where, f"meta tags, headings, {checked} internal reference(s)")
    return page


def check_sitemap(root, pages, base_url, rep):
    where = str((root / "sitemap.xml").relative_to(ROOT) if root.is_relative_to(ROOT) else root / "sitemap.xml")
    sm = root / "sitemap.xml"
    if not sm.exists():
        rep.fail(where, "missing")
        return
    try:
        locs = [el.text.strip() for el in ET.parse(sm).getroot().iter(f"{SITEMAP_NS}loc") if el.text]
    except ET.ParseError as err:
        rep.fail(where, f"does not parse: {err}")
        return
    if not locs:
        rep.fail(where, "has no <loc> entries")
    before = rep.fails
    for path, page in pages.items():
        robots = page.meta.get(("name", "robots"), "").lower()
        if path.name == "404.html" or "noindex" in robots:
            continue
        if page.canonical not in locs:
            rep.fail(where, f"page {path.relative_to(root)} (canonical {page.canonical}) is not listed")
    for loc in locs:
        target = resolve_local(loc, root / "index.html", root, base_url)
        if target is None:
            rep.fail(where, f"{loc} is outside the site base {base_url}")
        elif not Path(target[0]).exists():
            rep.fail(where, f"{loc} has no matching file")
    if rep.fails == before:
        rep.ok(where, f"{len(locs)} URL(s), every indexable page covered")
    robots_txt = root / "robots.txt"
    if robots_txt.exists() and "sitemap:" not in robots_txt.read_text(encoding="utf-8").lower():
        rep.warn(str(robots_txt), "robots.txt does not reference the sitemap")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="*", default=[str(ROOT / "docs")],
                    help="site directories or single HTML files (default: docs)")
    ap.add_argument("--no-sitemap", action="store_true", help="skip sitemap.xml checks for directories")
    args = ap.parse_args(argv)

    rep = Report()
    for arg in args.paths:
        target = Path(arg).resolve()
        if not target.exists():
            rep.fail(arg, "does not exist")
            continue
        root = target if target.is_dir() else target.parent
        files = sorted(target.rglob("*.html")) if target.is_dir() else [target]
        index = root / "index.html"
        base_url = None
        if index.exists():
            base_url = parse(index).canonical
        cache, pages = {}, {}
        for f in files:
            page = check_page(f, root, base_url or parse(f).canonical, rep, cache)
            pages[f] = page
        if target.is_dir() and not args.no_sitemap:
            check_sitemap(root, pages, base_url, rep)
    print(f"\n{rep.fails} failure(s), {rep.warns} warning(s)")
    return 1 if rep.fails else 0


if __name__ == "__main__":
    sys.exit(main())
