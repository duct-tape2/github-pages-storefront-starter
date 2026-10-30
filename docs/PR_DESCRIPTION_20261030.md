# Template quality pass: one-file quickstart, checker, SEO/a11y defaults

## Summary

Forking this template now means editing one file. `storefront.json` drives the page, `scripts/build.py` renders `docs/`, and `scripts/check_site.py` checks links, meta tags, JSON-LD, and the sitemap. Both scripts use only the Python 3 standard library, and a PR-only workflow runs them with the unit tests.

The live sample page is now generated from that file. Its copy, prices, and links are unchanged. The branch also fixes a real bug on the live page: **12 secondary buttons, including the paid-inquiry links, were white text on the light background (1.09:1 contrast) and practically invisible.**

Full findings: [`docs/REVIEW_20261030.md`](REVIEW_20261030.md).

## Changes by area

**Quickstart and docs**
- `README.md` now opens with five steps: copy the template, edit `storefront.json`, build and check, enable Pages from `/docs`, verify. All existing sections and links are kept, and a repo-layout table was added.
- `docs/CUSTOMIZING.md` gives a reference for every field and covers colors, images, custom domains, extra pages, and local preview.
- `CHECKLIST.md` adds the offline check commands to Quick Test. Nothing was removed.
- `CHANGELOG.md` is new.

**Template defaults (`scripts/build.py` → `docs/index.html`)**
- Semantic HTML: header/main/footer, one `<h1>`, sections labelled by `<h2>`, offers as `<article>`.
- Accessibility: a skip link is the first Tab stop, focus rings are 3px, and all text is ≥ 4.5:1 contrast (measured). Tap targets are ≥ 48px tall.
- Mobile-first CSS: one column with full-width buttons at 375px, with no horizontal scroll (measured).
- Speed: one HTML file with inline CSS. No external fonts, scripts, or CSS. The favicon is an empty `data:` icon, which avoids a 404.
- SEO: title, description, canonical, `og:*` including image size and alt, Twitter card with image alt, and `theme-color`. JSON-LD is a `@graph` of Product → Offers (Free; $99 with `itemOffered: Service`) plus FAQPage, all from the same strings shown on the page. `sitemap.xml` is generated. `robots.txt` is written only when the site is at a domain root, and `.nojekyll` is added.
- Content validation: unknown keys, malformed prices, and lowercase currency codes are rejected, and the URL must be https and end with `/`. All text is HTML-escaped, and `</` is escaped inside JSON-LD.

**Checker and CI**
- `scripts/check_site.py` checks required meta tags, og:url against the canonical, internal links and `#fragments`, CSS `url()` and og:image files, root-relative paths (which break project sites), heading order, image alt text, JSON-LD parsing and required fields, JSON-LD text against visible text, and two-way sitemap coverage. It works offline.
- `tests/test_scripts.py` has 16 unittest cases covering a valid build, schema rejection, escaping, robots logic, and checker pass/fail cases.
- `.github/workflows/site-check.yml` runs on `pull_request` only, with `contents: read`, a SHA-pinned checkout with `persist-credentials: false`, and no secrets or deploy steps.

**Examples**
- `examples/storefront.example.json` uses every supported field, with `_comment` notes. A test enforces that it stays complete.
- `examples/free-storefront-lite.html` (the hand-edit version) gets a placeholder visible price, JSON-LD, a skip link, focus styles, and mobile-first CSS. `og:type` changes from `product` to `website`, and the dot-separated links become a list.

**Case study:** no case-study pages exist in this repo (the case study is served from another repo), so nothing was changed. See the owner decisions below.

## Test and check output

```
$ python3 scripts/build.py --check
build: output is up to date
exit 0

$ python3 scripts/check_site.py docs
PASS docs/index.html: JSON-LD types: Answer, Brand, FAQPage, Offer, Product, Question, Service
PASS docs/index.html: meta tags, headings, 3 internal reference(s)
PASS docs/sitemap.xml: 1 URL(s), every indexable page covered

0 failure(s), 0 warning(s)
exit 0

$ python3 scripts/check_site.py examples/free-storefront-lite.html
FAIL examples/free-storefront-lite.html: og:image 'https://yourname.github.io/your-product/social-card.png' points to missing file /home/user/repo/examples/social-card.png
PASS examples/free-storefront-lite.html: JSON-LD types: Answer, FAQPage, Offer, Product, Question

1 failure(s), 0 warning(s)
exit 1        # expected: placeholder image the forker must supply; not run in CI

$ python3 -m unittest discover -s tests
Ran 16 tests in 0.112s
OK

Browser (headless Chromium), docs/index.html:
375px:  scrollWidth 375 = viewport, 0 text nodes below 4.5:1, first Tab = "Skip to content" (focus ring visible)
1280px: scrollWidth 1280 = viewport, 0 text nodes below 4.5:1, first Tab = "Skip to content"
Same script on the original page: 12 links at 1.09:1, no skip link.
```

Not run: the workflow on GitHub itself, since this sandbox has no credentials. Its YAML parses and runs exactly the three commands above.

## Needs the owner's decision

1. **The social card advertises "$19"** (a "GitHub Pages DIY Kit"), but nothing on the site offers a $19 product. Publish the kit or replace `docs/assets/storefront-starter-hero.png`. Until then, Product JSON-LD deliberately has no `image`.
2. **Case study pages** live in the repo behind `duct-tape2.github.io/examples/storefront-starter-case-study/`. Run the same structure-only pass there if wanted.
3. **New FAQ section.** All four answers are copied word for word from the README, and I wrote only the questions. Keep it, reword it, or delete the `faq` entries.
4. **Price cards.** "Done For You" now shows a Free card and a $99 card ("Buyer-ready repo page", named from the existing footer link). The prices and the text are unchanged.
5. **$99 refund or support terms** aren't on the page, although the checklist asks for them. I added none.
6. **"full kit"** in "upgrade path to the full kit or service" isn't described anywhere. Clarify or remove it.
7. **`?sample=1`** on the raw checklist link does nothing there. Keep it or drop it.
8. **Markdown docs in `docs/`** (the review, this file, the customization guide) are publicly served by Pages. Move them if unwanted.
9. **New release.** The `v1.0-free-sample` ZIP predates these changes.
10. **Hero background PNG** (80 KB at 8–13% opacity). Keep it, convert it to WebP, or drop it.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01SfVnRs8UcrPJcHFCR6WDwM
