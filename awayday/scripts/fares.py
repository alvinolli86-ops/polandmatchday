"""Pluggable fare providers. No fares are ever invented: without a token or without cached
data a leg stays 'no recent fare' / 'pending'. The token is read from the environment and
never printed or written anywhere."""
import json, os, re, time, threading, urllib.parse, urllib.request, urllib.error, datetime as dt

def link_dates(link):
    """Local travel dates (ddmm) encoded in the Aviasales search path, e.g. /search/KRK2310STN25101."""
    m = re.match(r"/search/[A-Z]{3}(\d{4})[A-Z]{3}(\d{4})", link or "")
    return (m.group(1), m.group(2)) if m else None

class NoFareProvider:
    name = "none"
    def quote(self, origin, dest, depart, ret):
        return {"status": "pending_token", "price": None, "currency": None,
                "note": "Fare pending: Travelpayouts API token not set (TRAVELPAYOUTS_TOKEN)."}

class TravelpayoutsProvider:
    """Aviasales Data API v3 prices_for_dates: cheapest round trips for exact dates found by
    Aviasales users (cached, not live). Rate limit observed in headers: 600 req/min."""
    name = "travelpayouts"
    URL = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
    def __init__(self, token, currency="pln", market="pl", max_rps=6):
        self._t, self.currency, self.market = token, currency, market
        self._lock, self._last, self._gap = threading.Lock(), 0.0, 1.0 / max_rps
    def _throttle(self):
        with self._lock:
            wait = self._last + self._gap - time.time()
            if wait > 0: time.sleep(wait)
            self._last = time.time()
    def raw(self, origin, dest, depart, ret):
        q = {"origin": origin, "destination": dest, "departure_at": depart, "return_at": ret,
             "one_way": "false", "direct": "true", "sorting": "price", "currency": self.currency,
             "market": self.market, "limit": 30}
        for attempt in range(4):
            self._throttle()
            req = urllib.request.Request(self.URL + "?" + urllib.parse.urlencode(q), headers={"X-Access-Token": self._t})
            try:
                r = urllib.request.urlopen(req, timeout=25)
                rem = r.headers.get("X-Rate-Limit-Remaining")
                if rem is not None and int(rem) < 20: time.sleep(int(r.headers.get("X-Rate-Limit-Reset", "10")))
                return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code == 429: time.sleep(int(e.headers.get("X-Rate-Limit-Reset", "30")) + 1); continue
                return {"success": False, "error": f"HTTP {e.code}", "data": []}
            except Exception as e:
                err = type(e).__name__; time.sleep(3)
        return {"success": False, "error": f"network error ({err})", "data": []}
    def quote(self, origin, dest, depart, ret):
        d = self.raw(origin, dest, depart, ret)
        if not d.get("success", True) and d.get("error"):
            return {"status": "error", "price": None, "currency": None, "note": d["error"]}
        rows = [r for r in (d.get("data") or [])
                if r.get("origin_airport") == origin and r.get("destination_airport") == dest
                and r.get("transfers", 0) == 0 and r.get("return_transfers", 0) == 0
                and link_dates(r.get("link")) == (depart[8:10] + depart[5:7], ret[8:10] + ret[5:7])]
        if not rows:
            return {"status": "no_recent_fare", "price": None, "currency": None,
                    "note": "No cached direct fare for these exact dates."}
        r = min(rows, key=lambda r: r["price"])
        m = re.search(r"search_date=(\d{2})(\d{2})(\d{4})", r.get("link") or "")
        found = f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None
        return {"status": "cached", "price": r["price"], "currency": (d.get("currency") or self.currency).upper(),
                "airline": r.get("airline"), "flight_number": r.get("flight_number"),
                "departure_at": r.get("departure_at"), "return_at": r.get("return_at"),
                "duration_to": r.get("duration_to"), "found_on": found,
                "link": "https://www.aviasales.com" + r["link"] if r.get("link") else None,
                "note": "Cached fare found by Aviasales users, not live."}

def get_provider():
    tok = os.environ.get("TRAVELPAYOUTS_TOKEN")
    return TravelpayoutsProvider(tok) if tok else NoFareProvider()

def partner_marker():
    """Travelpayouts partner id (marker). Not a secret. The API token stays in the environment."""
    cfg = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config.json")
    try:
        return str(json.load(open(cfg))["affiliates"]["travelpayouts_marker"])
    except Exception:
        return "792630"

def with_marker(url):
    """Attach marker= to an Aviasales link.

    Travelpayouts documents the search-results path as
    https://www.aviasales.com/search/PARAMS and says an expanded affiliate
    link carries the partner id as the marker query parameter
    (https://support.travelpayouts.com/hc/en-us/articles/5711895629714 and
    https://support.travelpayouts.com/hc/en-us/articles/360027634052).
    The Data API returns a path plus its own query string and tells you to
    turn that into a partner link; we keep that URL and add marker=.
    """
    if not url:
        return url
    if url.startswith("/search/"):
        url = "https://www.aviasales.com" + url
    if "aviasales." not in url:
        return url
    if re.search(r"(?:[?&])marker=", url):
        return url
    return url + ("&" if "?" in url else "?") + "marker=" + partner_marker()

def search_link(origin, dest, depart, ret):
    """Aviasales search-results link for one adult, economy, plus the partner marker.

    PARAMS is ORIGIN + DDMM + DEST + DDMM + adult count, as documented for
    https://www.aviasales.com/search/PARAMS
    """
    d1 = dt.date.fromisoformat(str(depart)[:10])
    d2 = dt.date.fromisoformat(str(ret)[:10])
    path = f"{origin}{d1:%d%m}{dest}{d2:%d%m}1"
    return with_marker(f"https://www.aviasales.com/search/{path}")
