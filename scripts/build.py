#!/usr/bin/env python3
"""Build the static site into ./site from ./data. Usage: python3 scripts/build.py"""
import json, shutil, html, datetime as dt, re, sys
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import quote_plus, urlparse
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site"
sys.path.insert(0, str(ROOT / "awayday" / "scripts"))
from build_preview import inner_html, MAX_KM
WAW = ZoneInfo("Europe/Warsaw")
CFG = json.load(open(ROOT / "config.json"))

def normalize_base_path(cfg):
    """Origin path prefix for a project site, e.g. /polandmatchday/."""
    raw = cfg.get("base_path")
    if not raw:
        raw = urlparse(cfg.get("base_url") or "/").path or "/"
    raw = str(raw)
    if not raw.startswith("/"):
        raw = "/" + raw
    if not raw.endswith("/"):
        raw += "/"
    return raw

BASE = normalize_base_path(CFG)

def url(path=""):
    """Internal link/asset URL under base_path (works on GitHub Pages project sites)."""
    return BASE + str(path).lstrip("/")

def subscribe_url():
    """beehiiv public subscribe page. Its client reads ?email= and prefills the field."""
    return CFG["newsletter"]["publication_url"].rstrip("/") + "/subscribe"

def newsletter_form(input_id):
    action = subscribe_url()
    return f"""<form method='get' action='{E(action)}'>
<label for='{input_id}'>Email</label>
<input id='{input_id}' name='email' type='email' required autocomplete='email' placeholder='you@example.com'>
<p><button class='btn' type='submit'>Subscribe free</button></p>
</form>"""
CLUBS = json.load(open(ROOT / "data/clubs.json"))
PUBS = json.load(open(ROOT / "data/pubs.json"))
LIGA = json.load(open(ROOT / "data/liga1_tickets.json"))
EK = json.load(open(ROOT / "data/fixtures_ekstraklasa.json"))
L1 = json.load(open(ROOT / "data/fixtures_1liga.json"))
NOW = dt.datetime.now(WAW)
E = html.escape

CITIES = {
 "warsaw":   {"name":"Warsaw","pl":"Warszawa","ek":["Legia Warszawa"],"l1":["Polonia Warsaw"],"gyg":"Warsaw","bk":"Warsaw"},
 "krakow":   {"name":"Kraków","pl":"Kraków","ek":["Wisła Kraków","Cracovia","Wieczysta Kraków"],"l1":["Puszcza Niepołomice"],"gyg":"Krakow","bk":"Krakow"},
 "wroclaw":  {"name":"Wrocław","pl":"Wrocław","ek":["Śląsk Wrocław"],"l1":[],"gyg":"Wroclaw","bk":"Wroclaw"},
 "gdansk":   {"name":"Gdańsk & Tricity","pl":"Gdańsk / Gdynia","ek":[],"l1":["Lechia Gdańsk","Arka Gdynia"],"gyg":"Gdansk","bk":"Gdansk"},
 "poznan":   {"name":"Poznań","pl":"Poznań","ek":["Lech Poznań"],"l1":["Warta Poznań"],"gyg":"Poznan","bk":"Poznan"},
 "szczecin": {"name":"Szczecin","pl":"Szczecin","ek":["Pogoń Szczecin"],"l1":[],"gyg":"Szczecin","bk":"Szczecin"},
 "lodz":     {"name":"Łódź","pl":"Łódź","ek":["Widzew Łódź"],"l1":["ŁKS Łódź"],"gyg":"Lodz","bk":"Lodz"},
 "katowice": {"name":"Katowice & Silesia","pl":"Katowice / Zabrze / Gliwice / Chorzów / Bytom","ek":["GKS Katowice","Górnik Zabrze","Piast Gliwice"],"l1":["Ruch Chorzów","Polonia Bytom"],"gyg":"Katowice","bk":"Katowice"},
 "bialystok":{"name":"Białystok","pl":"Białystok","ek":["Jagiellonia Białystok"],"l1":[],"gyg":"Bialystok","bk":"Bialystok"},
 "lublin":   {"name":"Lublin","pl":"Lublin","ek":["Motor Lublin"],"l1":[],"gyg":"Lublin","bk":"Lublin"},
}
CITY_NOTE = {"krakow":"Puszcza Niepołomice play in Niepołomice, just outside Kraków."}
STATUS = {"yes":("Passport OK online","ok"),"accepted":("Passport accepted (online not explicit)","mid"),
          "unclear":("Unclear – contact club / box office","warn"),"unverified":("Unverified","warn")}

club_by_name = {c["name"]: c for c in CLUBS["clubs"]}
venues = defaultdict(Counter)
for m in EK["matches"]:
    if m["venue"]: venues[m["home"]][m["venue"]] += 1
for c in CLUBS["clubs"]:
    v = venues[c["name"]].most_common(1)
    c["venue"] = v[0][0] if v else None
    c["stadium"] = c["venue"].split(", ", 1)[1] if c["venue"] else "unverified"
    c["town"] = c["venue"].split(", ", 1)[0] if c["venue"] else ""

ALL = sorted(EK["matches"] + L1["matches"], key=lambda m: (m["kickoff"] or (m["date"] or "9999") + "T99"))

def mdt(m):
    if m["kickoff"]: return dt.datetime.fromisoformat(m["kickoff"]).astimezone(WAW)
    if m["date"]: return dt.datetime.fromisoformat(m["date"] + "T00:00").replace(tzinfo=WAW)
    return None

