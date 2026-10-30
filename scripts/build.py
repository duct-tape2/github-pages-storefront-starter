#!/usr/bin/env python3
"""Render the storefront page from one JSON content file.

Python 3 standard library only. Usage:

    python3 scripts/build.py                      # storefront.json -> docs/
    python3 scripts/build.py --check              # fail if docs/ is out of date
    python3 scripts/build.py --config examples/storefront.example.json \
        --out examples/rendered --no-sitemap

Writes index.html and sitemap.xml (plus robots.txt when the site lives at a
domain root, the only place crawlers read it). All text is HTML-escaped; the
content file cannot inject markup or scripts.
"""

import argparse
import json
import re
import sys
from html import escape
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parent.parent

# Allowed keys per object. Unknown keys are rejected so typos fail loudly.
SCHEMA = {
    "": {"site", "seo", "hero", "product", "sections", "faq", "footer"},
    "site": {"url", "name", "lang", "theme_color"},
    "seo": {"title", "description", "social_title", "social_description", "image",
            "image_width", "image_height", "image_alt", "og_type", "twitter_site"},
    "hero": {"eyebrow", "heading", "lead", "background_image", "actions"},
    "product": {"name", "description", "brand", "image", "sku", "offers"},
    "offer": {"name", "price", "currency", "url", "description", "availability",
              "item_type", "price_label", "actions"},
    "section": {"id", "heading", "paragraphs", "list", "columns", "code", "actions",
                "links_heading", "links", "include"},
    "action": {"label", "url", "style"},
    "link": {"label", "url"},
    "faq": {"question", "answer"},
    "footer": {"text", "label", "url"},
}
REQUIRED = {
    "site": {"url", "name"},
    "seo": {"title", "description"},
    "hero": {"heading"},
    "product": {"name", "description", "offers"},
    "offer": {"name", "price", "currency"},
    "section": {"heading"},
    "action": {"label", "url"},
    "link": {"label", "url"},
    "faq": {"question", "answer"},
    "footer": {"text"},
}
AVAILABILITY = {"InStock", "OutOfStock", "PreOrder", "OnlineOnly", "SoldOut", "Discontinued"}
SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£"}


class ContentError(ValueError):
    pass


def check_keys(obj, kind, where):
    if not isinstance(obj, dict):
        raise ContentError(f"{where}: expected an object")
    # Keys starting with "_" are comments and are ignored.
    unknown = {k for k in obj if not k.startswith("_")} - SCHEMA[kind]
    if unknown:
        raise ContentError(f"{where}: unknown field(s) {sorted(unknown)}; allowed: {sorted(SCHEMA[kind])}")
    missing = {k for k in REQUIRED.get(kind, ()) if obj.get(k) in (None, "", [])}
    if missing:
        raise ContentError(f"{where}: missing required field(s) {sorted(missing)}")


def validate(cfg):
    check_keys(cfg, "", "content")
    for key in ("site", "seo", "hero", "product"):
        check_keys(cfg.get(key) or {}, key, key)
    url = cfg["site"]["url"]
    if not re.match(r"^https://[^/]+/(.*/)?$", url):
        raise ContentError("site.url: must be an absolute https URL ending in '/'")
    for i, a in enumerate(cfg["hero"].get("actions", [])):
        check_keys(a, "action", f"hero.actions[{i}]")
    for i, o in enumerate(cfg["product"]["offers"]):
        where = f"product.offers[{i}]"
        check_keys(o, "offer", where)
        if not re.match(r"^\d+(\.\d{1,2})?$", str(o["price"])):
            raise ContentError(f"{where}.price: use a plain number such as \"19\" or \"19.50\"")
        if not re.match(r"^[A-Z]{3}$", o["currency"]):
            raise ContentError(f"{where}.currency: use an ISO 4217 code such as \"USD\"")
        if o.get("availability") and o["availability"] not in AVAILABILITY:
            raise ContentError(f"{where}.availability: one of {sorted(AVAILABILITY)}")
        for j, a in enumerate(o.get("actions", [])):
            check_keys(a, "action", f"{where}.actions[{j}]")
    for i, s in enumerate(cfg.get("sections", [])):
        where = f"sections[{i}]"
        check_keys(s, "section", where)
        if s.get("include") not in (None, "offers", "faq"):
            raise ContentError(f"{where}.include: must be \"offers\" or \"faq\"")
        for j, a in enumerate(s.get("actions", [])):
            check_keys(a, "action", f"{where}.actions[{j}]")
        for j, a in enumerate(s.get("links", [])):
            check_keys(a, "link", f"{where}.links[{j}]")
    for i, q in enumerate(cfg.get("faq", [])):
        check_keys(q, "faq", f"faq[{i}]")
    for i, f in enumerate(cfg.get("footer", [])):
        check_keys(f, "footer", f"footer[{i}]")


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "section"


