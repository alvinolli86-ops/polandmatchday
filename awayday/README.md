# Away Day from Poland

The site home page is built from `data/trips.json` by `scripts/build.py` at the repo root. `./run_all.sh` refreshes the data. It always exits 0. Set `TRAVELPAYOUTS_TOKEN` to refresh fares; without it the last committed `data/fares.json` is kept. `raw/ourairports.csv` is downloaded when missing and is gitignored.

Flight links are Aviasales search URLs with `marker=` from `config.json` (`affiliates.travelpayouts_marker`). The API token is read from the environment and never written to disk.

| Step | Script | Output | Source | Licence/ToS |
|---|---|---|---|---|
| Fixtures | scripts/fetch_fixtures.py | data/fixtures.json | TheSportsDB v1, free test key `123` (eventsnextleague + eventsround) | Free "test" key, roughly 30 req/min. A production/commercial key is Premium at $9/month. |
| Kickoff cross-check | same (`--recheck`) | crosscheck field | openfootball/football.json 2026-27 (EN1, EN2, ES1, IT1, DE1, FR1, NL1, PT1) | CC0 / public domain |
| Stadium coords | scripts/fetch_clubs_wikidata.py | raw/wikidata_clubs.json | Wikidata SPARQL (club P118 league, P115 venue, P625 coords) | CC0 |
| Airports | (csv) | raw/ourairports.csv | OurAirports | Public domain |
| Club→airports | scripts/build_club_airports.py | data/clubs_airports.json | Wikidata + OurAirports, straight-line km; 8 clubs hand-compiled in data/manual_clubs.json | — |
| Direct routes | scripts/fetch_routes.py | data/routes_from_poland.json | English Wikipedia "Airlines and destinations" for 12 PL airports, links→IATA via OurAirports/Wikidata | CC BY-SA 4.0, attribution required |
| Fares | scripts/fares.py | per leg | Travelpayouts Aviasales Data API v3 `prices_for_dates` (cached, last ~48h) | Needs a free token. No token means "pending". |
| Join + HTML | scripts/build_preview.py | data/trips.json, preview/ | — | — |

## Known limits
- TheSportsDB free key: `eventsnextleague` returns only 1 event and `eventsseason` only 15, so we walk round by round. Its data is community-edited.
- The Wednesday 28 Oct Serie A round is dropped from the weekend view.
- One Scottish match is flagged postponed.
- openfootball has no Scotland/Austria/Czech/Belgium/Swiss/Danish/2.BL. La Liga has nominal dates only (no kickoff times). There is 1 real conflict (Alverca v Arouca: 15:30 vs 18:00).
- OpenFlights routes.dat was tested but not used, because it's from 2014. Wikipedia is current-ish, but community-edited. "begins/ends/resumes" notes are parsed per airline. "Seasonal" is ambiguous (summer or winter) and is flagged.
- Wikidata sometimes lists a club's former ground (e.g. Brentford/Griffin Park). The distances are still fine for choosing an airport.
- Clubs are mapped only if they have a home game in the window: 233 of them now. Re-running the script picks up the rest over time.

## Fares (added 20 Oct, token set)
- `scripts/fetch_fares.py` queries `prices_for_dates` for every leg: (origin, dest, out = D-1 and D, back = D+1), with direct=true, market=pl and currency=pln. It runs at 6 req/s; the response header says the limit is 600 requests a minute. Results go to `data/fares.json`. The token is read from the environment and never written to disk.
- Results are filtered to the exact airport pair, nonstop both ways, and the exact dates. Dates are taken from the Aviasales link path, because the API mixes local time and Z timestamps.
- A match-day outbound flight only counts if it lands 3h or more before kickoff (departure_at + duration_to).
- The API returns only the search date, not hours ("search_date" in the link). That's why freshness is shown in days.
- The returned links carry no affiliate marker. They are plain aviasales.com links.
