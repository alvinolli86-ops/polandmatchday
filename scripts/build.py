#!/usr/bin/env python3
"""Build the static site into ./site from ./data. Usage: python3 scripts/build.py"""
import json, shutil, html, datetime as dt, re
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import quote_plus, urlparse
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site"
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
CLUBS = json.load(open(ROOT / "data/clubs.json"))
PUBS = json.load(open(ROOT / "data/pubs.json"))
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
@media(min-width:700px){.hero h1{font-size:2.1rem}.match{grid-template-columns:1.4fr 1fr auto;align-items:center}}
"""

def page(path, title, desc, body, prefix=None):
    nav = "".join(f"<a href='{url(h)}'>{t}</a>" for h, t in [("", "This weekend"), ("clubs/", "Clubs"), ("cities/", "Cities"), ("tickets-for-foreigners/", "Tickets for foreigners"), ("where-to-watch/", "Where to watch"), ("newsletter/", "Newsletter")])
    canon = CFG["base_url"].rstrip("/") + "/" + path
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{canon}">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:type" content="website">
<link rel="stylesheet" href="{url('style.css')}"></head><body>
<header><div class="wrap"><div class="top"><a class="logo" href="{url()}">⚽ Poland <span>Matchday</span></a><nav>{nav}</nav></div>{body[0]}</div></header>
<main class="wrap">{body[1]}</main>
<footer><div class="wrap"><p><a href="{url('about/')}">About</a> · <a href="{url('get-featured/')}">Get your pub featured</a> · <a href="{url('newsletter/')}">Newsletter</a></p>
<p>Fixtures: Ekstraklasa from <a href="https://ekstraklasa.org/terminarz/">ekstraklasa.org</a> (official); 1. Liga from <a href="https://www.thesportsdb.com/">TheSportsDB</a> (community data). Last refresh: {E(EK['fetched'])} (Polish time). All times Europe/Warsaw. Always confirm with the club before travelling.</p>
<p>Unofficial fan guide. Not affiliated with Ekstraklasa S.A. or any club.</p></div></footer></body></html>"""
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

    # HOME
    s, e = weekend_window(NOW)
    wk = [m for m in ALL if (d := mdt(m)) and s <= d < e]
    nxt = [m for m in ALL if (d := mdt(m)) and e <= d < e + dt.timedelta(days=10)]
    body = f"<p class='small'>Weekend of {s.strftime('%a %d %b')} – {(e - dt.timedelta(days=1)).strftime('%a %d %b %Y')}. Kickoff times in Polish time (Europe/Warsaw). 1. Liga times come from community data – confirm with the club.</p>"
    body += "<h2>This weekend in Poland</h2>" + ("".join(match_card(m, "") for m in wk) or "<p class='empty'>No matches found for this weekend.</p>")
    body += "<h2>Coming up next</h2>" + ("".join(match_card(m, "") for m in nxt) or "<p class='empty'>Nothing scheduled yet.</p>")
    body += f"""<h2>New to Polish football?</h2><div class='grid'>
<div class='card'><strong>Can I buy online with a passport?</strong><p class='small'>Mostly yes. See the <a href='{url("tickets-for-foreigners/")}'>club-by-club table</a> with official sources.</p></div>
<div class='card'><strong>Watching the Premier League?</strong><p class='small'>English-friendly <a href='{url("where-to-watch/")}'>sports bars in Warsaw & Kraków</a>.</p></div>
<div class='card'><strong>Get the weekly email</strong><p class='small'>The best matches to see in Poland, every Thursday. <a href='{url("newsletter/")}'>Sign up</a>.</p></div></div>"""
    page("", "Football in Poland this weekend – Ekstraklasa & 1. Liga fixtures in English | Poland Matchday",
         "This weekend's Ekstraklasa and 1. Liga matches with kickoff times in Polish time, ticket rules for foreigners and where to watch. In English.",
         (hero("Football in Poland this weekend", "Ekstraklasa & 1. Liga fixtures, tickets for foreigners and where to watch – in English."), body), "")
    urls.append("")

    # TICKETS FOR FOREIGNERS
    cnt = Counter(c["passport"] for c in CLUBS["clubs"])
    rows = "".join(f"<tr><td><a href='{url('clubs/' + c['slug'] + '/')}'>{E(c['name'])}</a></td><td><span class='badge {STATUS[c['passport']][1]}'>{STATUS[c['passport']][0]}</span></td><td><a href='{E(c['ticket_url'])}' rel='nofollow'>Official ticket site</a></td><td class='small'><a href='{E(c['source'])}' rel='nofollow'>source</a>, checked {CLUBS['checked']}</td></tr>" for c in sorted(CLUBS["clubs"], key=lambda c: ("yes accepted unclear unverified".split().index(c["passport"]), c["name"])))
    leg = "".join(f"<li><span class='badge {STATUS[k][1]}'>{STATUS[k][0]}</span> {E(v)}</li>" for k, v in CLUBS["status_legend"].items())
    body = f"""<p>Polish clubs must sell named tickets (stadium safety law), so every shop asks for a PESEL – the Polish ID number. Visitors don't have one. The good news from the clubs' own pages: <strong>{cnt['yes']} of 18</strong> Ekstraklasa clubs explicitly let you buy online with a passport number, <strong>{cnt['accepted']}</strong> accept a passport in their rules without spelling out the online shop, and <strong>{cnt['unclear']}</strong> is unclear.</p>
<ul class='small'>{leg}</ul><table><tr><th>Club</th><th>Passport online?</th><th>Buy</th><th>Evidence</th></tr>{rows}</table>
<p class='small'>Bring the same passport to the stadium – tickets are personal and ID can be checked at the gate. Rules change; we re-check official pages and show the date checked.</p>"""
    page("tickets-for-foreigners/", "Ekstraklasa tickets for foreigners: buying without a PESEL (2026/27) | Poland Matchday",
         "Can you buy Polish football tickets online with a passport? Club-by-club answers for all 18 Ekstraklasa clubs, from official ticket pages.",
         (hero("Ekstraklasa tickets for foreigners", "Buying without a PESEL – club by club, from official sources."), body), "../")
    urls.append("tickets-for-foreigners/")

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
        maps = "https://www.google.com/maps/search/?api=1&query=" + quote_plus(c["stadium"] + " " + c["town"])
        city = CITIES.get(c["city"]) if c["city"] else None
        citylink = f"<p>More in <a href='{url('cities/' + c['city'] + '/')}'>{E(city['name'])}</a>.</p>" if city else ""
        body = f"""<div class='card'><p><strong>Stadium:</strong> {E(c['stadium'])}, {E(c['town'])} · <a href='{maps}' rel='nofollow'>Map</a></p>
<p><strong>Official tickets:</strong> <a href='{E(c['ticket_url'])}' rel='nofollow'>{E(c['ticket_url'])}</a></p></div>
<h2>Can I buy online with a passport?</h2><div class='card'><p><span class='badge {st[1]}'>{st[0]}</span></p><p>{E(c['evidence'])}</p>
<p class='small'>Source: <a href='{E(c['source'])}' rel='nofollow'>official club document</a> · checked {CLUBS['checked']}</p></div>
<h2>Ticket prices</h2><div class='card'>{price}</div>
<h2>Stands to avoid as a neutral</h2><div class='card'>{avoid}</div>
<h2>Getting there</h2><div class='card'><p class='empty'>Transport notes not yet verified. Use the map link above and local public transport apps.</p></div>
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
            tick = "<h2>Tickets</h2><div class='card'><p class='empty'>Ticket rules for this club not yet verified.</p></div>"
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
        clubs_html = "".join(f"<li>{club_link(t, '../../')} <span class='tag'>Ekstraklasa</span></li>" for t in v["ek"]) + "".join(f"<li>{E(t)} <span class='tag l1'>1. Liga</span> <span class='small'>(ticket rules not yet verified)</span></li>" for t in v["l1"])
        up = [m for m in ALL if m["home"] in teams and not m["finished"] and (not m["date"] or mdt(m) >= NOW - dt.timedelta(hours=3))][:8]
        pubs = [p for p in PUBS["pubs"] if p["city"] == k]
        pubs_html = "".join(f"<li><a href='{E(p['url'])}' rel='nofollow'>{E(p['name'])}</a> – {E(p['address'])}</li>" for p in pubs)
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
        return f"""<div class='card'><strong><a href='{E(p['url'])}' rel='nofollow'>{E(p['name'])}</a></strong> <span class='tag'>{E(CITIES[p['city']]['name'])}</span>