def price_label(offer):
    if offer.get("price_label"):
        return offer["price_label"]
    price = offer["price"]
    if float(price) == 0:
        return "Free"
    symbol = SYMBOLS.get(offer["currency"])
    return f"{symbol}{price}" if symbol else f"{price} {offer['currency']}"


def e(text):
    return escape(str(text), quote=True)


def render_actions(actions, indent):
    if not actions:
        return ""
    pad = " " * indent
    items = []
    for i, a in enumerate(actions):
        style = a.get("style") or ("primary" if i == 0 else "secondary")
        cls = "btn" if style == "primary" else "btn secondary"
        items.append(f'{pad}  <a class="{cls}" href="{e(a["url"])}">{e(a["label"])}</a>')
    return f'{pad}<div class="actions">\n' + "\n".join(items) + f"\n{pad}</div>\n"


def render_list(items, indent):
    pad = " " * indent
    lis = "\n".join(f"{pad}  <li>{e(x)}</li>" for x in items)
    return f"{pad}<ul>\n{lis}\n{pad}</ul>\n"


def render_offers(offers):
    out = ['      <div class="grid offers">\n']
    for o in offers:
        out.append('        <article class="panel offer">\n')
        out.append(f'          <h3>{e(o["name"])}</h3>\n')
        out.append(f'          <p class="price">{e(price_label(o))}</p>\n')
        if o.get("description"):
            out.append(f'          <p>{e(o["description"])}</p>\n')
        out.append(render_actions(o.get("actions"), 10))
        out.append("        </article>\n")
    out.append("      </div>\n")
    return "".join(out)


def render_faq(faq):
    out = []
    for q in faq:
        out.append('      <div class="faq-item">\n')
        out.append(f'        <h3>{e(q["question"])}</h3>\n')
        out.append(f'        <p>{e(q["answer"])}</p>\n')
        out.append("      </div>\n")
    return "".join(out)


def render_section(s, cfg):
    sid = s.get("id") or slug(s["heading"])
    out = [f'    <section id="{e(sid)}" aria-labelledby="{e(sid)}-title">\n',
           f'      <h2 id="{e(sid)}-title">{e(s["heading"])}</h2>\n']
    for p in s.get("paragraphs", []):
        out.append(f'      <p class="muted">{e(p)}</p>\n')
    if s.get("list"):
        out.append(render_list(s["list"], 6))
    if s.get("columns"):
        out.append('      <div class="grid">\n')
        for col in s["columns"]:
            out.append('        <div class="panel">\n')
            out.append(render_list(col, 10))
            out.append("        </div>\n")
        out.append("      </div>\n")
    if s.get("code"):
        out.append(f'      <pre><code>{e(s["code"])}</code></pre>\n')
    out.append(render_actions(s.get("actions"), 6))
    if s.get("links"):
        if s.get("links_heading"):
            out.append(f'      <h3>{e(s["links_heading"])}</h3>\n')
        out.append('      <ul class="links">\n')
        for link in s["links"]:
            out.append(f'        <li><a href="{e(link["url"])}">{e(link["label"])}</a></li>\n')
        out.append("      </ul>\n")
    if s.get("include") == "offers":
        out.append(render_offers(cfg["product"]["offers"]))
    elif s.get("include") == "faq":
        out.append(render_faq(cfg.get("faq", [])))
    out.append("    </section>\n")
    return "".join(out)


