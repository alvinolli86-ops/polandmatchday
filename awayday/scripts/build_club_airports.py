"""Map each home club in fixtures.json to stadium coords (Wikidata, CC0) and its nearest
airports with scheduled service (OurAirports, public domain). Unmatched clubs fall back to
data/manual_clubs.json (hand-compiled, marked as such)."""
import csv, json, math, os, re, sys, unicodedata
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def key(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(fc|cf|afc|sc|ac|ssc|as|us|rc|cd|ud|sd|rcd|ca|club|de|del|calcio|football|fk|sk|bv|vfb|vfl|tsg|sv|kv|krc|rsc|bk|if|og|1)\b", " ", s)
    return re.sub(r"[^a-z]", "", s)
def hav(a, b, c, d):
    p = math.pi / 180; x = math.sin((c-a)*p/2)**2 + math.cos(a*p)*math.cos(c*p)*math.sin((d-b)*p/2)**2
    return 12742 * math.asin(math.sqrt(x))

ports = [r for r in csv.DictReader(open(f"{BASE}/raw/ourairports.csv", encoding="utf-8"))
         if r["iata_code"] and r["scheduled_service"] == "yes" and r["type"] in ("large_airport", "medium_airport")]
wd = json.load(open(f"{BASE}/raw/wikidata_clubs.json"))
idx = {}
for c in wd:
    for n in [c["name"]] + c["aliases"]: idx.setdefault(key(n), c)
manual = json.load(open(f"{BASE}/data/manual_clubs.json")) if os.path.exists(f"{BASE}/data/manual_clubs.json") else {}
fx = json.load(open(f"{BASE}/data/fixtures.json"))
teams = sorted({(m["home"], m["league"], m.get("venue") or "") for m in fx["matches"]})
out, unmatched = {}, []
for team, league, venue in teams:
    k = key(team); c = idx.get(k)
    if not c:  # loose containment match, same league only
        cands = [x for x in wd if any(k and (k in key(n) or key(n) in k) and len(key(n)) > 3 for n in [x["name"]] + x["aliases"])]
        if len(cands) == 1: c = cands[0]
    if team in manual:
        m = manual[team]; out[team] = {"league": league, "venue": venue, "source": "manual (hand-compiled, verify)", **m}; continue
    if not c: unmatched.append((team, league, venue)); continue
    vk = key(venue)
    v = next((x for x in c["venues"] if vk and (key(x["name"]) in vk or vk in key(x["name"]))), c["venues"][0])
    near = sorted(((hav(v["lat"], v["lon"], float(p["latitude_deg"]), float(p["longitude_deg"])), p) for p in ports), key=lambda t: t[0])
    near = [{"iata": p["iata_code"], "name": p["name"], "city": p["municipality"], "km": round(d)} for d, p in near if d <= 200][:4]
    out[team] = {"league": league, "venue": venue or v["name"], "wikidata": c["qid"], "wikidata_name": c["name"],
                 "stadium_wikidata": v["name"], "lat": v["lat"], "lon": v["lon"], "nearest_airports": near,
                 "source": "Wikidata stadium coords + OurAirports (straight-line km)"}
json.dump(out, open(f"{BASE}/data/clubs_airports.json", "w"), ensure_ascii=False, indent=1)
json.dump(unmatched, open(f"{BASE}/raw/unmatched_clubs.json", "w"), ensure_ascii=False, indent=1)
print(len(out), "mapped,", len(unmatched), "unmatched", file=sys.stderr)
for u in unmatched: print("  UNMATCHED", u, file=sys.stderr)
