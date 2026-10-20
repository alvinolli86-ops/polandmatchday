"""Join fixtures x stadium airports x direct routes from Poland x cached fares (data/fares.json,
written by fetch_fares.py) -> data/trips.json + preview/index.html. Never calls the fare API itself."""
import json, os, re, html, sys, urllib.request, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fares import search_link, with_marker
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_KM = 100            # straight-line stadium -> airport limit
MATCHDAY_BUFFER_H = 3   # match-day outbound must land >= 3h before kickoff
PL_NAMES = {"WAW":"Warsaw Chopin","WMI":"Warsaw Modlin","KRK":"Kraków","KTW":"Katowice","GDN":"Gdańsk","WRO":"Wrocław",
            "POZ":"Poznań","LCJ":"Łódź","RZE":"Rzeszów","SZZ":"Szczecin","LUZ":"Lublin","BZG":"Bydgoszcz"}
AIRLINES = {"FR":"Ryanair","RK":"Ryanair UK","W6":"Wizz Air","W4":"Wizz Air Malta","W9":"Wizz Air UK","LO":"LOT","U2":"easyJet",
            "EC":"easyJet Europe","LS":"Jet2","EW":"Eurowings","LH":"Lufthansa","SK":"SAS","KL":"KLM","AF":"Air France","BA":"British Airways",
            "VY":"Vueling","IB":"Iberia","AZ":"ITA Airways","TP":"TAP","OS":"Austrian","LX":"Swiss","SN":"Brussels Airlines","DY":"Norwegian",
            "D8":"Norwegian","NO":"Neos","HV":"Transavia","TO":"Transavia France","V7":"Volotea","EN":"Air Dolomiti","ENT":"Enter Air","E4":"Enter Air"}
TIER = {"Premier League":0,"La Liga":0,"Serie A":0,"Bundesliga":0,"Ligue 1":0,"Eredivisie":1,"Primeira Liga":1,
        "Scottish Premiership":1,"Austrian Bundesliga":2,"Czech First League":2,"Belgian Pro League":2,"Championship":2,
        "Swiss Super League":3,"Danish Superliga":3,"2. Bundesliga":3}
MONTHS = {m: i for i, m in enumerate(["january","february","march","april","may","june","july","august","september","october","november","december"], 1)}
TOP_N = 15

def clean(a): return re.sub(r"\s*\([^)]*airline[^)]*\)", "", a)
def parse_date(s):
    m = re.search(r"(\d{1,2}) (\w+) (\d{4})", s)
    return dt.date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1))) if m and m.group(2).lower() in MONTHS else None

def active_airlines(dest, dep, ret):
    ok = []
    for al in dest["airlines"]:
        good = True
        for n in [n for n in dest["notes"] if n.startswith(al + " ")]:
            d = parse_date(n)
            if not d: continue
            if re.search(r"\((begins|resumes)", n) and d > dep: good = False
            if re.search(r"\(ends", n) and d < ret: good = False
        if good: ok.append(al)
    return ok

def ecb_pln_per_eur():
    try:
        x = urllib.request.urlopen("https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml", timeout=15).read().decode()
        return float(re.search(r"currency='PLN' rate='([\d.]+)'", x).group(1)), re.search(r"time='([\d-]+)'", x).group(1)
    except Exception:
        return None, None

def feasible_matchday(q, kickoff_utc):
    """Match-day outbound only counts if it lands MATCHDAY_BUFFER_H before kickoff (needs departure time + duration)."""
    if not q.get("departure_at") or not q.get("duration_to"): return False
    arr = dt.datetime.fromisoformat(q["departure_at"].replace("Z", "+00:00")) + dt.timedelta(minutes=q["duration_to"])
    return arr <= dt.datetime.fromisoformat(kickoff_utc) - dt.timedelta(hours=MATCHDAY_BUFFER_H)