def fmt_time(m):
    d = mdt(m)
    if not d: return "Date TBC"
    day = d.strftime("%a %d %b")
    if m["kickoff"] and m["time_confirmed"]:
        return f"{day}, {d.strftime('%H:%M')} <abbr title='Polish time (Europe/Warsaw)'>{d.tzname()}</abbr>"
    return f"{day}, kickoff TBC"

def club_link(name, prefix=None):
    c = club_by_name.get(name)
    return f"<a href='{url('clubs/' + c['slug'] + '/')}'>{E(name)}</a>" if c else E(name)

def gyg(q): return f"https://www.getyourguide.com/s/?q={quote_plus(q)}&partner_id={CFG['affiliates']['getyourguide_partner_id']}"
def booking(q): return f"https://www.booking.com/searchresults.html?ss={quote_plus(q)}&aid={CFG['affiliates']['booking_aid']}"

def aff_box(city_q, prefix):
    return f"""<aside class='aff'><h3>Making a weekend of it?</h3>
<p><a rel='sponsored nofollow' href='{gyg(city_q)}'>Things to do in {E(city_q)} (GetYourGuide)</a> ·
<a rel='sponsored nofollow' href='{booking(city_q)}'>Hotels in {E(city_q)} (Booking.com)</a></p>
<p class='small'>Affiliate links (placeholders – not yet active). We may earn a commission at no extra cost to you.</p></aside>"""

CSS = """
:root{--pitch:#0b3d2e;--pitch2:#11553f;--line:#e8f5ee;--accent:#ffd23f;--ink:#14211b;--muted:#5d6b64;--ok:#1f8f4e;--mid:#b07d00;--warn:#b3412e;--card:#fff}
*{box-sizing:border-box}body{margin:0;font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:#f3f6f4}
a{color:#0d6b4a}header{background:var(--pitch);background-image:repeating-linear-gradient(90deg,var(--pitch) 0 40px,var(--pitch2) 40px 80px);color:#fff}
.wrap{max-width:960px;margin:0 auto;padding:0 16px}
.top{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 0;flex-wrap:wrap}
.logo{color:#fff;text-decoration:none;font-weight:800;font-size:1.25rem;letter-spacing:.3px}.logo span{color:var(--accent)}
nav a{color:var(--line);text-decoration:none;margin-right:14px;font-size:.95rem}nav a:hover{color:var(--accent)}
.hero{padding:20px 0 26px}.hero h1{margin:0 0 6px;font-size:1.7rem;line-height:1.2}.hero p{margin:0;color:var(--line)}
main{padding:20px 0 40px}h2{margin-top:28px;border-left:5px solid var(--accent);padding-left:10px}
.card{background:var(--card);border-radius:12px;padding:14px 16px;margin:10px 0;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.match{display:grid;grid-template-columns:1fr;gap:4px}.match .teams{font-weight:700;font-size:1.05rem}
.match .meta{color:var(--muted);font-size:.9rem}.tag{display:inline-block;font-size:.75rem;padding:2px 8px;border-radius:99px;background:#e6efe9;color:#24543f;margin-right:6px;font-weight:600}
.tag.l1{background:#eef0fb;color:#33407a}.badge{display:inline-block;padding:3px 10px;border-radius:99px;font-size:.8rem;font-weight:700;color:#fff}
.badge.ok{background:var(--ok)}.badge.mid{background:var(--mid)}.badge.warn{background:var(--warn)}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;font-size:.92rem}th,td{padding:8px 10px;border-bottom:1px solid #e5ebe7;text-align:left;vertical-align:top}th{background:#e8f0eb}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px}
.btn{display:inline-block;background:var(--accent);color:#1b1b1b;font-weight:700;padding:9px 16px;border-radius:8px;text-decoration:none;border:0;cursor:pointer;font-size:1rem}
.small{font-size:.82rem;color:var(--muted)}.aff{background:#fffbea;border:1px dashed #e7c84b;border-radius:12px;padding:10px 14px;margin:18px 0}.aff h3{margin:0 0 4px;font-size:1rem}
form label{display:block;margin:10px 0 4px;font-weight:600}form input,form textarea,form select{width:100%;padding:9px;border:1px solid #c9d6ce;border-radius:8px;font:inherit}
footer{background:#0a2a20;color:#b9cfc4;padding:20px 0;font-size:.85rem}footer a{color:#e8f5ee}
.empty{color:var(--muted);font-style:italic}.warnbox{background:#fff1ee;border-left:4px solid var(--warn);padding:8px 12px;border-radius:6px}
.wrap.wide{max-width:1150px}
.how{background:#fff3cd;color:#664d03;border-radius:12px;padding:12px 14px;margin:0 0 12px}
.how h2{border:0;padding:0;margin:0 0 6px;font-size:1.05rem;color:#664d03}
.aday h2{border-left:0;padding-left:0}
.aday h3{font-size:1.05rem;color:#0b5a3a;margin:8px 0}
.aday .sm{font-size:.78rem;color:var(--muted)}
.aday .eur{color:var(--muted);font-size:.78rem;font-weight:400}
.aday .nf{color:#9aa4ad;font-size:.82rem}
.aday .lg{font-size:.7rem;text-transform:uppercase;letter-spacing:.05em;color:#0b7a55;font-weight:600}
.aday td.n{color:#8a96a0;font-weight:600;width:2rem}
.aday td.p a{color:#0b6b3a;text-decoration:none;font-size:1.05rem}
.aday .b{display:inline-block;font-size:.7rem;padding:1px 7px;border-radius:9px;margin-top:2px;font-weight:600}
.aday .b.ok{background:#d1f2e0;color:#0b5a3a}.aday .b.mid{background:#e8ecf0;color:#3d4a55}.aday .b.warn{background:#fde2e1;color:#8a1c17}
.aday .filter{margin:8px 0}.aday .filter select,.aday .filter input{width:auto;font:inherit;padding:6px}
.aday ul.routes{margin:6px 0 0;padding-left:18px}.aday ul.routes li{margin:4px 0}
.aday ul.routes{margin:6px 0 0;padding-left:18px}.aday ul.routes li{margin:4px 0}
.aday .filter label{display:inline;font-weight:600}
@media(min-width:700px){.hero h1{font-size:2.1rem}.match{grid-template-columns:1.4fr 1fr auto;align-items:center}}
"""

