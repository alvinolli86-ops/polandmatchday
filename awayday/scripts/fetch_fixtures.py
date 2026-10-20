"""Upcoming fixtures for European leagues.
Primary: TheSportsDB v1 free test key '123' (eventsnextleague -> current round, eventsround -> full round, UTC timestamps).
Cross-check: openfootball/football.json (CC0/public domain; local kickoff times) where the league exists.
Nothing is invented: missing/placeholder times are flagged TBC, disagreements flagged."""
import json, os, sys, time, urllib.request, urllib.error, datetime as dt, unicodedata, re
from zoneinfo import ZoneInfo
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = "123"; PL = ZoneInfo("Europe/Warsaw")
LEAGUES = [  # (TheSportsDB id, name, country tz, openfootball code)
 (4328,"Premier League","Europe/London","en.1"), (4329,"Championship","Europe/London","en.2"),
 (4335,"La Liga","Europe/Madrid","es.1"), (4332,"Serie A","Europe/Rome","it.1"),
 (4331,"Bundesliga","Europe/Berlin","de.1"), (4399,"2. Bundesliga","Europe/Berlin",None),
 (4334,"Ligue 1","Europe/Paris","fr.1"), (4337,"Eredivisie","Europe/Amsterdam","nl.1"),
 (4344,"Primeira Liga","Europe/Lisbon","pt.1"), (4330,"Scottish Premiership","Europe/London",None),
 (4621,"Austrian Bundesliga","Europe/Vienna",None), (4631,"Czech First League","Europe/Prague",None),
 (4672,"Slovak First Football League","Europe/Bratislava",None),
 (4338,"Belgian Pro League","Europe/Brussels",None), (4675,"Swiss Super League","Europe/Zurich",None),
 (4340,"Danish Superliga","Europe/Copenhagen",None)]
SEASON = "2026-2027"

def get(url, tries=2):
    """One retry. A 429 must not burn the whole job; an incomplete run keeps the last file."""
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AwayDayPrototype/0.1"})
            return json.load(urllib.request.urlopen(req, timeout=30))
        except urllib.error.HTTPError as e:
            if i == tries - 1: raise
            time.sleep(8 if e.code == 429 else 3)
        except Exception:
            if i == tries - 1: raise
            time.sleep(3)

