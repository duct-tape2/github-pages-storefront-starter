# GitHub Pages Storefront Starter

Free sample repo for turning a small repo, checklist, deck, PDF, or digital download into a clearer GitHub Pages product page.

The GitHub template button is enabled, so you can create a private or public starter copy without forking history.

## Quickstart

You need a GitHub account and Python 3 (already installed on macOS, most Linux, and GitHub Codespaces). Nothing else to install.

1. **Copy the repo.** [Create a repo from this template](https://github.com/new?template_name=github-pages-storefront-starter&template_owner=duct-tape2), or fork it. Clone your copy.
2. **Edit one file: [`storefront.json`](storefront.json).** Set `site.url` to your page address (`https://YOUR-NAME.github.io/YOUR-REPO/`), then replace the title, description, hero, offers, sections, FAQ, and footer. [`examples/storefront.example.json`](examples/storefront.example.json) shows every supported field.
3. **Build and check.**
   ```bash
   python3 scripts/build.py        # writes docs/index.html and docs/sitemap.xml
   python3 scripts/check_site.py   # links, meta tags, JSON-LD, sitemap
   ```
   Fix anything marked `FAIL`, then commit `storefront.json` and `docs/` and push.
4. **Enable GitHub Pages.** In your repo: **Settings → Pages → Build and deployment → Deploy from a branch**, branch `main`, folder `/docs`, **Save**.
5. **Verify.** After the Pages deploy finishes (see the **Actions** tab), open your `site.url`. Paste it into the [free browser checker](https://duct-tape2.github.io/storefront-checker/) and a social preview tool to confirm the title, image, and price show up.

Pull requests run the same build check, site checker, and tests automatically ([`.github/workflows/site-check.yml`](.github/workflows/site-check.yml)).

Prefer no build step? Copy [examples/free-storefront-lite.html](examples/free-storefront-lite.html) to `docs/index.html` and edit it by hand, keeping the JSON-LD block in sync with the visible text.

More: [docs/CUSTOMIZING.md](docs/CUSTOMIZING.md) (field reference, images, custom domains, adding pages) · [CHECKLIST.md](CHECKLIST.md) · [CHANGELOG.md](CHANGELOG.md)

## Repo Layout

| Path | What it is |
| --- | --- |
| `storefront.json` | The one content file you edit. |
| `scripts/build.py` | Renders `docs/` from `storefront.json`. Python 3 stdlib only. `--check` fails if `docs/` is stale. |
| `scripts/check_site.py` | Checks internal links, required meta tags, JSON-LD, and sitemap coverage. Python 3 stdlib only. |
| `docs/` | The published GitHub Pages site (generated `index.html`, `sitemap.xml`, plus `assets/`). |
| `examples/` | Full-field example content and a hand-edit HTML version. |
| `tests/` | `python3 -m unittest discover -s tests` |

## Use The Free Sample

- Start with [CHECKLIST.md](CHECKLIST.md).
- [Create a repo from this template](https://github.com/new?template_name=github-pages-storefront-starter&template_owner=duct-tape2).
- Copy the small demo from [examples/free-storefront-lite.html](examples/free-storefront-lite.html).
- [View the live sample](https://duct-tape2.github.io/github-pages-storefront-starter/).
- [Read the free launch guide](https://duct-tape2.github.io/guides/github-pages-storefront/).
- [Download the free sample ZIP](https://github.com/duct-tape2/github-pages-storefront-starter/releases/download/v1.0-free-sample/github-pages-storefront-starter-free-sample.zip).
- [Run the free browser checker](https://duct-tape2.github.io/storefront-checker/).
- [Generate a static storefront page](https://duct-tape2.github.io/tools/static-storefront-builder/).
- [Read the public case study](https://duct-tape2.github.io/examples/storefront-starter-case-study/).

## Done For You

For `$99`, turn one existing GitHub repo into a buyer-ready product page with clear positioning, proof, scope, and inquiry paths.

- [Review the service scope](https://duct-tape2.github.io/repo-launch/).
- [View shipped work](https://duct-tape2.github.io/work/).
- [Read the case study](https://duct-tape2.github.io/examples/storefront-starter-case-study/).
- [Open the approved paid inquiry](https://github.com/duct-tape2/duct-tape2/issues/new?template=paid-inquiry.yml).
- [Email the listed service address](mailto:sks7178@gmail.com?subject=Buyer-ready%20repo%20page%20inquiry).

Available worldwide in English and priced in USD. Send only a public repo URL and the page outcome you want. Payment instructions are confirmed privately after scope is accepted. No revenue guarantees.

## Safe Scope

This repo and service are for normal digital products and small repo-based product pages.

Do not use them for security, vulnerability, exploit, bypass, jailbreak, spam, fake-review, credential, private-data, or personal-data scraping work.

## Public-Safe Support

- [Ask a public-safe question](https://github.com/duct-tape2/github-pages-storefront-starter/issues/new?template=question.yml).
- [Request public-safe storefront feedback](https://github.com/duct-tape2/github-pages-storefront-starter/issues/new?template=storefront-feedback.yml).

Do not post payment details, passwords, API keys, private files, customer data, analytics exports, or private URLs in public issues.

## License

[MIT](LICENSE)