def page(path, title, desc, body, prefix=None, wide=False, site_name=None, footer=None):
    nav = "".join(f"<a href='{url(h)}'>{t}</a>" for h, t in [("", "Away days"), ("matches-in-poland/", "Matches in Poland"), ("clubs/", "Clubs"), ("cities/", "Cities"), ("tickets-for-foreigners/", "Tickets for foreigners"), ("where-to-watch/", "Where to watch"), ("newsletter/", "Newsletter")])
    canon = CFG["base_url"].rstrip("/") + "/" + path
    site = site_name or CFG["site_name"]
    wrap = "wrap wide" if wide else "wrap"
    if footer is None:
        footer = f"""<p><a href="{url('about/')}">About</a> · <a href="{url('matches-in-poland/')}">Matches in Poland</a> · <a href="{url('get-featured/')}">Get your pub featured</a> · <a href="{url('newsletter/')}">Newsletter</a> · <a href="{E(subscribe_url())}">Subscribe free</a></p>
<p>Poland fixtures: Ekstraklasa from <a href="https://ekstraklasa.org/terminarz/">ekstraklasa.org</a> (official); 1. Liga from <a href="https://www.thesportsdb.com/">TheSportsDB</a> (community data). Last refresh: {E(EK['fetched'])} (Polish time). All times Europe/Warsaw. Always confirm with the club before travelling.</p>
<p>Unofficial fan guide. Not affiliated with Ekstraklasa S.A. or any club.</p>"""
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{canon}">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:type" content="website">
<meta property="og:url" content="{canon}"><meta property="og:site_name" content="{E(site)}"><meta property="og:locale" content="en_GB">
<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{E(title)}"><meta name="twitter:description" content="{E(desc)}">
<link rel="stylesheet" href="{url('style.css')}">
<script nowprocket data-noptimize="1" data-cfasync="false" data-wpfc-render="false" seraph-accel-crit="1" data-no-defer="1" data-cmp-ab="2">
  (function () {{
      var script = document.createElement("script");
      script.async = 1;
      script.setAttribute("data-cmp-ab","2");
      script.src = 'https://emrldco.com/NTg3OTky.js?t=587992';
      document.head.appendChild(script);
  }})();
</script>
</head><body>
<header><div class="{wrap}"><div class="top"><a class="logo" href="{url()}">Away <span>Day</span></a><nav>{nav}</nav></div>{body[0]}</div></header>
<main class="{wrap}">{body[1]}</main>
<footer><div class="{wrap}">{footer}</div></footer></body></html>"""
    f = OUT / path / "index.html" if not path.endswith(".html") else OUT / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(doc, encoding="utf-8")

def hero(h1, p): return f"<div class='hero'><h1>{E(h1)}</h1><p>{p}</p></div>"

def match_card(m, prefix):
    c = club_by_name.get(m["home"])
    tag = "<span class='tag'>Ekstraklasa</span>" if m["league"] == "Ekstraklasa" else "<span class='tag l1'>1. Liga</span>"
    right = f"<strong>{E(m['score'])}</strong>" if m["score"] else (f"<span class='badge {STATUS[c['passport']][1]}'>{STATUS[c['passport']][0]}</span>" if c else "<span class='small'>Ticket rules: unverified</span>")
    venue = E(m["venue"]) if m["venue"] else "Venue unverified"
    return f"""<div class='card match'><div><div class='teams'><a href='{url('match/' + m['id'] + '/')}'>{E(m['home'])} – {E(m['away'])}</a></div><div class='meta'>{tag}Round {m['round']} · {venue}</div></div>
<div class='meta'>{fmt_time(m)}</div><div>{right}</div></div>"""

def weekend_window(now):
    d = now.date()
    wd = d.weekday()  # Mon=0
    fri = d + dt.timedelta(days=(4 - wd)) if wd <= 3 else d - dt.timedelta(days=(wd - 4))
    start = dt.datetime.combine(fri, dt.time(0), WAW)
    end = start + dt.timedelta(days=4)  # Fri..Mon
    return start, end

def build():
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    (OUT / "style.css").write_text(CSS)
    urls = []

    # HOME — Away Day from Poland
    away_title = "Away Day from Poland – cheapest football weekends with direct flights"
    away_desc = "Cheapest football weekends abroad from Polish airports. Each weekend: a top 15 of cached direct return fares, then every match you can fly to. Prices are not live — check before you book."
    trips_path = ROOT / "awayday" / "data" / "trips.json"
    routes_path = ROOT / "awayday" / "data" / "routes_from_poland.json"
    if trips_path.exists():
        away = json.loads(trips_path.read_text())
        updated = away.get("fares_fetched")
        if updated:
            try:
                stamp = dt.datetime.fromisoformat(updated).strftime("%d %b %Y, %H:%M UTC")
            except ValueError:
                stamp = updated + " UTC"
            updated_line = f"Prices last updated {stamp}."
        else:
            updated_line = "Prices last updated: not yet. Showing no cached fares until a fetch succeeds."
        rate = away.get("ecb_pln_per_eur")
        eur_note = f" Euro amounts use the ECB rate of {rate} PLN per euro ({away.get('ecb_date')})." if rate else ""
        wiki_links = ""
        if routes_path.exists():
            routes = json.loads(routes_path.read_text())
            bits = []
            for code, ap in routes.get("airports", {}).items():
                slug = ap.get("wikipedia_page", "").replace(" ", "_")
                if slug:
                    bits.append(f'<a href="https://en.wikipedia.org/wiki/{quote_plus(slug).replace("+", "_")}">{E(code)}</a>')
            if bits:
                wiki_links = " Airport pages used: " + ", ".join(bits) + "."
        note = f"""<div class="how"><h2>How it works</h2>