def json_ld(cfg, page_url):
    product = cfg["product"]
    graph = []
    item = {
        "@type": "Product",
        "name": product["name"],
        "description": product["description"],
        "url": page_url,
    }
    if product.get("image"):
        item["image"] = urljoin(page_url, product["image"])
    if product.get("brand"):
        item["brand"] = {"@type": "Brand", "name": product["brand"]}
    if product.get("sku"):
        item["sku"] = product["sku"]
    offers = []
    for o in product["offers"]:
        offer = {"@type": "Offer", "name": o["name"], "price": str(o["price"]),
                 "priceCurrency": o["currency"]}
        if o.get("url"):
            offer["url"] = urljoin(page_url, o["url"])
        if o.get("description"):
            offer["description"] = o["description"]
        if o.get("availability"):
            offer["availability"] = "https://schema.org/" + o["availability"]
        if o.get("item_type"):
            offer["itemOffered"] = {"@type": o["item_type"], "name": o["name"]}
        offers.append(offer)
    item["offers"] = offers
    graph.append(item)
    faq = cfg.get("faq", [])
    if faq:
        graph.append({
            "@type": "FAQPage",
            "mainEntity": [{
                "@type": "Question",
                "name": q["question"],
                "acceptedAnswer": {"@type": "Answer", "text": q["answer"]},
            } for q in faq],
        })
    data = json.dumps({"@context": "https://schema.org", "@graph": graph}, indent=2, ensure_ascii=False)
    # "</" can never appear inside the script element.
    return data.replace("</", "<\\/")


CSS = """    *, *::before, *::after { box-sizing: border-box; }
    :root {
      --ink: #171717;
      --muted: #4d4d4d;
      --paper: #f7f5ef;
      --line: #ded8cb;
      --accent: #165e6f;
      --night: #15131d;
    }
    body {
      margin: 0;
      color: var(--ink);
      background: var(--paper);
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 17px;
      line-height: 1.55;
    }
    a { color: var(--accent); text-underline-offset: 2px; }
    a:focus-visible, .btn:focus-visible {
      outline: 3px solid #f2b705;
      outline-offset: 3px;
    }
    .skip {
      position: absolute;
      left: 12px;
      top: -60px;
      z-index: 10;
      padding: 10px 14px;
      border-radius: 6px;
      color: #fff;
      background: var(--accent);
      font-weight: 700;
    }
    .skip:focus { top: 12px; }
    .hero {
      position: relative;
      display: flex;
      align-items: flex-end;
      overflow: hidden;
      color: #fff;
      background: var(--night);
      padding: 48px 16px 36px;
    }
    .hero::before {
      content: "";
      position: absolute;
      inset: 0;
      background: var(--hero-image, none) 70% center / cover no-repeat;
      opacity: .08;
    }
    .hero::after {
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(180deg, rgba(21,19,29,.08), rgba(21,19,29,.86));
    }
    .inner, main {
      width: min(1040px, 100%);
      margin: 0 auto;
    }
    .hero .inner { position: relative; z-index: 1; }
    .eyebrow {
      margin: 0 0 12px;
      color: #bae6fd;
      font-size: 13px;
      font-weight: 800;
      letter-spacing: .04em;
      text-transform: uppercase;
    }
    h1 {
      max-width: 840px;
      margin: 0;
      font-size: clamp(36px, 9vw, 76px);
      line-height: 1;
      overflow-wrap: break-word;
    }
    .lead {
      max-width: 740px;
      margin: 20px 0 0;
      color: #eef2f7;
      font-size: 19px;
    }
    .actions {
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-top: 22px;
    }
    .btn {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 48px;
      padding: 10px 18px;
      border: 1px solid var(--accent);
      border-radius: 6px;
      color: #fff;
      background: var(--accent);
      font-weight: 800;
      text-align: center;
      text-decoration: none;
    }
    .btn.secondary { color: var(--accent); background: transparent; }
    .hero .btn { border-color: #fff; color: #111; background: #fff; }
    .hero .btn.secondary { color: #fff; background: rgba(255,255,255,.08); }
    main { padding: 24px 16px 48px; }
    section {
      padding: 28px 0;
      border-bottom: 1px solid var(--line);
      scroll-margin-top: 16px;
    }
    h2 { margin: 0 0 14px; font-size: 26px; line-height: 1.15; }
    h3 { margin: 18px 0 8px; font-size: 19px; line-height: 1.25; }
    .grid { display: grid; grid-template-columns: 1fr; gap: 16px; }
    .panel {
      padding: 20px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }
    .panel h3 { margin-top: 0; }
    .price { margin: 0 0 8px; font-size: 28px; font-weight: 800; }
    .muted { color: var(--muted); }
    ul { padding-left: 20px; }
    li { margin: 7px 0; }
    .links li { margin: 10px 0; }
    pre {
      margin: 16px 0;
      padding: 12px 14px;
      border-radius: 6px;
      background: #ece7dc;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }
    code { font-size: 15px; }
    .faq-item h3 { margin-bottom: 4px; }
    .faq-item p { margin-top: 0; }
    footer {
      padding: 28px 16px 44px;
      color: var(--muted);
      text-align: center;
    }
    footer p { margin: 4px 0; }
    @media (min-width: 761px) {
      .hero { min-height: 74vh; padding: 42px 22px; }
      .hero::before { background-position: 72% center; opacity: .13; }
      main { padding: 36px 22px 58px; }
      h2 { font-size: 28px; }
      .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .actions { flex-direction: row; flex-wrap: wrap; gap: 12px; }
      .btn { display: inline-flex; }
    }
"""


