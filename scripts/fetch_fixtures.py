#!/usr/bin/env python3
"""Refresh fixtures.

Ekstraklasa: official public fixture pages on ekstraklasa.org (/terminarz/<season>/kolejka-N/),
             server-rendered HTML, no key needed. Kickoff times there are Polish local time.
1. Liga:     TheSportsDB free public test key "123" (eventsround endpoint). strTimestamp is UTC.
             Community-maintained data -> shown with a "confirm with club" note.
Usage: python3 scripts/fetch_fixtures.py   (writes data/fixtures_*.json)
"""
import json, re, sys, time, datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SEASON = "2026-2027"
ROUNDS = 34
WAW = ZoneInfo("Europe/Warsaw")
UA = {"User-Agent": "PolandMatchdayBot/0.1 (+fixtures refresh; contact via site)"}
ABBR = re.compile(r"^[A-ZĄĆĘŁŃÓŚŹŻ]{3}$")

def year_for(month):  # season 2026-2027: Jul-Dec -> 2026, Jan-Jun -> 2027
    a, b = SEASON.split("-")
    return int(a) if month >= 7 else int(b)

def parse_round(html, rnd):
    s = BeautifulSoup(html, "html.parser")
    out, seen = [], set()
    for a in s.find_all("a", href=re.compile(r"^/mecz/[0-9a-f-]{36}/")):
        parts = a["href"].strip("/").split("/")
        mid, slug = parts[1], parts[2]
        if mid in seen:
            continue
        node = a
        box = None
        for _ in range(10):
            node = node.parent
            if node is None:
                break
            toks = [t for t in node.get_text("|", strip=True).split("|") if t.strip()]
            if sum(1 for t in toks if ABBR.match(t)) >= 2:
                box = node
                break
        if box is None:
            continue
        seen.add(mid)
        toks = [t.strip() for t in box.get_text("|", strip=True).split("|") if t.strip()]
        ab = [i for i, t in enumerate(toks) if ABBR.match(t)]
        home, away = toks[ab[0] + 1], toks[ab[1] + 1]
        tm = next((t for t in toks if re.match(r"^\d{2}:\d{2}$", t)), None)
        dm = next((t for t in toks if re.match(r"^\d{2}\.\d{2}$", t)), None)
        venue = next((t for t in toks if ", " in t and not re.search(r"\d{2}\.\d{2}", t)), None)
        finished = "Zakończony" in toks
        score = None
        if finished:
            seg = toks[ab[0] + 2: ab[1]]
            nums = [x for x in seg if x.isdigit()]
            if len(nums) >= 2:
                score = f"{nums[0]}–{nums[1]}"
        ticket = None
        for b in box.find_all("a", href=True):
            if "bilet" in b.get_text(" ", strip=True).lower():
                ticket = b["href"]
        kickoff = None
        date_iso = None
        if dm:
            d, m = map(int, dm.split("."))
            y = year_for(m)
            date_iso = f"{y:04d}-{m:02d}-{d:02d}"
            if tm:
                hh, mm = map(int, tm.split(":"))
                kickoff = dt.datetime(y, m, d, hh, mm, tzinfo=WAW).isoformat()
        out.append({
            "id": "ek-" + mid[:8], "league": "Ekstraklasa", "round": rnd,
            "home": home, "away": away, "date": date_iso, "kickoff": kickoff,
            "time_confirmed": bool(tm), "venue": venue, "finished": finished, "score": score,
            "ticket_url": ticket, "source_url": f"https://ekstraklasa.org/mecz/{mid}/{slug}/",
        })
    return out

def fetch_ekstraklasa():
    allm = []
    for r in range(1, ROUNDS + 1):
        url = f"https://ekstraklasa.org/terminarz/{SEASON}/kolejka-{r}/"
        try:
            resp = requests.get(url, headers=UA, timeout=20)
            resp.raise_for_status()
            ms = parse_round(resp.text, r)
            allm += ms
            print(f"Ekstraklasa round {r}: {len(ms)} matches", file=sys.stderr)
        except Exception as e:
            print(f"Ekstraklasa round {r}: ERROR {e}", file=sys.stderr)
        time.sleep(0.5)
    return allm

def fetch_1liga():
    allm = []
    for r in range(1, ROUNDS + 1):
        url = f"https://www.thesportsdb.com/api/v1/json/123/eventsround.php?id=4661&r={r}&s={SEASON}"
        try:
            ev = requests.get(url, headers=UA, timeout=20).json().get("events") or []
        except Exception as e:
            print(f"1. Liga round {r}: ERROR {e}", file=sys.stderr); ev = []
        for e in ev:
            ts, t = e.get("strTimestamp"), e.get("strTime")
            kickoff, confirmed = None, False
            if ts and t and t not in ("00:00:00",):
                kickoff = dt.datetime.fromisoformat(ts).replace(tzinfo=dt.timezone.utc).astimezone(WAW).isoformat()
                confirmed = True
            fin = e.get("strStatus") in ("FT", "AET", "PEN", "Match Finished")
            hs, as_ = e.get("intHomeScore"), e.get("intAwayScore")
            allm.append({
                "id": "1l-" + str(e["idEvent"]), "league": "1. Liga", "round": r,
                "home": e["strHomeTeam"], "away": e["strAwayTeam"],
                "date": (kickoff or "")[:10] or e.get("dateEvent"), "kickoff": kickoff,
                "time_confirmed": confirmed, "venue": e.get("strVenue") or None,
                "finished": fin, "score": f"{hs}–{as_}" if fin and hs is not None else None,
                "ticket_url": None,
                "source_url": f"https://www.thesportsdb.com/event/{e['idEvent']}",
            })
        print(f"1. Liga round {r}: {len(ev)} matches", file=sys.stderr)
        time.sleep(1.2)  # be gentle with the free tier
    return allm

if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    now = dt.datetime.now(WAW).isoformat(timespec="minutes")
    ek = fetch_ekstraklasa()
    if ek:
        json.dump({"fetched": now, "source": "ekstraklasa.org (official)", "matches": ek},
                  open(DATA / "fixtures_ekstraklasa.json", "w"), ensure_ascii=False, indent=1)
    l1 = fetch_1liga()
    if l1:
        json.dump({"fetched": now, "source": "TheSportsDB (community data, free test key)", "matches": l1},
                  open(DATA / "fixtures_1liga.json", "w"), ensure_ascii=False, indent=1)
    print(f"done: {len(ek)} Ekstraklasa, {len(l1)} 1. Liga", file=sys.stderr)