<p>Direct return flights from a Polish airport to an airport within {MAX_KM} km of the stadium. You fly out the day before the match, or on match day only when the cached flight lands at least 3 hours before kickoff, and you fly back the next day.</p>
<p><strong>Prices are cached</strong>, not a live search. They are fares Aviasales users found recently. {E(updated_line)} Check the price on Aviasales before you book. A cabin bag is usually extra.{E(eur_note)} Routes come from Wikipedia and can be out of date. Kickoffs come from TheSportsDB and are cross-checked against openfootball where that league exists.</p>
<p>Each weekend also lists <strong>No flight needed</strong> trips: a direct train from a Polish city in about 8 hours or less. That time is a typical published journey, not a live departure, and the page does not show a train fare.</p>
<p class="small">Watching in Poland instead? <a href="{url('matches-in-poland/')}">Matches in Poland</a>.</p></div>"""
        lists = f'<div class="aday">{inner_html(away)}</div>'
        unreachable = len(away.get("unreachable") or [])
        foot = f"""<p><a href="{url('about/')}">About</a> · <a href="{url('matches-in-poland/')}">Matches in Poland</a> · <a href="{url('newsletter/')}">Newsletter</a> · <a href="{E(subscribe_url())}">Subscribe free</a></p>
<p>{unreachable} more weekend matches have no direct route from Poland to an airport within {MAX_KM} km. {E(updated_line)}</p>
<p>Fares: <a href="https://support.travelpayouts.com/hc/en-us/articles/203956163-Aviasales-Data-API">Travelpayouts Aviasales Data API</a> (cached prices, not live). Flight links are Aviasales affiliate links. Fixtures: <a href="https://www.thesportsdb.com/">TheSportsDB</a> and <a href="https://github.com/openfootball/football.json">openfootball/football.json</a> (CC0). Stadium coordinates: <a href="https://www.wikidata.org/">Wikidata</a> (CC0). Airports: <a href="https://ourairports.com/">OurAirports</a> (public domain).</p>
<p>Routes are adapted from the English Wikipedia “Airlines and destinations” sections by Wikipedia contributors, <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>. We turned those lists into airport pairs and dropped charter-only routes.{wiki_links}</p>
<p>Ground trips use hand-checked typical times from the source linked on each card, including <a href="https://www.spravazeleznic.cz/">Správa železnic</a>, <a href="https://www.seat61.com/trains-and-routes/berlin-to-warsaw-by-train.htm">Seat61</a>, <a href="https://en.wikipedia.org/wiki/Berlin-Warszawa-Express">Wikipedia</a>, <a href="https://krakow.pl/getHtml?dok_id=319347">the City of Kraków</a>, <a href="https://www.leoexpress.com/en/where-we-go/connections/krakow-prague">Leo Express</a> and <a href="https://slovakia.travel/en/travel-essentials/transport/getting-here/by-train">slovakia.travel</a>. Checked 20 Oct 2026. Not a live timetable.</p>
<p>Unofficial. Not affiliated with any club, league, airline, or Aviasales.</p>"""
    else:
        note = "<p class='empty'>Trip data is not available yet.</p>"
        lists = ""
        foot = None
    nl = f"""<h2>Get the weekend list</h2><div class='card'><p>A short email when the next cheap football weekends are up. Free. This opens the newsletter subscribe page with your email filled in. Nothing is stored on this site.</p>
{newsletter_form('away-nl-email')}</div>"""
    page("", away_title, away_desc,
         (hero("Away Day from Poland", "The cheapest football weekends abroad, with direct flights from Polish airports."), note + lists + nl),
         "", wide=True, site_name="Away Day from Poland", footer=foot)
    urls.append("")

    # MATCHES IN POLAND (former home page; same fixtures, tickets and bars)
    s, e = weekend_window(NOW)
    wk = [m for m in ALL if (d := mdt(m)) and s <= d < e]
    nxt = [m for m in ALL if (d := mdt(m)) and e <= d < e + dt.timedelta(days=10)]
    body = f"<p class='small'>Weekend of {s.strftime('%a %d %b')} – {(e - dt.timedelta(days=1)).strftime('%a %d %b %Y')}. Kickoff times in Polish time (Europe/Warsaw). 1. Liga times come from community data – confirm with the club.</p>"
    body += "<h2>This weekend in Poland</h2>" + ("".join(match_card(m, "") for m in wk) or "<p class='empty'>No matches found for this weekend.</p>")
    body += "<h2>Coming up next</h2>" + ("".join(match_card(m, "") for m in nxt) or "<p class='empty'>Nothing scheduled yet.</p>")
    body += f"""<h2>New to Polish football?</h2><div class='grid'>
