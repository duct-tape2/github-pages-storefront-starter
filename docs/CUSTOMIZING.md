# Customizing the Storefront

Everything on the page comes from [`storefront.json`](../storefront.json). Edit it, run `python3 scripts/build.py`, then `python3 scripts/check_site.py`. [`examples/storefront.example.json`](../examples/storefront.example.json) uses every field below.

All text is plain text. The build escapes it, so HTML tags show up as literal characters. Keys that start with `_` (like `"_comment"`) are ignored. Unknown keys are rejected so typos fail loudly.

> Note: files in `docs/` are published by GitHub Pages, including this one. That's harmless, but you can move Markdown docs elsewhere if you want only the storefront online.

## Field reference

**Required** fields are in bold.

### `site`
| Field | Notes |
| --- | --- |
| **`url`** | Public page address, `https://` and ending in `/`. Used for canonical, `og:url`, sitemap, and to turn relative image paths into absolute ones. |
| **`name`** | Site name (`og:site_name`). |
| `lang` | Page language, default `en`. |
| `theme_color` | Browser UI color on mobile, e.g. `#15131d`. |

### `seo`
| Field | Notes |
| --- | --- |
| **`title`** | `<title>`. Aim for under 60 characters. |
| **`description`** | Meta description. Aim for 120–160 characters. |
| `social_title`, `social_description` | Open Graph and Twitter text. Default to `title` / `description`. |
| `image` | Social card, relative to `site.url` (e.g. `assets/social-card.png`) or absolute. 1200×630 works everywhere. |
| `image_width`, `image_height`, `image_alt` | Recommended whenever `image` is set. |
| `og_type` | Default `website`. |
| `twitter_site` | Your `@handle`, if you want it in link previews. |

### `hero`
| Field | Notes |
| --- | --- |
| **`heading`** | The page's only `<h1>`. |
| `eyebrow`, `lead` | Small label above and paragraph below the heading. |
| `background_image` | Decorative image shown faintly behind the hero. It's decorative, so it needs no alt text. Keep it small (under ~150 KB). |
| `actions` | Buttons: `{ "label", "url", "style": "primary" \| "secondary" }`. The first one is primary unless you set `style`. |

### `product` (drives the Product/Offer JSON-LD)
| Field | Notes |
| --- | --- |
| **`name`**, **`description`** | Must also appear as visible text on the page. Reusing `hero.heading` / `hero.lead` is easiest. |
| `brand`, `sku`, `image` | Optional Product fields. |
| **`offers`** | List of offers, rendered as price cards. |

Each offer:

| Field | Notes |
| --- | --- |
| **`name`** | Card heading. |
| **`price`** | Plain number string: `"19"`, `"49.50"`, `"0"` for free. |
| **`currency`** | ISO 4217 code: `USD`, `EUR`, `GBP`, `CAD`… |
| `price_label` | Overrides the visible price (default `$19`, `Free`, or `19 CAD`). It must still contain the number. |
| `description`, `url`, `actions` | Card text, offer link, and buttons. |
| `availability` | `InStock`, `OutOfStock`, `PreOrder`, `OnlineOnly`, `SoldOut`, or `Discontinued`. Leave it out if you're not sure. |
| `item_type` | Set it to `Service` when the offer is a service rather than the product itself. |

### `sections`
A list of page sections, in order. Each one needs a **`heading`**. Optional fields render in this order:

`paragraphs` (list of strings) · `list` (bullets) · `columns` (list of bullet lists shown as side-by-side cards) · `code` (one command) · `actions` (buttons) · `links_heading` + `links` (`{ "label", "url" }` list)

- `id` sets the `#anchor`. The default is the heading in slug form, e.g. `#delivery-and-support`.
- `"include": "offers"` puts the offer cards in that section, and `"include": "faq"` puts the FAQ there. Without them, offers go at the end under **Pricing**, followed by the FAQ under **Questions**.

### `faq`
A list of `{ "question", "answer" }` objects. It renders visibly and builds FAQPage JSON-LD from the same text. Leave the list empty to omit both.

### `footer`
A list of `{ "text", "label", "url" }` lines. `label` and `url` are optional.

## Common tasks

**Change colors.** Edit the CSS variables at the top of the `CSS` string in `scripts/build.py` (`--accent`, `--paper`, `--night`…). Keep body text at a 4.5:1 contrast ratio or better against its background.

**Replace images.** Put files in `docs/assets/` and reference them as `assets/name.png`. The checker fails if a referenced local file is missing.

**Custom domain.** In **Settings → Pages**, set the domain, then change `site.url` to `https://yourdomain.com/` and rebuild. At a domain root the build also writes `robots.txt` pointing at the sitemap. On a `user.github.io/repo/` project site, crawlers ignore `robots.txt`, so the build skips it. Submit the sitemap in Search Console instead.

**Add a second page.** Hand-write `docs/other.html` (copy the `<head>` pattern from `docs/index.html`), add its URL to `docs/sitemap.xml`, and run the checker. It verifies links, meta tags, and that every page is in the sitemap. Rebuilding only rewrites `index.html` and `sitemap.xml`, so re-add the extra URL to the sitemap after each build, or keep the page out of the sitemap with `<meta name="robots" content="noindex">`.

**Preview locally.** `python3 -m http.server -d docs 8000`, then open <http://localhost:8000/>.

**Preview the example content.** `python3 scripts/build.py --config examples/storefront.example.json --out /tmp/preview --no-sitemap`

## What the checker enforces

`python3 scripts/check_site.py [dir-or-file ...]` (default `docs`), exit code 1 on any `FAIL`:

- `lang`, charset, `<title>`, description, viewport, absolute https canonical, `og:type/title/description/url/image`, `twitter:card/title/description/image`, and `og:url` matching the canonical
- internal links, CSS `url()` references, and image, script, and `og:image` files exist, `#fragments` exist, and there are no root-relative `/paths` that break on project sites
- exactly one `<h1>`, no skipped heading levels, every `<img>` has `alt`
- every JSON-LD block parses. Product has a name and offers, each Offer has a price and currency, and FAQ questions have answers. Product and offer names, descriptions, prices, and FAQ text must be **visible on the page**.
- `sitemap.xml` lists every indexable page, and every sitemap URL maps to a real file

It doesn't fetch external URLs, so it works offline and in CI without network access.
