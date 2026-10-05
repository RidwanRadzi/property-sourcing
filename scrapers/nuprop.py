"""
NuProp scraper for 'unsold developer unit' leads.

NuProp (nuprop.my -- note: no 'www', that subdomain fails DNS) is a new-launch
marketing platform: every project listed on it is, by the site's own purpose,
a project still being actively sold by its developer. Each state page
(nuprop.my/<state>, paginated via ?offset=N&limit=10) is server-rendered HTML
with project cards under div.__property, so no API reverse-engineering was
needed -- confirmed live via curl_cffi impersonate='chrome124' (plain curl/
requests gets blocked or returns no useful markup on some paths; curl_cffi's
browser TLS fingerprint works).

Each card typically shows an explicit status badge ('Available', 'Sold Out',
etc) plus a 'From RM ...' starting price -- we skip anything explicitly
marked sold out and keep the rest as signal_type='new_launch_unsold'.
"""
import re
import time
from curl_cffi import requests as cffi_req
from bs4 import BeautifulSoup

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.models import Lead

BASE = 'https://nuprop.my'
STATES = [
    'johor', 'kedah', 'kelantan', 'kuala-lumpur', 'melaka', 'negeri-sembilan',
    'pahang', 'penang', 'perak', 'putrajaya', 'sarawak', 'selangor',
]
SOLD_OUT_MARKERS = ('sold out', 'fully sold')
PRICE_RE = re.compile(r'From RM\s*[\d,.]+\s*[KkMm]?')
POSTCODE_ADDR_RE = re.compile(r'[^|]*\b\d{5}\b[^|]*')


def _fetch_state_page(sess, state: str, offset: int):
    url = f'{BASE}/{state}' if offset == 0 else f'{BASE}/{state}?offset={offset}&limit=10'
    try:
        r = sess.get(url, timeout=20)
    except Exception as e:
        print(f'  [nuprop] fetch error: {e}')
        return None
    if r.status_code != 200:
        return None
    return r.text


def _parse_cards(html: str, state: str) -> list[Lead]:
    soup = BeautifulSoup(html, 'html.parser')
    leads = []
    for card in soup.select('div.__property'):
        for img in card.select('.__image'):
            img.decompose()  # strip base64 image blobs before extracting text
        title_el = card.select_one('h3')
        developer_el = card.select_one('.text-muted.font-weight-bold')
        link_el = card.select_one('a[href^="https://nuprop.my/"]')
        if not title_el or not link_el:
            continue
        text = card.get_text(' | ', strip=True)
        if any(marker in text.lower() for marker in SOLD_OUT_MARKERS):
            continue  # explicitly sold out -- not a lead
        price_m = PRICE_RE.search(text)
        addr_m = POSTCODE_ADDR_RE.search(text)
        leads.append(Lead(
            source='nuprop',
            signal_type='new_launch_unsold',
            project=title_el.get_text(strip=True),
            city=state.replace('-', ' ').title(),
            address=addr_m.group(0).strip(' |') if addr_m else '',
            snippet=text[:300],
            price=price_m.group(0) if price_m else '',
            developer=developer_el.get_text(strip=True) if developer_el else '',
            url=link_el['href'],
        ))
    return leads


def scrape_all(states=STATES, max_pages_per_state=3, delay=1.2) -> list[Lead]:
    sess = cffi_req.Session(impersonate='chrome124')
    leads = []
    for state in states:
        print(f'[nuprop] {state}')
        for page in range(max_pages_per_state):
            offset = page * 10
            html = _fetch_state_page(sess, state, offset)
            if html is None:
                break
            page_leads = _parse_cards(html, state)
            if not page_leads:
                break  # no more cards -- end of this state's listings
            leads.extend(page_leads)
            print(f'  offset {offset}: +{len(page_leads)} (running total {len(leads)})')
            time.sleep(delay)
    return leads


if __name__ == '__main__':
    results = scrape_all()
    print(f'\nTotal NuProp leads: {len(results)}')