<div class='card'><strong>Can I buy online with a passport?</strong><p class='small'>Mostly yes. See the <a href='{url("tickets-for-foreigners/")}'>club-by-club table</a> with official sources.</p></div>
<div class='card'><strong>Watching the Premier League?</strong><p class='small'>English-friendly <a href='{url("where-to-watch/")}'>sports bars</a> in Warsaw, Kraków, Wrocław, Poznań, Gdańsk, Łódź, Gliwice, Białystok and Lublin.</p></div>
<div class='card'><strong>Flying out instead?</strong><p class='small'>The <a href='{url()}'>Away Day</a> home page lists the cheapest weekends abroad with a direct flight.</p></div>
<div class='card'><strong>Get the weekly email</strong><p class='small'>The best matches to see in Poland, every Thursday.</p>{newsletter_form('home-nl-email')}</div></div>"""
    page("matches-in-poland/", "Football in Poland this weekend – Ekstraklasa & 1. Liga fixtures in English | Poland Matchday",
         "This weekend's Ekstraklasa and 1. Liga matches with kickoff times in Polish time, ticket rules for foreigners and where to watch. In English.",
         (hero("Football in Poland this weekend", "Ekstraklasa & 1. Liga fixtures, tickets for foreigners and where to watch – in English."), body), "../")
    urls.append("matches-in-poland/")

    # TICKETS FOR FOREIGNERS
    cnt = Counter(c["passport"] for c in CLUBS["clubs"])
    rows = "".join(f"<tr><td><a href='{url('clubs/' + c['slug'] + '/')}'>{E(c['name'])}</a></td><td><span class='badge {STATUS[c['passport']][1]}'>{STATUS[c['passport']][0]}</span></td><td><a href='{E(c['ticket_url'])}' rel='nofollow'>Official ticket site</a></td><td class='small'><a href='{E(c['source'])}' rel='nofollow'>source</a>, checked {CLUBS['checked']}</td></tr>" for c in sorted(CLUBS["clubs"], key=lambda c: ("yes accepted unclear unverified".split().index(c["passport"]), c["name"])))
    leg = "".join(f"<li><span class='badge {STATUS[k][1]}'>{STATUS[k][0]}</span> {E(v)}</li>" for k, v in CLUBS["status_legend"].items())
    body = f"""<p>Polish clubs must sell named tickets (stadium safety law), so every shop asks for a PESEL – the Polish ID number. Visitors don't have one. The good news from the clubs' own pages: <strong>{cnt['yes']} of 18</strong> Ekstraklasa clubs explicitly let you buy online with a passport number, <strong>{cnt['accepted']}</strong> accept a passport in their rules without spelling out the online shop, and <strong>{cnt['unclear']}</strong> is unclear.</p>
<ul class='small'>{leg}</ul><table><tr><th>Club</th><th>Passport online?</th><th>Buy</th><th>Evidence</th></tr>{rows}</table>
<p class='small'>Bring the same passport to the stadium – tickets are personal and ID can be checked at the gate. Rules change; we re-check official pages and show the date checked.</p>
<p>1. Liga is a different set of clubs. <a href='{url("tickets-1-liga/")}'>Ticket rules for 1. Liga</a> — only where the club has published them.</p>"""
    page("tickets-for-foreigners/", "Ekstraklasa tickets for foreigners: buying without a PESEL (2026/27) | Poland Matchday",
         "Can you buy Polish football tickets online with a passport? Club-by-club answers for all 18 Ekstraklasa clubs, from official ticket pages.",
         (hero("Ekstraklasa tickets for foreigners", "Buying without a PESEL – club by club, from official sources."), body), "../")
    urls.append("tickets-for-foreigners/")

    # 1. LIGA TICKET RULES
    liga_by = {c["name"]: c for c in LIGA["clubs"]}
    known = set()
    for m in L1["matches"]:
        known.add(m["home"]); known.add(m["away"])
    blocks = []
    for c in sorted(LIGA["clubs"], key=lambda c: c["name"]):
        st = STATUS[c["passport"]]
        buy = f"<p><a href='{E(c['buy'])}' rel='nofollow'>Where the club says to buy</a></p>" if c.get("buy") else ""
        blocks.append(f"""<div class='card' id='{E(c['slug'])}'><h2>{E(c['name'])}</h2>
<p><span class='badge {st[1]}'>{st[0]}</span></p><p>{E(c['text'])}</p>{buy}
<p class='small'>Source: <a href='{E(c['source'])}' rel='nofollow'>official club page</a> · checked {LIGA['checked']}</p></div>""")
    rest = sorted(n for n in known if n not in liga_by)
    rest_html = "".join(f"<li>{E(n)}</li>" for n in rest)
    body = f"""<p>1. Liga clubs also sell named tickets. Below is only what each club has published about a passport or Fan Card (karta kibica), and where to buy. If a club is not in the cards, we have not found an official rule yet — check before you go.</p>
