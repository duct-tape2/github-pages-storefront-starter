# Changelog

This file follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions match GitHub release tags.

## [Unreleased]

### Added
- `storefront.json`, the single content file for the page. `scripts/build.py` (Python 3 stdlib) renders `docs/index.html` and `docs/sitemap.xml` from it, and `--check` fails when `docs/` is stale.
- `scripts/check_site.py` (Python 3 stdlib) checks internal links and fragments, required meta tags, heading order, image alt text, JSON-LD parsing and visible-text consistency, and sitemap coverage.
- `.github/workflows/site-check.yml` runs the build check, site checker, and unit tests on pull requests only, with a read-only token.
- `tests/test_scripts.py`: unit tests for the build and checker.
- `examples/storefront.example.json`, covering every supported field.
- `docs/CUSTOMIZING.md` (field reference and common tasks), `docs/sitemap.xml`, and `docs/.nojekyll`.
- Product/Offer/FAQPage JSON-LD on the live sample page and the lite example, built only from visible text.
- `og:image:alt`, `twitter:image:alt`, and `theme-color`, plus an empty inline favicon so browsers don't request a missing `/favicon.ico`.
- Skip link, visible keyboard focus ring, and landmark-labelled sections.

### Changed
- `README.md` now starts with a five-step quickstart: copy, edit one file, build/check, enable Pages, verify.
- `docs/index.html` is generated, and its copy and links are unchanged. The "Done For You" text moved into price cards (Free / $99). The nine-button checker row became two buttons plus a link list. A short FAQ reuses existing README sentences word for word.
- CSS is mobile-first. Buttons wrap instead of overflowing at 375px, and the long checker command wraps.
- In `examples/free-storefront-lite.html`, `og:type` changed from `product` to `website`. The page gained a visible placeholder price, JSON-LD, and a skip link. Dot-separated links became a list.
- `CHECKLIST.md`: the Quick Test section now lists the offline checks.

## [v1.0-free-sample]

### Added
- Free sample checklist, lite storefront HTML example, live sample page, and issue forms.