def key(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(fc|cf|afc|sc|ac|ssc|as|us|rc|cd|ud|sd|rcd|ca|club|de|calcio|football|1\.|fk|sk|bv|vfb|vfl|tsg|sv|1|04|05|1899|1909|1846|1907|1913)\b", " ", s)
    return re.sub(r"[^a-z]", "", s)

ALIAS = {"intermilan": "internazionalemilano"}

def crosscheck(m, ofb_matches, info):
    hk, ak = key(m["home"]), key(m["away"])
    def sim(a, b): return a == b or (min(len(a), len(b)) > 3 and (a in b or b in a))
    hk, ak = ALIAS.get(hk, hk), ALIAS.get(ak, ak)
    exact = [o for o in ofb_matches if hk == key(o["team1"]) and ak == key(o["team2"])]
    cand = exact or [o for o in ofb_matches if sim(hk, key(o["team1"])) and sim(ak, key(o["team2"]))]
    if not cand: return "not found in openfootball"
    d0 = dt.date.fromisoformat(m["date_local"])
    o = min(cand, key=lambda o: abs((dt.date.fromisoformat(o["date"]) - d0).days))
    info["crosschecked"] += 1
    gap = abs((dt.date.fromisoformat(o["date"]) - d0).days)
    if not o.get("time"):
        if gap <= 3: return "openfootball has only the nominal matchday date, no kickoff yet"
        info["conflicts"] += 1; return f"CONFLICT: openfootball has {o['date']} (no time)"
    if gap:
        info["conflicts"] += 1; return f"CONFLICT: openfootball has {o['date']} {o['time']}"
    if o["time"] != m["kickoff_local"][-5:]:
        info["conflicts"] += 1; return f"CONFLICT: openfootball time {o['time']} local"
    return "agrees (date+time)"

def recheck():
    """Re-run the openfootball cross-check on saved fixtures without refetching TheSportsDB."""
    out = json.load(open(f"{BASE}/data/fixtures.json"))
    for lid, lname, tz, ofb in LEAGUES:
        if not ofb: continue
        om = get(f"https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/{ofb}.json")["matches"]
        info = out["leagues"][lname]; info["crosschecked"] = info["conflicts"] = 0
        for m in out["matches"]:
            if m["league"] == lname: m["crosscheck"] = crosscheck(m, om, info)
        print(lname, info["crosschecked"], "checked,", info["conflicts"], "conflicts", file=sys.stderr)
    json.dump(out, open(f"{BASE}/data/fixtures.json", "w"), ensure_ascii=False, indent=1)

def window(today):
    # next two Fri-Mon weekends
    fri = today + dt.timedelta(days=(4 - today.weekday()) % 7)
    return [(fri + dt.timedelta(days=7*i), fri + dt.timedelta(days=7*i + 3)) for i in range(2)]

def main():
    today = dt.date.today()
    weekends = window(today); start, end = weekends[0][0], weekends[-1][1]
    out = {"generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "window": [str(start), str(end)], "weekends": [[str(a), str(b)] for a, b in weekends],
           "sources": {"primary": "TheSportsDB v1 free key 123", "crosscheck": "openfootball/football.json"},
           "leagues": {}, "matches": []}
    for lid, lname, tz, ofb in LEAGUES:
        info = {"thesportsdb_id": lid, "rounds_fetched": [], "matches": 0, "crosschecked": 0, "conflicts": 0, "errors": []}
        try:
            nxt = (get(f"https://www.thesportsdb.com/api/v1/json/{KEY}/eventsnextleague.php?id={lid}") or {}).get("events") or []
            r0 = int(nxt[0]["intRound"]) if nxt and nxt[0].get("intRound") else None
        except Exception as e:
            info["errors"].append(f"next: {e}"); r0 = None
        evs = []
        if r0:
            for r in range(r0, r0 + 16):
                time.sleep(2.2)  # free key ~30 req/min
                try:
                    e = (get(f"https://www.thesportsdb.com/api/v1/json/{KEY}/eventsround.php?id={lid}&r={r}&s={SEASON}") or {}).get("events") or []
                except Exception as ex:
                    info["errors"].append(f"round {r}: {ex}"); continue
                info["rounds_fetched"].append(r); evs += e
                if e and max(x["dateEvent"] for x in e) < str(start): continue
                if e and min(x["dateEvent"] for x in e) > str(end): break
        ofb_matches = []
        if ofb:
            try:
                d = get(f"https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/{ofb}.json")
                ofb_matches = d["matches"]
            except Exception as ex: info["errors"].append(f"openfootball: {ex}")
        seen = set()
        for e in evs:
            if e["idEvent"] in seen: continue
            seen.add(e["idEvent"])
            ts = e.get("strTimestamp")
            if not ts: continue
            utc = dt.datetime.fromisoformat(ts).replace(tzinfo=dt.timezone.utc)
            local = utc.astimezone(ZoneInfo(tz)); pl = utc.astimezone(PL)
            if not (str(start) <= str(local.date()) <= str(end)): continue
            status = e.get("strStatus") or ""
            flags = []
            if (e.get("strPostponed") or "no").lower() != "no" or status in ("PST", "Postponed", "CANC"): flags.append("postponed/cancelled")
            if utc.time() == dt.time(0, 0): flags.append("kickoff time TBC (00:00 placeholder)")
            m = {"league": lname, "home": e["strHomeTeam"], "away": e["strAwayTeam"], "venue": e.get("strVenue"),
                 "kickoff_utc": utc.isoformat(), "kickoff_local": local.strftime("%a %d %b %H:%M"), "kickoff_pl": pl.strftime("%a %d %b %H:%M"),
                 "date_local": str(local.date()), "round": e.get("intRound"), "thesportsdb_event": e["idEvent"], "flags": flags, "crosscheck": None}
            if ofb_matches:
                m["crosscheck"] = crosscheck(m, ofb_matches, info)
            out["matches"].append(m); info["matches"] += 1
        out["leagues"][lname] = info
        print(lname, info, file=sys.stderr)
    out["matches"].sort(key=lambda m: m["kickoff_utc"])
    path = f"{BASE}/data/fixtures.json"
    if os.path.exists(path):
        prev = json.load(open(path))
        dropped = []
        for name, info in out["leagues"].items():
            old_n = ((prev.get("leagues") or {}).get(name) or {}).get("matches") or 0
            if info["errors"] and info["matches"] < old_n:
                dropped.append(f"{name} {info['matches']}/{old_n}")
        prev_n = len(prev.get("matches") or [])
        if dropped or (prev_n and len(out["matches"]) < 0.6 * prev_n and any(i["errors"] for i in out["leagues"].values())):
            print("incomplete TheSportsDB fetch; keeping last committed fixtures:", "; ".join(dropped) or f"{len(out['matches'])}/{prev_n}", file=sys.stderr)
            sys.exit(1)
    tmp = path + ".tmp"
    json.dump(out, open(tmp, "w"), ensure_ascii=False, indent=1)
    os.replace(tmp, path)

if __name__ == "__main__":
    recheck() if "--recheck" in sys.argv else main()