def main():
    fx = json.load(open(f"{BASE}/data/fixtures.json"))
    clubs = json.load(open(f"{BASE}/data/clubs_airports.json"))
    routes = json.load(open(f"{BASE}/data/routes_from_poland.json"))["airports"]
    fpath = f"{BASE}/data/fares.json"
    fares = json.load(open(fpath)) if os.path.exists(fpath) else {"quotes": {}, "fetched": None}
    Q = fares["quotes"]
    trips, unreachable, unmapped = [], [], []
    for m in fx["matches"]:
        wk = next((i for i, (a, b) in enumerate(fx["weekends"]) if a <= m["date_local"] <= b), None)
        if wk is None: continue
        c = clubs.get(m["home"])
        if not c: unmapped.append(m); continue
        d = dt.date.fromisoformat(m["date_local"]); ret = d + dt.timedelta(days=1)
        legs = []
        for ap in c["nearest_airports"]:
            if ap["km"] > MAX_KM: continue
            for o, r in routes.items():
                dest = r["destinations"].get(ap["iata"])
                if not dest or dest.get("charter_only"): continue
                als = active_airlines(dest, d - dt.timedelta(days=1), ret)
                if not als: continue
                opts = []
                for dep, kind in ((d - dt.timedelta(days=1), "day before"), (d, "match day")):
                    q = Q.get(f"{o}|{ap['iata']}|{dep}|{ret}")
                    if not q or q.get("status") != "cached": continue
                    if kind == "match day" and not feasible_matchday(q, m["kickoff_utc"]): continue
                    opts.append({**q, "out_date": str(dep), "ret_date": str(ret), "out_kind": kind})
                best = min(opts, key=lambda q: q["price"]) if opts else None
                legs.append({"origin": o, "dest": ap["iata"], "dest_name": ap["name"], "km_to_stadium": ap["km"],
                             "airlines": [clean(a) for a in als], "seasonal_flag": dest["seasonal_only"], "fare": best,
                             "checked": any(f"{o}|{ap['iata']}|{dep}|{ret}" in Q for dep in (d - dt.timedelta(days=1), d)),
                             "check_link": search_link(o, ap["iata"], str(d - dt.timedelta(days=1)), str(ret))})
        rec = {**m, "weekend": wk, "legs": legs}
        priced = [l for l in legs if l["fare"]]
        rec["cheapest"] = min(priced, key=lambda l: l["fare"]["price"]) if priced else None
        (trips if legs else unreachable).append(rec)
    rate, rate_date = ecb_pln_per_eur()
    out = {"generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "fares_fetched": fares.get("fetched"),
           "ecb_pln_per_eur": rate, "ecb_date": rate_date, "weekends": fx["weekends"],
           "trips": trips, "unreachable": unreachable, "unmapped": unmapped}
    json.dump(out, open(f"{BASE}/data/trips.json", "w"), ensure_ascii=False, indent=1)
    render(out)
    print(len(trips), "reachable,", sum(1 for t in trips if t["cheapest"]), "with a cached fare,", len(unreachable), "no direct route", file=sys.stderr)

E = html.escape
def fmt(s): return dt.date.fromisoformat(s[:10]).strftime("%a %d %b")
from zoneinfo import ZoneInfo
def hhmm(s):
    """Flight time converted to Polish time (API mixes local offsets and Z)."""
    if not s or len(s) < 16: return ""
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Warsaw")).strftime("%H:%M")
def al_name(code): return AIRLINES.get(code or "", code or "?")

def badge(m):
    cc = m.get("crosscheck")
    if m["flags"]: return '<span class="b warn">' + E("; ".join(m["flags"])) + "</span>"
    if cc == "agrees (date+time)": return '<span class="b ok">kickoff confirmed by 2 sources</span>'
    if cc and cc.startswith("CONFLICT"): return '<span class="b warn">sources disagree: ' + E(cc[10:]) + "</span>"
    return '<span class="b mid">kickoff from 1 source – verify</span>'

def found_text(q, now):
    if not q.get("found_on"): return "found: date unknown"
    days = (now.date() - dt.date.fromisoformat(q["found_on"])).days
    ago = "today" if days <= 0 else ("yesterday" if days == 1 else f"{days} days ago")
    return f"price found {ago} ({fmt(q['found_on'])})"

def price_html(q, rate):
    eur = f' <span class="eur">≈ €{q["price"]/rate:.0f}</span>' if rate and q["currency"] == "PLN" else ""
    return f'<b>{q["price"]} zł</b>{eur}'

def leg_href(leg, trip):
    """Aviasales link for this leg, with the partner marker. Fare links from the API are preferred."""
    q = leg.get("fare") or {}
    if q.get("link"):
        return with_marker(q["link"])
    d = dt.date.fromisoformat(trip["date_local"])
    return search_link(leg["origin"], leg["dest"], str(d - dt.timedelta(days=1)), str(d + dt.timedelta(days=1)))

def pick_top(ts):
    """Cheapest trips, at most two rows into the same destination airport."""
    ranked = sorted((t for t in ts if t["cheapest"]), key=lambda t: (t["cheapest"]["fare"]["price"], t["kickoff_utc"]))
    picked, seen = [], {}
    for t in ranked:
        dest = t["cheapest"]["dest"]
        if seen.get(dest, 0) >= 2:
            continue
        picked.append(t)
        seen[dest] = seen.get(dest, 0) + 1
        if len(picked) >= TOP_N:
            break
    return picked