def render_page(cfg):
    site, seo, hero, product = cfg["site"], cfg["seo"], cfg["hero"], cfg["product"]
    page_url = site["url"]
    title = seo["title"]
    desc = seo["description"]
    s_title = seo.get("social_title") or title
    s_desc = seo.get("social_description") or desc

    sections = list(cfg.get("sections", []))
    included = {s.get("include") for s in sections}
    if "offers" not in included:
        sections.append({"heading": "Pricing", "include": "offers"})
    if cfg.get("faq") and "faq" not in included:
        sections.append({"heading": "Questions", "include": "faq"})

    head = [
        "<!doctype html>",
        f'<html lang="{e(site.get("lang", "en"))}">',
        "<head>",
        '  <meta charset="utf-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1">',
        f"  <title>{e(title)}</title>",
        f'  <meta name="description" content="{e(desc)}">',
        f'  <link rel="canonical" href="{e(page_url)}">',
        '  <link rel="icon" href="data:,">',
    ]
    if site.get("theme_color"):
        head.append(f'  <meta name="theme-color" content="{e(site["theme_color"])}">')
    head += [
        f'  <meta property="og:type" content="{e(seo.get("og_type", "website"))}">',
        f'  <meta property="og:site_name" content="{e(site["name"])}">',
        f'  <meta property="og:title" content="{e(s_title)}">',
        f'  <meta property="og:description" content="{e(s_desc)}">',
        f'  <meta property="og:url" content="{e(page_url)}">',
    ]
    image = urljoin(page_url, seo["image"]) if seo.get("image") else ""
    if image:
        head.append(f'  <meta property="og:image" content="{e(image)}">')
        if seo.get("image_width") and seo.get("image_height"):
            head.append(f'  <meta property="og:image:width" content="{int(seo["image_width"])}">')
            head.append(f'  <meta property="og:image:height" content="{int(seo["image_height"])}">')
        if seo.get("image_alt"):
            head.append(f'  <meta property="og:image:alt" content="{e(seo["image_alt"])}">')
    head.append(f'  <meta name="twitter:card" content="{"summary_large_image" if image else "summary"}">')
    if seo.get("twitter_site"):
        head.append(f'  <meta name="twitter:site" content="{e(seo["twitter_site"])}">')
    head += [
        f'  <meta name="twitter:title" content="{e(s_title)}">',
        f'  <meta name="twitter:description" content="{e(s_desc)}">',
    ]
    if image:
        head.append(f'  <meta name="twitter:image" content="{e(image)}">')
        if seo.get("image_alt"):
            head.append(f'  <meta name="twitter:image:alt" content="{e(seo["image_alt"])}">')
    head.append('  <script type="application/ld+json">')
    head.append(json_ld(cfg, page_url))
    head.append("  </script>")
    css = CSS
    if hero.get("background_image"):
        # Decorative only, so it lives in CSS rather than an <img> needing alt text.
        bg = hero["background_image"].replace('"', "%22").replace(")", "%29")
        css = css.replace("var(--hero-image, none)", f'url("{bg}")')
    head.append(f"  <style>\n{css}  </style>")
    head.append("</head>")

    body = ["<body>", '  <a class="skip" href="#main">Skip to content</a>',
            '  <header class="hero">', '    <div class="inner">']
    if hero.get("eyebrow"):
        body.append(f'      <p class="eyebrow">{e(hero["eyebrow"])}</p>')
    body.append(f'      <h1>{e(hero["heading"])}</h1>')
    if hero.get("lead"):
        body.append(f'      <p class="lead">{e(hero["lead"])}</p>')
    body.append(render_actions(hero.get("actions"), 6).rstrip("\n"))
    body += ["    </div>", "  </header>", "", '  <main id="main" tabindex="-1">']
    body.append("\n".join(render_section(s, cfg).rstrip("\n") for s in sections))
    body.append("  </main>")
    if cfg.get("footer"):
        body.append("")
        body.append("  <footer>")
        for f in cfg["footer"]:
            if f.get("url"):
                body.append(f'    <p>{e(f["text"])} <a href="{e(f["url"])}">{e(f.get("label") or f["url"])}</a></p>')
            else:
                body.append(f'    <p>{e(f["text"])}</p>')
        body.append("  </footer>")
    body += ["</body>", "</html>", ""]
    return "\n".join(head) + "\n" + "\n".join(body)