<ul class='small'>{leg}</ul>
{''.join(blocks)}
<h2>Not yet verified</h2><div class='card'><p>No official passport or Fan Card rule found for these 1. Liga clubs in this check:</p><ul>{rest_html}</ul><p class='small'>Checked {LIGA['checked']}. We will add a club when its own ticket page or regulations say so.</p></div>"""
    page("tickets-1-liga/", "1. Liga tickets for foreigners: Fan Card and passport rules | Poland Matchday",
         "Can visitors buy 1. Liga tickets with a passport? Club-by-club rules from official ticket pages, including ŁKS, Arka, Warta, Lechia, Ruch, Odra, Puszcza and Podbeskidzie.",
         (hero("1. Liga tickets for foreigners", "Fan Card, passport and where to buy — only what each club publishes."), body), "../")
    urls.append("tickets-1-liga/")

    # CLUBS index + pages
    cards = "".join(f"<div class='card'><a href='{url('clubs/' + c['slug'] + '/')}'><strong>{E(c['name'])}</strong></a><br><span class='small'>{E(c['stadium'])}</span><br><span class='badge {STATUS[c['passport']][1]}'>{STATUS[c['passport']][0]}</span></div>" for c in sorted(CLUBS["clubs"], key=lambda c: c["name"]))
    page("clubs/", "Ekstraklasa clubs 2026/27 – stadiums & tickets for visitors | Poland Matchday",
         "All 18 Ekstraklasa clubs for 2026/27: stadium, official ticket site and whether foreigners can buy online with a passport.",
         (hero("Ekstraklasa clubs 2026/27", "Stadiums, official ticket sites and passport rules for all 18 clubs."), f"<div class='grid'>{cards}</div>"), "../")
    urls.append("clubs/")
    for c in CLUBS["clubs"]:
        st = STATUS[c["passport"]]
        up = [m for m in ALL if c["name"] in (m["home"], m["away"]) and not m["finished"] and (not m["date"] or mdt(m) >= NOW - dt.timedelta(hours=3))][:6]
        price = f"<p>{E(c['price']['text'])}<br><span class='small'>Source: <a href='{E(c['price']['source'])}' rel='nofollow'>{E(c['price']['type'])}</a>, checked {CLUBS['checked']}</span></p>" if c.get("price") else "<p class='empty'>Not yet verified from an official price list – check the <a href='" + E(c['ticket_url']) + "' rel='nofollow'>official ticket site</a>.</p>"
        avoid = f"<p>{E(c['avoid']['text'])}<br><span class='small'>Source: <a href='{E(c['avoid']['source'])}' rel='nofollow'>{E(c['avoid']['type'])}</a></span></p>" if c.get("avoid") else "<p class='empty'>Not yet researched. If you know the home ultras' stand, <a href='" + url("about/") + "'>tell us</a>.</p>"
        if c.get("transport"):
            transport = f"<p>{E(c['transport']['text'])}<br><span class='small'>Source: <a href='{E(c['transport']['source'])}' rel='nofollow'>{E(c['transport'].get('type') or 'official')}</a>, checked {CLUBS['checked']}</span></p>"
        else:
            transport = "<p class='empty'>Not yet verified from the club or the local transport operator. Check before you go, and use the map link above.</p>"
        maps = "https://www.google.com/maps/search/?api=1&query=" + quote_plus(c["stadium"] + " " + c["town"])
        city = CITIES.get(c["city"]) if c["city"] else None
        citylink = f"<p>More in <a href='{url('cities/' + c['city'] + '/')}'>{E(city['name'])}</a>.</p>" if city else ""
        body = f"""<div class='card'><p><strong>Stadium:</strong> {E(c['stadium'])}, {E(c['town'])} · <a href='{maps}' rel='nofollow'>Map</a></p>
<p><strong>Official tickets:</strong> <a href='{E(c['ticket_url'])}' rel='nofollow'>{E(c['ticket_url'])}</a></p></div>
<h2>Can I buy online with a passport?</h2><div class='card'><p><span class='badge {st[1]}'>{st[0]}</span></p><p>{E(c['evidence'])}</p>
<p class='small'>Source: <a href='{E(c['source'])}' rel='nofollow'>official club document</a> · checked {CLUBS['checked']}</p></div>
<h2>Ticket prices</h2><div class='card'>{price}</div>
<h2>Stands to avoid as a neutral</h2><div class='card'>{avoid}</div>
<h2>Getting there</h2><div class='card'>{transport}</div>
<h2>Next matches</h2>{''.join(match_card(m, '../../') for m in up) or "<p class='empty'>No upcoming fixtures found.</p>"}
{citylink}{aff_box(c['town'] or c['name'], '../../')}"""
        page(f"clubs/{c['slug']}/", f"{c['en']} tickets for foreigners – stadium, passport rules & fixtures | Poland Matchday",
             f"How to buy {c['en']} tickets as a foreigner: passport rules from the official ticket site, stadium ({c['stadium']}), next home and away matches.",
             (hero(f"{c['en']} tickets for foreigners", f"{E(c['stadium'])} · {E(c['town'])}"), body), "../../")
        urls.append(f"clubs/{c['slug']}/")

    # MATCH pages
    for m in ALL:
        c = club_by_name.get(m["home"])
        tl = m["ticket_url"] or (c["ticket_url"] if c else None)
        info = f"<p><strong>Kickoff:</strong> {fmt_time(m)}</p><p><strong>Venue:</strong> {E(m['venue'] or 'unverified')}</p>"
        if m["score"]: info += f"<p><strong>Result:</strong> {E(m['score'])}</p>"
        tick = ""
        if c:
            st = STATUS[c["passport"]]
            tick = f"<h2>Tickets</h2><div class='card'><p><span class='badge {st[1]}'>{st[0]}</span> <a href='{url('clubs/' + c['slug'] + '/')}'>Full rules for {E(c['name'])}</a></p>" + (f"<p><a class='btn' href='{E(tl)}' rel='nofollow'>Official tickets</a></p>" if tl else "") + "</div>"
        else:
            rec = liga_by.get(m["home"])
            if rec:
                st = STATUS[rec["passport"]]
                tick = f"<h2>Tickets</h2><div class='card'><p><span class='badge {st[1]}'>{st[0]}</span> <a href='{url('tickets-1-liga/#' + rec['slug'])}'>Ticket rules for {E(rec['name'])}</a></p>" + (f"<p><a class='btn' href='{E(rec['buy'])}' rel='nofollow'>Official tickets</a></p>" if rec.get("buy") else "") + "</div>"
            else:
                tick = f"<h2>Tickets</h2><div class='card'><p class='empty'>Ticket rules for this club not yet verified. <a href='{url('tickets-1-liga/')}'>1. Liga ticket rules</a></p></div>"
        note = "" if m["league"] == "Ekstraklasa" else "<p class='warnbox small'>1. Liga data comes from a community database (TheSportsDB). Confirm date and kickoff with the club.</p>"
        town = (m["venue"] or "").split(", ")[0] or (c["town"] if c else "Poland")
        body = f"""<div class='card'>{info}<p class='small'>{E(m['league'])}, round {m['round']} · <a href='{E(m['source_url'])}' rel='nofollow'>data source</a></p></div>{note}{tick}