<p class='small'>{E(p['address'])} · {f(p['phone'])}</p><p><strong>Shows:</strong> {E(p['shows'])}<br><strong>Screens:</strong> {f(p['screens'])}<br>
<strong>English commentary:</strong> {f(p['english_commentary'])}<br><strong>Booking:</strong> {f(p['booking'])}<br><strong>Hours:</strong> {f(p['hours'])}</p>
<p class='small'>Source: <a href='{E(p['url'])}' rel='nofollow'>venue's own website</a>, checked {PUBS['checked']}</p></div>"""
    body = "<p>English-friendly sports bars showing the Premier League and Champions League, verified from each venue's own website. Fields we could not confirm are marked <em>unverified</em>.</p>" + "".join(pubcard(p) for p in PUBS["pubs"]) + f"<p><a class='btn' href='{url('get-featured/')}'>Own a bar? Get listed or featured</a></p>"
    page("where-to-watch/", "Where to watch the Premier League & Champions League in Warsaw and Kraków | Poland Matchday",
         "English-friendly sports bars in Poland showing Premier League and Champions League football – verified from the venues' own sites.",
         (hero("Where to watch the Premier League in Poland", "English-friendly sports bars in Warsaw & Kraków."), body), "../")
    urls.append("where-to-watch/")

    # GET FEATURED
    body = """<p>Run a bar in Poland that shows the Premier League, Champions League or Ekstraklasa to an English-speaking crowd? Get a free basic listing, or ask about a <strong>featured</strong> spot on city pages and in the weekly newsletter.</p>
<form class='card' onsubmit="event.preventDefault();document.getElementById('msg').textContent='Thanks! Submissions are not live yet – this form is a preview.';">
<label>Bar name</label><input required name='name'><label>City</label><select name='city'><option>Warsaw</option><option>Kraków</option><option>Wrocław</option><option>Gdańsk / Tricity</option><option>Poznań</option><option>Szczecin</option><option>Łódź</option><option>Katowice area</option><option>Other</option></select>
<label>Website / Google Maps link</label><input name='url' type='url'><label>Which competitions do you show? English commentary?</label><textarea name='shows' rows='3'></textarea>
<label>Contact email</label><input name='email' type='email' required><label>Interested in</label><select name='plan'><option>Free basic listing</option><option>Featured listing (paid)</option></select>
<p><button class='btn' type='submit'>Submit</button></p><p id='msg' class='small'></p><p class='small'>Preview only – no data is sent or stored yet.</p></form>"""
    page("get-featured/", "Get your sports bar listed – Poland Matchday", "List your English-friendly sports bar in Poland on Poland Matchday's where-to-watch guide.",
         (hero("Get your bar featured", "Reach visiting fans and expats looking for a place to watch the game."), body), "../")
    urls.append("get-featured/")

    # NEWSLETTER
    body = """<div class='card'><p>Every Thursday: the best matches to see in Poland this weekend, ticket sale openings, and where to watch the big games. Free.</p>
<form onsubmit="event.preventDefault();document.getElementById('nmsg').textContent='Thanks! The newsletter is launching soon – signups are not live yet.';">
<label>Email</label><input type='email' required placeholder='you@example.com'><p><button class='btn' type='submit'>Subscribe</button></p><p id='nmsg' class='small'></p></form>
<p class='small'>Placeholder – will connect to a newsletter tool before launch.</p></div>"""
    page("newsletter/", "Poland Matchday newsletter – this weekend's best football in Poland", "A free weekly email with the best football matches to see in Poland, ticket news and where to watch.",
         (hero("The weekly Poland Matchday email", "Every Thursday, free."), body), "../")
    urls.append("newsletter/")

    # ABOUT
    body = f"""<div class='card'><p>Poland Matchday is an independent, English-language guide for visitors and expats who want to see live football in Poland – or find a bar showing the Premier League.</p>
<p><strong>How we source data:</strong> Ekstraklasa fixtures come from the official <a href='https://ekstraklasa.org/terminarz/'>ekstraklasa.org</a> fixture pages and refresh automatically. 1. Liga fixtures come from <a href='https://www.thesportsdb.com/'>TheSportsDB</a>, a community database, so please confirm them. Ticket rules come only from clubs' own ticket pages and regulations, each linked with the date we checked it. Where we couldn't confirm something we say <em>unverified</em> rather than guess.</p>
<p><strong>Affiliate disclosure:</strong> some links (GetYourGuide, Booking.com) may earn us a commission at no cost to you.</p>
<p>Not affiliated with Ekstraklasa S.A., PZPN or any club. Spotted an error? Corrections form coming soon.</p></div>"""
    page("about/", "About Poland Matchday", "Who we are and how Poland Matchday sources fixtures and ticket rules.", (hero("About Poland Matchday", "Independent. In English. Sourced."), body), "../")
    urls.append("about/")

    base = CFG["base_url"].rstrip("/")
    (OUT / "sitemap.xml").write_text("<?xml version='1.0' encoding='UTF-8'?>\n<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>" + "".join(f"<url><loc>{base}/{u}</loc></url>" for u in urls) + "</urlset>")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")
    print(f"built {len(urls)} pages into {OUT}")

if __name__ == "__main__":
    build()
