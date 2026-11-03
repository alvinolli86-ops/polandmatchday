"""LiveFootballTickets links via Awin.

Team paths are the ones linked from the live league pages on 3 Nov 2026
(https://www.livefootballtickets.com/us/{league}/{slug}-tickets.html).
Each of those URLs returned HTTP 200. A team that is not in this list uses
the league page. Event URLs are not guessed. Leagues LiveFootballTickets
does not sell, and leagues we were not asked to link, get no link.
Champions League fixtures are not in the feed; the league page is ready
if a trip is labelled Champions League.
"""
import html, json, os
from urllib.parse import quote

E = html.escape
BASE = "https://www.livefootballtickets.com"
# Advertiser 119227, publisher 3129214. Not a secret. Documented Awin deep link.
def awin_prefix():
    """Awin deep-link prefix. Ids live in config.json and are not secret."""
    cfg = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config.json")
    mid, affid = "119227", "3129214"
    try:
        aff = json.load(open(cfg)).get("affiliates") or {}
        mid = str(aff.get("awin_livefootballtickets_mid") or mid)
        affid = str(aff.get("awin_livefootballtickets_affid") or affid)
    except Exception:
        pass
    return f"https://www.awin1.com/cread.php?awinmid={mid}&awinaffid={affid}&ued="

LEAGUE_PAGES = {
    "Premier League": "/us/premier-league-tickets.html",
    "La Liga": "/us/la-liga-tickets.html",
    "Serie A": "/us/serie-a-tickets.html",
    "Champions League": "/us/champions-league-tickets.html",
}

# Home-club name as TheSportsDB spells it -> path seen on the league page.
TEAM_PAGES = {
    "Premier League": {
        "Arsenal": "/us/premier-league/arsenal-tickets.html",
        "Aston Villa": "/us/premier-league/aston-villa-tickets.html",
        "Bournemouth": "/us/premier-league/bournemouth-tickets.html",
        "Brentford": "/us/premier-league/brentford-tickets.html",
        "Brighton and Hove Albion": "/us/premier-league/brighton-and-hove-albion-tickets.html",
        "Chelsea": "/us/premier-league/fc-chelsea-tickets.html",
        "Coventry City": "/us/premier-league/coventry-city-tickets.html",
        "Crystal Palace": "/us/premier-league/crystal-palace-tickets.html",
        "Everton": "/us/premier-league/everton-tickets.html",
        "Fulham": "/us/premier-league/fulham-tickets.html",
        "Hull City": "/us/premier-league/hull-city-tickets.html",
        "Ipswich Town": "/us/premier-league/ipswich-town-tickets.html",
        "Leeds United": "/us/premier-league/leeds-united-tickets.html",
        "Liverpool": "/us/premier-league/liverpool-tickets.html",
        "Manchester City": "/us/premier-league/manchester-city-tickets.html",
        "Manchester United": "/us/premier-league/manchester-united-tickets.html",
        "Newcastle United": "/us/premier-league/newcastle-united-tickets.html",
        "Nottingham Forest": "/us/premier-league/nottingham-forest-tickets.html",
        "Sunderland": "/us/premier-league/sunderland-tickets.html",
        "Tottenham Hotspur": "/us/premier-league/tottenham-hotspur-tickets.html",
    },
    "La Liga": {
        "Deportivo Alavés": "/us/la-liga/alaves-tickets.html",
        "Athletic Bilbao": "/us/la-liga/athletic-de-bilbao-tickets.html",
        "Atlético Madrid": "/us/la-liga/atletico-madrid-tickets.html",
        "Celta Vigo": "/us/la-liga/celta-de-vigo-tickets.html",
        "Deportivo de A Coruña": "/us/la-liga/deportivo-la-coruna-tickets.html",
        "Elche": "/us/la-liga/elche-cf-tickets.html",
        "Espanyol": "/us/la-liga/espanyol-tickets.html",
        "Barcelona": "/us/la-liga/fc-barcelona-tickets.html",
        "Sevilla": "/us/la-liga/fc-sevilla-tickets.html",
        "Getafe": "/us/la-liga/getafe-tickets.html",
        "Levante": "/us/la-liga/levante-ud-tickets.html",
        "Osasuna": "/us/la-liga/osasuna-tickets.html",
        "Racing de Santander": "/us/la-liga/racing-santander-tickets.html",
        "Rayo Vallecano": "/us/la-liga/rayo-vallecano-tickets.html",
        "Real Betis": "/us/la-liga/real-betis-tickets.html",
        "Real Madrid": "/us/la-liga/real-madrid-tickets.html",
        "Real Sociedad": "/us/la-liga/real-sociedad-tickets.html",
        "Valencia": "/us/la-liga/valencia-tickets.html",
        "Villarreal": "/us/la-liga/villarreal-tickets.html",
    },
    "Serie A": {
        "AC Milan": "/us/serie-a/ac-milan-tickets.html",
        "Roma": "/us/serie-a/as-roma-tickets.html",
        "Atalanta": "/us/serie-a/atalanta-tickets.html",
        "Bologna": "/us/serie-a/bologna-tickets.html",
        "Cagliari": "/us/serie-a/cagliari-tickets.html",
        "Como": "/us/serie-a/como-tickets.html",
        "Fiorentina": "/us/serie-a/fiorentina-tickets.html",
        "Frosinone": "/us/serie-a/frosinone-tickets.html",
        "Genoa": "/us/serie-a/genoa-tickets.html",
        "Inter Milan": "/us/serie-a/inter-milan-tickets.html",
        "Juventus": "/us/serie-a/juventus-tickets.html",
        "Lazio": "/us/serie-a/lazio-tickets.html",
        "Lecce": "/us/serie-a/lecce-tickets.html",
        "Monza": "/us/serie-a/monza-tickets.html",
        "Napoli": "/us/serie-a/napoli-tickets.html",
        "Parma": "/us/serie-a/parma-tickets.html",
        "Sassuolo": "/us/serie-a/us-sassuolo-tickets.html",
        "Torino": "/us/serie-a/torino-tickets.html",
        "Udinese": "/us/serie-a/udinese-tickets.html",
        "Venezia": "/us/serie-a/venezia-tickets.html",
    },
}

def destination(league, home):
    """Most specific LiveFootballTickets page we have actually seen, or None."""
    if league not in LEAGUE_PAGES:
        return None
    path = TEAM_PAGES.get(league, {}).get(home) or LEAGUE_PAGES[league]
    return BASE + path

def awin_href(league, home):
    dest = destination(league, home)
    if not dest:
        return None
    return awin_prefix() + quote(dest, safe="")

def ticket_link(league, home):
    href = awin_href(league, home)
    if not href:
        return ""
    return (f'<a class="tickets" href="{E(href)}" target="_blank" rel="sponsored nofollow noopener">Match tickets</a>')