<p>Clubs: {club_link(m['home'], '../../')} vs {club_link(m['away'], '../../')}</p>{aff_box(town, '../../')}"""
        d = mdt(m)
        ds = d.strftime("%d %b %Y") if d else "date TBC"
        page(f"match/{m['id']}/", f"{m['home']} vs {m['away']} – {ds} tickets & kickoff time | Poland Matchday",
             f"{m['home']} v {m['away']} ({m['league']}, round {m['round']}): kickoff in Polish time, venue and how foreigners can buy tickets.",
             (hero(f"{m['home']} vs {m['away']}", f"{E(m['league'])} · {fmt_time(m)}"), body), "../../")
        urls.append(f"match/{m['id']}/")

    # CITIES
    cards = "".join(f"<div class='card'><a href='{url('cities/' + k + '/')}'><strong>{E(v['name'])}</strong></a><br><span class='small'>{E(', '.join(v['ek'] + v['l1']) or '—')}</span></div>" for k, v in CITIES.items())
    page("cities/", "Football by city in Poland – Warsaw, Kraków, Wrocław, Gdańsk & more | Poland Matchday",
         "Which clubs play in each Polish city, upcoming matches and English-friendly sports bars.", (hero("Football by city", "Pick a city to see its clubs and next matches."), f"<div class='grid'>{cards}</div>"), "../")
    urls.append("cities/")
    for k, v in CITIES.items():
        teams = v["ek"] + v["l1"]
        def l1_line(t):
            rec = liga_by.get(t)
            if not rec:
                return f"<li>{E(t)} <span class='tag l1'>1. Liga</span> <span class='small'>(ticket rules not yet verified)</span></li>"
            st = STATUS[rec["passport"]]
            return f"<li><a href='{url('tickets-1-liga/#' + rec['slug'])}'>{E(t)}</a> <span class='tag l1'>1. Liga</span> <span class='badge {st[1]}'>{st[0]}</span></li>"
        clubs_html = "".join(f"<li>{club_link(t, '../../')} <span class='tag'>Ekstraklasa</span></li>" for t in v["ek"]) + "".join(l1_line(t) for t in v["l1"])
        up = [m for m in ALL if m["home"] in teams and not m["finished"] and (not m["date"] or mdt(m) >= NOW - dt.timedelta(hours=3))][:8]
        pubs = [p for p in PUBS["pubs"] if p["city"] == k]
        pubs_html = "".join(f"<li><a href='{E(p['url'])}' rel='nofollow'>{E(p['name'])}</a> – {E(p['address'])} · <a href='https://www.google.com/maps/search/?api=1&query={quote_plus(p['address'])}' rel='nofollow'>Map</a></li>" for p in pubs)
        body = f"""<h2>Clubs</h2><div class='card'><ul>{clubs_html}</ul>{('<p class=small>' + E(CITY_NOTE[k]) + '</p>') if k in CITY_NOTE else ''}</div>
<h2>Home matches coming up</h2>{''.join(match_card(m, '../../') for m in up) or "<p class='empty'>No upcoming home fixtures found.</p>"}
<h2>Where to watch the Premier League / Champions League</h2><div class='card'>{('<ul>' + pubs_html + '</ul>') if pubs else "<p class='empty'>No verified bars yet.</p>"}<p class='small'><a href='{url("where-to-watch/")}'>All bars</a> · <a href='{url("get-featured/")}'>Own a bar? Get listed</a></p></div>
{aff_box(v['gyg'], '../../')}"""
        page(f"cities/{k}/", f"Football in {v['name']}: matches, tickets & where to watch | Poland Matchday",
             f"Football in {v['name']} for visitors: {', '.join(teams)} – upcoming matches, ticket rules for foreigners and English-friendly sports bars.",
             (hero(f"Football in {v['name']}", E(v['pl'])), body), "../../")
        urls.append(f"cities/{k}/")

    # WHERE TO WATCH
    def pubcard(p):
        f = lambda x: E(x) if x != "unverified" else "<span class='small'>unverified</span>"
        maps = "https://www.google.com/maps/search/?api=1&query=" + quote_plus(p["address"])
        note = E(p["source_note"]) if p.get("source_note") else "venue's own website"
        return f"""<div class='card'><strong><a href='{E(p['url'])}' rel='nofollow'>{E(p['name'])}</a></strong> <span class='tag'>{E(CITIES[p['city']]['name'])}</span>