def render_sitemap(cfg):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f'  <url><loc>{e(cfg["site"]["url"])}</loc></url>\n'
            "</urlset>\n")


def outputs(cfg, sitemap=True):
    files = {"index.html": render_page(cfg)}
    if sitemap:
        files["sitemap.xml"] = render_sitemap(cfg)
        if urlparse(cfg["site"]["url"]).path == "/":
            files["robots.txt"] = f"User-agent: *\nAllow: /\n\nSitemap: {cfg['site']['url']}sitemap.xml\n"
    return files


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default=str(ROOT / "storefront.json"))
    ap.add_argument("--out", default=str(ROOT / "docs"))
    ap.add_argument("--no-sitemap", action="store_true", help="only write index.html")
    ap.add_argument("--check", action="store_true", help="exit 1 if the output files are stale")
    args = ap.parse_args(argv)

    try:
        cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
        validate(cfg)
    except (OSError, json.JSONDecodeError, ContentError) as err:
        print(f"build: {args.config}: {err}", file=sys.stderr)
        return 2

    out = Path(args.out)
    stale = []
    for name, text in outputs(cfg, sitemap=not args.no_sitemap).items():
        path = out / name
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == text:
            continue
        if args.check:
            stale.append(str(path))
        else:
            out.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            print(f"build: wrote {path}")
    if stale:
        print("build: out of date (run python3 scripts/build.py): " + ", ".join(stale), file=sys.stderr)
        return 1
    if args.check:
        print("build: output is up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
