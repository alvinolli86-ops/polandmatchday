#!/usr/bin/env bash
# Full Away Day pipeline. Always exits 0: a missing TRAVELPAYOUTS_TOKEN or a
# failed fetch must not stop the site build. Scripts write JSON only at the
# end, so a crash leaves the last committed file in place.
cd "$(dirname "$0")"
mkdir -p raw
if [ ! -s raw/ourairports.csv ]; then
  curl -fsSL -o raw/ourairports.csv https://davidmegginson.github.io/ourairports-data/airports.csv \
    || echo "ourairports download failed; keeping the last committed routes and airports"
fi
python3 scripts/fetch_routes.py || echo "fetch_routes failed; keeping last routes"
python3 scripts/fetch_clubs_wikidata.py || echo "wikidata fetch failed; keeping last club list"
python3 scripts/fetch_fixtures.py || echo "fixture fetch failed; keeping last fixtures"
python3 scripts/build_club_airports.py || echo "club-airport build failed; keeping last mapping"
python3 scripts/build_preview.py || echo "trip join failed; keeping last trips.json"
if [ -n "${TRAVELPAYOUTS_TOKEN:-}" ]; then
  python3 scripts/fetch_fares.py && python3 scripts/build_preview.py \
    || echo "fare fetch failed; keeping last fares.json"
else
  echo "TRAVELPAYOUTS_TOKEN is not set; using the last committed data/fares.json"
fi
exit 0
