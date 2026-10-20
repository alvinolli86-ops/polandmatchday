"""Direct routes from Polish airports, parsed from English Wikipedia
"Airlines and destinations" sections (CC BY-SA 4.0). Link targets are mapped
to IATA codes with OurAirports (public domain). Wikipedia can be out of date,
so every route is 'unverified - check airline schedule'."""
import csv, json, re, sys, urllib.parse, urllib.request, datetime, os
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "AwayDayPrototype/0.1 (local research prototype)"}
PL = ["WAW","WMI","KRK","KTW","GDN","WRO","POZ","LCJ","RZE","SZZ","LUZ","BZG"]
SEASONAL = re.compile(r"(?i)'{3}\s*seasonal(?:\s*charter)?\s*:?\s*'{3}")
LINK = re.compile(r"\[\[([^\]|#]+)(?:\|[^\]]*)?\]\]")

def api(params):
    params = {**params, "format": "json", "formatversion": "2"}
    req = urllib.request.Request("https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params), headers=UA)
    return json.load(urllib.request.urlopen(req, timeout=30))

def norm(t): return urllib.parse.unquote(t).replace("_", " ").strip().lower()

def split_top(body):
    parts, depth, cur, i = [], 0, "", 0
    while i < len(body):
        two = body[i:i+2]
        if two in ("[[", "{{"): depth += 1; cur += two; i += 2; continue
        if two in ("]]", "}}"): depth -= 1; cur += two; i += 2; continue
        if body[i] == "|" and depth == 0: parts.append(cur); cur = ""; i += 1; continue
        cur += body[i]; i += 1
    parts.append(cur); return parts

def parse_cell(airline, cell):
    rows = []
    for i, part in enumerate(SEASONAL.split(cell)):
        charter = bool(re.search(r"(?i)'{3}\s*charter", part))
        for m in re.finditer(r"\[\[([^\]|#]+)(?:\|[^\]]*)?\]\]([^,\[]*)", part):
            note = m.group(2).strip(" ,;\n")
            rows.append({"airline": airline, "target": m.group(1).strip(), "seasonal": i > 0,
                         "charter": charter, "note": note if note.startswith("(") else ""})
    return rows

def parse_dest_list(w):
    w = re.sub(r"<!--.*?-->", "", w, flags=re.S)
    w = re.sub(r"<ref[^>]*/>", "", w); w = re.sub(r"<ref[^>]*>.*?</ref>", "", w, flags=re.S)
    rows = []
    for m in re.finditer(r"\{\{\s*Airport[- ]dest(?:ination)?[- ]list", w, re.I):
        body = w[m.end():]; depth, j = 1, 0
        while j < len(body) and depth:
            if body[j:j+2] == "{{": depth += 1; j += 2; continue
            if body[j:j+2] == "}}": depth -= 1; j += 2; continue
            j += 1
        items = [x.strip() for x in split_top(body[:j-2])][1:]
        items = [x for x in items if not re.match(r"^\w+\s*=", x)]
        for k in range(0, len(items) - 1, 2):
            al = LINK.search(items[k])
            if al: rows += parse_cell(al.group(1).strip(), items[k+1])
    if not rows:  # older wikitable layout
        for row in re.split(r"\n\|-", w):
            cells = [c for c in re.split(r"\n\||\|\|", row) if c.strip()]
            if len(cells) >= 2:
                al = LINK.search(cells[0])
                if al: rows += parse_cell(al.group(1).strip(), " ".join(cells[1:]))
    return rows

def section_wikitext(title):
    p = api({"action":"parse","page":title,"prop":"sections","redirects":1})["parse"]
    secs = p["sections"]
    pas = next((s["index"] for s in secs if s["line"].strip().lower() == "passenger"), None)
    idx = pas or next((s["index"] for s in secs if "airlines and destinations" in s["line"].lower()), None)
    if idx is None: return None, p["title"]
    w = api({"action":"parse","page":p["title"],"prop":"wikitext","section":idx})["parse"]["wikitext"]
    return re.split(r"(?im)^=+\s*cargo\s*=+", w)[0], p["title"]

airports, wiki2iata = {}, {}
for r in csv.DictReader(open(f"{BASE}/raw/ourairports.csv", encoding="utf-8")):
    if r["iata_code"] and r["type"] in ("large_airport","medium_airport","small_airport"):
        airports[r["iata_code"]] = r
        if r["wikipedia_link"]:
            wiki2iata[norm(r["wikipedia_link"].rsplit("/wiki/",1)[-1])] = r["iata_code"]

raw_rows, unresolved = {}, set()
for code in PL:
    title = urllib.parse.unquote(airports[code]["wikipedia_link"].rsplit("/wiki/",1)[-1]).replace("_", " ")
    w, real = section_wikitext(title)
    if not w: print(code, "no section", file=sys.stderr); continue
    rows = parse_dest_list(w)
    raw_rows[code] = (real, rows)
    unresolved |= {r["target"] for r in rows if norm(r["target"]) not in wiki2iata}

redir, ul = {}, sorted(unresolved)
for i in range(0, len(ul), 50):
    q = api({"action":"query","titles":"|".join(ul[i:i+50]),"redirects":1})["query"]
    nm = {x["from"]: x["to"] for x in q.get("normalized", [])}
    rr = {x["from"]: x["to"] for x in q.get("redirects", [])}
    for t in ul[i:i+50]:
        n = nm.get(t, t); redir[t] = rr.get(n, n)

# fallback: Wikidata IATA code (P238) for targets OurAirports doesn't link
wd = {}
left = [t for t in ul if norm(redir.get(t, t)) not in wiki2iata]
for i in range(0, len(left), 50):
    chunk = [redir.get(t, t) for t in left[i:i+50]]
    q = api({"action":"query","titles":"|".join(chunk),"prop":"pageprops","ppprop":"wikibase_item"})["query"]
    qids = {p["title"]: p.get("pageprops", {}).get("wikibase_item") for p in q["pages"]}
    ids = [x for x in qids.values() if x]
    if not ids: continue
    req = urllib.request.Request("https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(
        {"action":"wbgetentities","ids":"|".join(ids),"props":"claims","format":"json"}), headers=UA)
    ents = json.load(urllib.request.urlopen(req, timeout=30))["entities"]
    for title, qid in qids.items():
        try: code = ents[qid]["claims"]["P238"][0]["mainsnak"]["datavalue"]["value"]
        except Exception: continue
        if code in airports: wd[norm(title)] = code
