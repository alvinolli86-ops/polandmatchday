# Poland Matchday (v0.1)

English-language guide to football in Poland for visitors & expats. Plain HTML + Python build script.

## Preview locally
    python3 scripts/fetch_fixtures.py     # refresh fixtures (~80 s)
    python3 scripts/build.py              # writes ./site (~650 pages)
    # Internal links use base_path from config.json (/polandmatchday/).
    mkdir -p /tmp/pm-preview && ln -sfn "$(pwd)/site" /tmp/pm-preview/polandmatchday
    python3 -m http.server 8080 --directory /tmp/pm-preview   # open http://localhost:8080/polandmatchday/

## Layout
- `data/clubs.json` – 18 Ekstraklasa clubs: official ticket site, passport rule + evidence + source URL + date checked. Hand-maintained, official sources only.
- `data/pubs.json` – sports bars, verified from their own websites; unknown fields = "unverified".
- `data/fixtures_ekstraklasa.json` – scraped from official ekstraklasa.org fixture pages (no key).
- `data/fixtures_1liga.json` – TheSportsDB free test key "123" (community data, times in UTC → converted).
- `config.json` – `base_url` (canonical tags and sitemap) and `base_path` (internal links and assets). Live site: https://alvinolli86-ops.github.io/polandmatchday. Affiliate IDs are placeholders: GYG_PARTNER_ID_PLACEHOLDER, BOOKING_AID_PLACEHOLDER.
- `.github/workflows/refresh-and-deploy.yml` – twice-daily fixture refresh plus GitHub Pages deploy on push to `main`. Pages source must be GitHub Actions.

## Known gaps
- Stands to avoid, transport notes and prices are only filled where a source was found; everything else says "not yet verified".
- The “get featured” form is a front-end placeholder; nothing is sent. Newsletter signup sends the visitor to the beehiiv subscribe page (`newsletter.publication_url` in `config.json`).
