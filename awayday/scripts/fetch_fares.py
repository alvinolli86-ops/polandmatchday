"""Query cached fares for every Polish-airport -> stadium-airport leg in trips.json.

Preferred trip: out on the day before the match or on match day, back the next day.
If every exact-date query is empty, ask again by month and keep a direct fare
within one day of that trip. The token is never written to disk.
"""
import json, os, sys, datetime as dt
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fares import get_provider
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
prov = get_provider()
if prov.name != "travelpayouts":
    sys.exit("TRAVELPAYOUTS_TOKEN not set")
trips = json.load(open(f"{BASE}/data/trips.json"))

exact = set()
months_for = {}
for t in trips["trips"] + (trips.get("unreachable") or []):
    d = dt.date.fromisoformat(t["date_local"])
    months = set()
    for od in (-2, -1, 0):
        out = d + dt.timedelta(days=od)
        for rd in (1, 2):
            ret = d + dt.timedelta(days=rd)
            months.add((out.strftime("%Y-%m"), ret.strftime("%Y-%m")))
    for l in t["legs"]:
        key = (l["origin"], l["dest"])
        months_for.setdefault(key, set()).update(months)
        for dep in (d - dt.timedelta(days=1), d):
            exact.add((l["origin"], l["dest"], str(dep), str(d + dt.timedelta(days=1))))

exact = sorted(exact)
print(len(exact), "exact-date queries", file=sys.stderr)

def run_exact(q):
    return q, prov.quote(*q)

with ThreadPoolExecutor(4) as ex:
    exact_res = list(ex.map(run_exact, exact))
quotes = {}
for q, r in exact_res:
    if r.get("status") == "cached":
        quotes["|".join(q)] = {**r, "out_date": q[2], "ret_date": q[3]}
print("exact", Counter(r["status"] for _, r in exact_res), file=sys.stderr)

if not quotes:
    print("exact dates were empty; widening to month ranges, ±1 day", file=sys.stderr)
    jobs = [(od, sorted(months)) for od, months in months_for.items()]
    print(len(jobs), "origin-destination pairs", file=sys.stderr)

    def run_month(item):
        (origin, dest), months = item
        offers = []
        for dep_m, ret_m in months:
            offers.extend(prov.month_offers(origin, dest, dep_m, ret_m))
        return origin, dest, offers

    with ThreadPoolExecutor(4) as ex:
        for origin, dest, offers in ex.map(run_month, jobs):
            for o in offers:
                k = f"{origin}|{dest}|{o['out_date']}|{o['ret_date']}"
                prev = quotes.get(k)
                if prev is None or o["price"] < prev["price"]:
                    quotes[k] = o
    print(len(quotes), "fares kept after the wider search", file=sys.stderr)

out = {
    "fetched": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    "provider": "Travelpayouts Aviasales Data API v3 prices_for_dates (market=pl, currency=pln, direct only; month range if exact dates are empty)",
    "quotes": quotes,
}
path = f"{BASE}/data/fares.json"
tmp = path + ".tmp"
json.dump(out, open(tmp, "w"), ensure_ascii=False, indent=1)
os.replace(tmp, path)
print(Counter(r["status"] for r in quotes.values()), "stored", len(quotes), file=sys.stderr)
