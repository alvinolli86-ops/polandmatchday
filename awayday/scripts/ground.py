"""No-flight ground trips. Reads the hand-maintained route file and fixtures.json.
Does not invent times or fares."""
import json, os, html, datetime as dt
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
E = html.escape
MAX_MINUTES = 8 * 60

def load():
    path = os.path.join(BASE, "data", "ground_routes.json")
    return json.load(open(path)) if os.path.exists(path) else {"routes": [], "clubs": []}

def _minutes_label(route):
    label = route.get("typical_label")
    if label:
        return label
    mins = route.get("typical_minutes")
    if mins is None:
        return None
    h, m = divmod(int(mins), 60)
    return f"{h} h" if m == 0 else f"{h} h {m:02d} min"

def eligible(route):
    mins = route.get("typical_minutes")
    return route.get("direct") and mins is not None and 0 < int(mins) <= MAX_MINUTES

def ground_html(start, end):
    """Cards for one weekend (inclusive local dates). Empty string if nothing qualifies."""
    data = load()
    city_of = {c["team"]: c["city"] for c in data.get("clubs") or []}
    by_city = {}
    for r in data.get("routes") or []:
        if eligible(r):
            by_city.setdefault(r["to"], []).append(r)
    fx_path = os.path.join(BASE, "data", "fixtures.json")
    if not os.path.exists(fx_path):
        return ""
    matches = json.load(open(fx_path)).get("matches") or []
    cards = []
    for m in sorted(matches, key=lambda m: m.get("kickoff_utc") or ""):
        d = m.get("date_local") or ""
        if not (start <= d <= end):
            continue
        city = city_of.get(m.get("home"))
        routes = by_city.get(city) or []
        if not routes:
            continue
        routes = sorted(routes, key=lambda r: (r["typical_minutes"], r["from"]))
        items = ""
        for r in routes:
            ops = " · ".join(
                f'<a href="{E(o["url"])}" target="_blank" rel="noopener">{E(o["name"])}</a>'
                for o in r.get("operators") or [] if o.get("url"))
            mode = "train" if r.get("mode") == "train" else "bus"
            tail = "check the timetable" if r.get("operators_confirmed") is False else "see operator"
            items += (f'<li>by {mode} from {E(r["from"])}, {E(_minutes_label(r))}'
                      f'{(" · " + ops) if ops else ""} · {tail}</li>')
        venue = f' · {E(m["venue"])}' if m.get("venue") else ""
        cards.append(
            f'<div class="card"><div class="lg">{E(m.get("league") or "")}</div>'
            f'<h4>{E(m["home"])} v {E(m["away"])}</h4>'
            f'<p class="sm">{E(m.get("kickoff_pl") or m.get("date_local") or "")} Polish time{venue}</p>'
            f'<ul class="routes">{items}</ul></div>')
    if not cards:
        return ""
    return (f'<h3>No flight needed</h3>'
            f'<p class="sm">Direct train from a Polish city in about 8 hours or less. '
            f'The time is a typical published journey, not a departure you can book from this page, and it is not a fare.</p>'
            + "".join(cards))