<p class='small'>{E(p['address'])} · <a href='{maps}' rel='nofollow'>Map</a> · {f(p['phone'])}</p><p><strong>Shows:</strong> {E(p['shows'])}<br><strong>Screens:</strong> {f(p['screens'])}<br>
<strong>English commentary:</strong> {f(p['english_commentary'])}<br><strong>Booking:</strong> {f(p['booking'])}<br><strong>Hours:</strong> {f(p['hours'])}</p>
<p class='small'>Source: <a href='{E(p['url'])}' rel='nofollow'>{note}</a>, checked {PUBS['checked']}</p></div>"""
    order = list(CITIES)
    grouped = []
    for key in order:
        group = [p for p in PUBS["pubs"] if p["city"] == key]
        if not group:
            continue
        grouped.append(f"<h2>{E(CITIES[key]['name'])}</h2>" + "".join(pubcard(p) for p in group))
    body = "<p>Sports bars near Ekstraklasa grounds and in city centres, checked from each venue's own website (or, where noted, the city's official tourism page). Real addresses only. Fields we could not confirm are marked <em>unverified</em>. No verified bar yet in Szczecin, Zabrze or Chorzów.</p>" + "".join(grouped) + f"<p><a class='btn' href='{url('get-featured/')}'>Own a bar? Get listed or featured</a></p>"
    page("where-to-watch/", "Where to watch football in Poland: sports bars in Warsaw, Kraków, Wrocław and more | Poland Matchday",
         "Fan-friendly sports bars in Warsaw, Kraków, Wrocław, Poznań, Gdańsk, Łódź, Gliwice, Białystok and Lublin, with addresses and map links. Checked from each venue's own site.",
         (hero("Where to watch football in Poland", "Sports bars with a real address, checked from the venue."), body), "../")
    urls.append("where-to-watch/")

    # GET FEATURED
    body = """<p>Run a bar in Poland that shows the Premier League, Champions League or Ekstraklasa to an English-speaking crowd? Get a free basic listing, or ask about a <strong>featured</strong> spot on city pages and in the weekly newsletter.</p>
<form class='card' onsubmit="event.preventDefault();document.getElementById('msg').textContent='Thanks! Submissions are not live yet – this form is a preview.';">
<label>Bar name</label><input required name='name'><label>City</label><select name='city'><option>Warsaw</option><option>Kraków</option><option>Wrocław</option><option>Gdańsk / Tricity</option><option>Poznań</option><option>Szczecin</option><option>Łódź</option><option>Katowice area</option><option>Białystok</option><option>Lublin</option><option>Other</option></select>
<label>Website / Google Maps link</label><input name='url' type='url'><label>Which competitions do you show? English commentary?</label><textarea name='shows' rows='3'></textarea>
<label>Contact email</label><input name='email' type='email' required><label>Interested in</label><select name='plan'><option>Free basic listing</option><option>Featured listing (paid)</option></select>
<p><button class='btn' type='submit'>Submit</button></p><p id='msg' class='small'></p><p class='small'>Preview only – no data is sent or stored yet.</p></form>"""
    page("get-featured/", "Get your sports bar listed – Poland Matchday", "List your English-friendly sports bar in Poland on Poland Matchday's where-to-watch guide.",
         (hero("Get your bar featured", "Reach visiting fans and expats looking for a place to watch the game."), body), "../")
    urls.append("get-featured/")

    # NEWSLETTER
    body = f"""<div class='card'><p>Every Thursday: the best matches to see in Poland this weekend, ticket sale openings, and where to watch the big games. Free.</p>
{newsletter_form('nl-email')}
<p class='small'>Subscribe free. This opens the newsletter’s subscribe page with your email filled in. Nothing is stored on this site.</p></div>"""
    page("newsletter/", "Poland Matchday newsletter – this weekend's best football in Poland", "A free weekly email with the best football matches to see in Poland, ticket news and where to watch.",
         (hero("The weekly Poland Matchday email", "Every Thursday, free."), body), "../")
    urls.append("newsletter/")

    # ABOUT
    body = f"""<div class='card'><p>Poland Matchday is an independent, English-language guide for visitors and expats who want to see live football in Poland – or find a bar showing the Premier League.</p>
<p><strong>How we source data:</strong> Ekstraklasa fixtures come from the official <a href='https://ekstraklasa.org/terminarz/'>ekstraklasa.org</a> fixture pages and refresh automatically. 1. Liga fixtures come from <a href='https://www.thesportsdb.com/'>TheSportsDB</a>, a community database, so please confirm them. Ticket rules come only from clubs' own ticket pages and regulations, each linked with the date we checked it. Where we couldn't confirm something we say <em>unverified</em> rather than guess.</p>
<p>The home page, <a href="{url()}">Away Day from Poland</a>, lists cheap football weekends abroad with direct flights from Polish airports. Those flight links go to Aviasales and include our Travelpayouts partner marker. Fares on that page are cached, not live.</p>
<p><strong>Affiliate disclosure:</strong> Aviasales flight links on the home page are affiliate links. GetYourGuide and Booking.com links on the Poland pages still use placeholder partner ids and are not live affiliate links.</p>
<p>Not affiliated with Ekstraklasa S.A., PZPN or any club. Spotted an error? Corrections form coming soon.</p></div>"""
    page("about/", "About Poland Matchday", "Who we are and how Poland Matchday sources fixtures and ticket rules.", (hero("About Poland Matchday", "Independent. In English. Sourced."), body), "../")
    urls.append("about/")

    base = CFG["base_url"].rstrip("/")
    (OUT / "sitemap.xml").write_text("<?xml version='1.0' encoding='UTF-8'?>\n<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>" + "".join(f"<url><loc>{base}/{u}</loc></url>" for u in urls) + "</urlset>")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")
    print(f"built {len(urls)} pages into {OUT}")

if __name__ == "__main__":
    build()
