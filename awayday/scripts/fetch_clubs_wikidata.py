"""Clubs + home stadium coordinates from Wikidata (CC0) via SPARQL."""
import json, urllib.parse, urllib.request, os
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEAGUES = {"Q9448":"EPL","Q19510":"Championship","Q82595":"Bundesliga","Q152665":"2. Bundesliga","Q15804":"Serie A",
  "Q13394":"Ligue 1","Q324867":"La Liga","Q167541":"Eredivisie","Q182994":"Primeira Liga","Q14377162":"Scottish Premiership",
  "Q219592":"Austrian Bundesliga","Q217016":"Czech First League","Q216022":"Belgian Pro League","Q202699":"Swiss Super League","Q204752":"Danish Superliga"}
q = """SELECT ?club ?clubLabel (GROUP_CONCAT(DISTINCT ?alias; separator="|") AS ?aliases) ?venueLabel ?coord ?cityLabel ?league WHERE {
 VALUES ?league { %s }
 ?club wdt:P118 ?league; wdt:P31/wdt:P279* wd:Q476028 .
 ?club wdt:P115 ?venue . ?venue wdt:P625 ?coord .
 OPTIONAL { ?venue wdt:P131 ?city . }
 OPTIONAL { ?club skos:altLabel ?alias FILTER(lang(?alias)="en") }
 FILTER NOT EXISTS { ?club wdt:P576 ?dissolved }
 SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
} GROUP BY ?club ?clubLabel ?venueLabel ?coord ?cityLabel ?league""" % " ".join("wd:"+k for k in LEAGUES)
req = urllib.request.Request("https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": q, "format": "json"}),
                             headers={"User-Agent": "AwayDayPrototype/0.1 (research)", "Accept": "application/sparql-results+json"})
rows = json.load(urllib.request.urlopen(req, timeout=120))["results"]["bindings"]
clubs = {}
for r in rows:
    qid = r["club"]["value"].rsplit("/",1)[1]
    lon, lat = map(float, r["coord"]["value"][6:-1].split())
    c = clubs.setdefault(qid, {"qid": qid, "name": r["clubLabel"]["value"], "aliases": [a for a in r.get("aliases",{}).get("value","").split("|") if a],
                               "venues": [], "leagues": set()})
    c["leagues"].add(LEAGUES[r["league"]["value"].rsplit("/",1)[1]])
    v = {"name": r["venueLabel"]["value"], "lat": lat, "lon": lon, "admin": r.get("cityLabel",{}).get("value")}
    if v not in c["venues"]: c["venues"].append(v)
for c in clubs.values(): c["leagues"] = sorted(c["leagues"])
json.dump(sorted(clubs.values(), key=lambda c: c["name"]), open(f"{BASE}/raw/wikidata_clubs.json","w"), ensure_ascii=False, indent=1)
print(len(rows), "rows,", len(clubs), "clubs")