for t in left:
    c = wd.get(norm(redir.get(t, t)))
    if c: wiki2iata[norm(t)] = c

out = {"generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
       "source": "English Wikipedia 'Airlines and destinations' sections (CC BY-SA 4.0) + OurAirports (public domain)",
       "caveat": "Community-edited; routes may be stale, seasonal, charter-only or not yet started. Verify on the airline site.",
       "airports": {}}
still = set()
for code, (real, rows) in raw_rows.items():
    dests = {}
    for r in rows:
        iata = wiki2iata.get(norm(r["target"])) or wiki2iata.get(norm(redir.get(r["target"], r["target"])))
        if not iata: still.add(r["target"]); continue
        if iata == code: continue
        d = dests.setdefault(iata, {"iata": iata, "name": airports[iata]["name"], "city": airports[iata]["municipality"],
              "country": airports[iata]["iso_country"], "airlines": [], "seasonal_only": True, "charter_only": True, "notes": []})
        if r["airline"] not in d["airlines"]: d["airlines"].append(r["airline"])
        if not r["seasonal"]: d["seasonal_only"] = False
        if not r["charter"]: d["charter_only"] = False
        if r["note"]: d["notes"].append(f'{r["airline"]} {r["note"]}')
    out["airports"][code] = {"wikipedia_page": real, "name": airports[code]["name"], "destinations": dict(sorted(dests.items()))}
    print(code, len(rows), "rows ->", len(dests), "destinations", file=sys.stderr)
out["unresolved_link_targets"] = sorted(still)
json.dump(out, open(f"{BASE}/data/routes_from_poland.json","w"), ensure_ascii=False, indent=1)
