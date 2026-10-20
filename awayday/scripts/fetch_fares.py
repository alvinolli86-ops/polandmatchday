"""Query cached fares for every Polish-airport -> stadium-airport leg in trips.json.
Outbound: day before match AND match day; return: day after. Results -> data/fares.json."""
import json, os, sys, datetime as dt
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fares import get_provider
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
prov = get_provider()
if prov.name != "travelpayouts": sys.exit("TRAVELPAYOUTS_TOKEN not set")
trips = json.load(open(f"{BASE}/data/trips.json"))
qs = set()
for t in trips["trips"] + trips["unreachable"]:
    d = dt.date.fromisoformat(t["date_local"])
    for l in t["legs"]:
        for dep in (d - dt.timedelta(days=1), d):
            qs.add((l["origin"], l["dest"], str(dep), str(d + dt.timedelta(days=1))))
qs = sorted(qs); print(len(qs), "queries", file=sys.stderr)
def run(q): return q, prov.quote(*q)
with ThreadPoolExecutor(4) as ex: res = list(ex.map(run, qs))
out = {"fetched": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "provider": "Travelpayouts Aviasales Data API v3 prices_for_dates (market=pl, currency=pln, direct only)",
       "quotes": {"|".join(q): r for q, r in res}}
json.dump(out, open(f"{BASE}/data/fares.json", "w"), ensure_ascii=False, indent=1)
from collections import Counter
print(Counter(r["status"] for _, r in res), file=sys.stderr)