def inner_html(out):
    """Filter plus one Top 15 and full list per weekend. No page chrome."""
    now = dt.datetime.now(dt.timezone.utc); rate = out["ecb_pln_per_eur"]
    secs = []
    for wi, (a, b) in enumerate(out["weekends"]):
        ts = [t for t in out["trips"] if t["weekend"] == wi]
        top = pick_top(ts)
        rows = ""
        for n, t in enumerate(top, 1):
            l = t["cheapest"]; q = l["fare"]
            href = leg_href(l, t)
            rows += (f'<tr><td class="n">{n}</td><td class="p"><a href="{E(href)}" target="_blank" rel="sponsored nofollow noopener">{price_html(q, rate)}</a>'
                     f'<div class="sm">return, per person</div></td>'
                     f'<td><b>{l["origin"]} → {l["dest"]}</b><div class="sm">{E(PL_NAMES[l["origin"]])} · {E(al_name(q.get("airline")))}</div></td>'
                     f'<td>out {fmt(q["out_date"])} {hhmm(q.get("departure_at"))}<div class="sm">back {fmt(q["ret_date"])} {hhmm(q.get("return_at"))} · times in Polish time{"<br><b>flies out on match day</b>" if q["out_kind"]=="match day" else ""}</div></td>'
                     f'<td><b>{E(t["home"])} v {E(t["away"])}</b><div class="sm">{E(t["league"])} · {l["km_to_stadium"]} km from airport</div></td>'
                     f'<td>{E(t["kickoff_pl"])}<div class="sm">Polish time</div>{badge(t)}</td>'
                     f'<td class="sm">{E(found_text(q, now))}</td></tr>')
        cap = f'<p class="sm">Top {len(top)} of the cheapest trips. At most two rows fly into the same airport, so one destination does not fill the list.</p>' if top else ""
        top_html = (f'{cap}<table class="top"><thead><tr><th>#</th><th>Return fare</th><th>Flight</th><th>Dates</th><th>Match</th><th>Kickoff</th><th>Freshness</th></tr></thead>{rows}</table>'
                    if top else '<p>No cached fares found for this weekend yet.</p>')
        cards = []
        for t in sorted(ts, key=lambda t: (t["cheapest"]["fare"]["price"] if t["cheapest"] else 10**9, TIER.get(t["league"], 9), t["kickoff_utc"])):
            origins = sorted({l["origin"] for l in t["legs"]})
            lr = ""
            for l in sorted(t["legs"], key=lambda l: (l["fare"]["price"] if l["fare"] else 10**9, l["origin"])):
                href = leg_href(l, t)
                f = (f'<a href="{E(href)}" target="_blank" rel="sponsored nofollow noopener">{price_html(l["fare"], rate)}</a> <span class="sm">{E(al_name(l["fare"].get("airline")))}, out {fmt(l["fare"]["out_date"])}</span>'
                     if l["fare"] else f'<span class="nf">no recent fare</span> <a class="sm" href="{E(href)}" target="_blank" rel="sponsored nofollow noopener">search on Aviasales</a>')
                lr += (f'<tr data-o="{l["origin"]}"><td><b>{l["origin"]}</b> → <b>{l["dest"]}</b> <span class="sm">{l["km_to_stadium"]} km</span></td>'
                       f'<td class="sm">{E(", ".join(l["airlines"]))}{" (seasonal?)" if l["seasonal_flag"] else ""}</td><td>{f}</td></tr>')
            cards.append(f'<div class="card" data-origins="{" ".join(origins)}" data-priced="{1 if t["cheapest"] else 0}"><div class="lg">{E(t["league"])}</div>'
                         f'<h4>{E(t["home"])} v {E(t["away"])}</h4><p class="sm">{E(t["kickoff_pl"])} Polish time ({E(t["kickoff_local"])} local) {badge(t)}</p>'
                         f'<table>{lr}</table></div>')
        npriced = sum(1 for t in ts if t["cheapest"])
        secs.append(f'''<section><h2>Weekend {wi+1}: {fmt(a)} – {fmt(b)}</h2>
<h3>Top {min(TOP_N, len(top) or TOP_N)} cheapest football trips from Poland</h3>{top_html}
<details><summary>All {len(ts)} matches with a direct flight from Poland ({npriced} with a cached fare)</summary>{"".join(cards)}</details></section>''')
    opts = "".join(f'<option value="{k}">{k} – {E(v)}</option>' for k, v in PL_NAMES.items())
    return f'''<div class="filter"><label>Full lists, flying from: <select id="o"><option value="">Any Polish airport</option>{opts}</select></label>
<label style="margin-left:14px"><input type="checkbox" id="pr"> only matches with a fare</label></div>
{"".join(secs)}
<script>
function f(){{const v=document.getElementById("o").value,p=document.getElementById("pr").checked;
document.querySelectorAll("[data-origins]").forEach(c=>{{const show=(!v||c.dataset.origins.split(" ").includes(v))&&(!p||c.dataset.priced=="1");c.style.display=show?"":"none";
c.querySelectorAll("tr").forEach(r=>r.style.display=!v||r.dataset.o==v?"":"none")}});
if(v||p)document.querySelectorAll(".aday details, main details").forEach(d=>d.open=true)}}
document.getElementById("o").onchange=f;document.getElementById("pr").onchange=f;
</script>'''

def render(out):
    rate = out["ecb_pln_per_eur"]
    body = inner_html(out)
    eur_note = f"EUR is converted at the ECB rate of {rate} PLN/EUR ({out['ecb_date']})." if rate else "EUR conversion unavailable."
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Away Day from Poland – cheapest football weekends</title><style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#f4f5f7;color:#16202a}}
header{{background:#0b3d2e;color:#fff;padding:20px 24px}} header h1{{margin:0 0 4px;font-size:26px}} header p{{margin:0;opacity:.85}}
.proto{{background:#fff3cd;color:#664d03;padding:9px 24px;font-size:13px;border-bottom:1px solid #e6d28f}}
main{{max-width:1150px;margin:0 auto;padding:12px 16px}} h2{{font-size:21px;margin:26px 0 4px}} h3{{font-size:16px;margin:8px 0;color:#0b5a3a}}
table{{width:100%;border-collapse:collapse;font-size:13.5px}} td,th{{padding:6px 7px;border-top:1px solid #e6e9ec;vertical-align:top;text-align:left}}
table.top{{background:#fff;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.08)}} table.top th{{font-size:12px;color:#5a6772;font-weight:600;border-top:0}}
td.n{{color:#8a96a0;font-weight:600}} td.p a{{color:#0b6b3a;text-decoration:none;font-size:15px}} .eur{{color:#5a6772;font-size:12px;font-weight:400}}
.sm{{font-size:12px;color:#5a6772}} .nf{{color:#9aa4ad;font-size:12.5px}} a{{color:#0b6bcb}}
details{{margin:12px 0}} summary{{cursor:pointer;font-weight:600;padding:8px 0}}
.card{{background:#fff;border-radius:8px;padding:10px 14px;margin:8px 0;box-shadow:0 1px 2px rgba(0,0,0,.06)}} .card h4{{margin:2px 0;font-size:16px}}
.lg{{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#0b7a55;font-weight:600}}
.b{{display:inline-block;font-size:11px;padding:1px 7px;border-radius:9px;margin-top:2px;font-weight:500}} .ok{{background:#d1f2e0;color:#0b5a3a}} .mid{{background:#e8ecf0;color:#3d4a55}} .warn{{background:#fde2e1;color:#8a1c17}}
.filter{{margin:10px 0;font-size:14px}} select{{font-size:14px;padding:4px}}
footer{{max-width:1150px;margin:0 auto;padding:10px 16px 40px;font-size:12.5px;color:#5a6772}}
</style></head><body>
<header><h1>Away Day from Poland</h1><p>The cheapest football weekends abroad, with direct flights from Polish airports.</p></header>
<div class="proto"><b>Prototype.</b> Fares are <b>cached prices that Aviasales users found recently</b>. They are not live, so check the price before booking.
Return trips are direct both ways, flying out the day before (or on match day if you land 3h+ before kickoff) and back the day after. Base fares usually exclude a cabin bag. {E(eur_note)}
Routes come from Wikipedia and kickoffs from TheSportsDB, cross-checked against openfootball where available. Prices last updated {E(str(out.get("fares_fetched")))} UTC.</div>
<main>{body}</main>
<footer><p>{len(out["unreachable"])} more weekend matches have no direct route from Poland to an airport within {MAX_KM} km.</p>
<p>Fares: Travelpayouts / Aviasales Data API, fetched {E(str(out["fares_fetched"]))} UTC. Fixtures: TheSportsDB and openfootball/football.json (CC0). Stadiums: Wikidata (CC0). Airports: OurAirports (public domain).
Routes adapted from English Wikipedia "Airlines and destinations" sections by Wikipedia contributors, <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>. Generated {E(out["generated"])} UTC.</p></footer>
</body></html>'''
    os.makedirs(f"{BASE}/preview", exist_ok=True)
    open(f"{BASE}/preview/index.html", "w").write(page)

if __name__ == "__main__": main()
