"""
iProperty scraper for 'unsold developer unit' leads.

iProperty.com.my and PropertyGuru.com.my are both owned by REA Group and run
the same underlying platform -- confirmed live: the same __NEXT_DATA__ shape,
the same isDeveloperListing/listerType/isDeveloperUnitListing fields, and the
same freetext-as-real-text-search behaviour. The only differences are the
base URL and path (`/sale/all-residential/` and `/rent/all-residential/`
instead of `/property-for-sale` and `/property-for-rent`, with a `?freetext=`
query param instead of PropertyGuru's `&freetext=` on top of listingType
params). A direct `/new-property-launches/` path 502s consistently (not a
rate-limit -- confirmed with 4 retries returning an identical-length error
page); the freetext search path works fine and is used instead.
"""
import re
import json
import time
from curl_cffi import requests as cffi_req

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.models import Lead
from common.keywords import DEVELOPER_UNIT_KEYWORDS

BASE = 'https://www.iproperty.com.my'
HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-MY,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
}
AREAS = ['Kuala Lumpur', 'Penang', 'Johor Bahru', 'Selangor', 'Negeri Sembilan']
LISTING_PATH = {'sale': 'sale', 'rent': 'rent'}


def _parse_next_data(html: str) -> dict | None:
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return None
    return json.loads(m.group(1))


def _fetch(sess, freetext: str, page: int, listing_type: str):
    path = LISTING_PATH[listing_type]
    url = f'{BASE}/{path}/all-residential/?freetext={freetext.replace(" ", "+")}&page={page}'
    try:
        r = sess.get(url, headers=HEADERS, timeout=30)
    except Exception as e:
        print(f'  [iproperty] fetch error: {e}')
        return None
    if r.status_code != 200:
        return None
    return _parse_next_data(r.text)


def _rows_from_data(data: dict) -> tuple[list[dict], int]:
    try:
        page_data = data['props']['pageProps']['pageData']['data']
    except (KeyError, TypeError):
        return [], 1
    listings = page_data.get('listingsData', [])
    out = [item['listingData'] for item in listings if item.get('listingData')]
    total_pages = page_data.get('paginationData', {}).get('totalPages', 1)
    return out, total_pages


def scrape_developer_listed_projects(areas=AREAS, listing_types=('sale', 'rent'),
                                      max_pages=5, delay=1.2) -> list[Lead]:
    sess = cffi_req.Session(impersonate='chrome124')
    leads = []
    for listing_type in listing_types:
        for area in areas:
            print(f'[iproperty/structured] {listing_type} / {area}')
            for page in range(1, max_pages + 1):
                data = _fetch(sess, area, page, listing_type)
                if data is None:
                    break
                rows, total_pages = _rows_from_data(data)
                if not rows:
                    break
                for d in rows:
                    if d.get('isDeveloperListing') or d.get('listerType') == 'developer':
                        price = (d.get('price') or {}).get('pretty', '')
                        leads.append(Lead(
                            source='iproperty',
                            signal_type='developer_listed_project',
                            project=d.get('localizedTitle', '').strip(),
                            city=area,
                            address=d.get('shortAddress', '').strip(),
                            price=price,
                            developer=d.get('developer', '') or '',
                            url=BASE + d['url'] if d.get('url', '').startswith('/') else d.get('url', ''),
                        ))
                print(f'  page {page}/{total_pages}: running total {len(leads)}')
                if page >= total_pages:
                    break
                time.sleep(delay)
    return leads


def scrape_keyword_matches(keywords=DEVELOPER_UNIT_KEYWORDS, listing_types=('sale', 'rent'),
                            max_pages=2, delay=1.2) -> list[Lead]:
    sess = cffi_req.Session(impersonate='chrome124')
    leads = []
    for listing_type in listing_types:
        for kw in keywords:
            print(f'[iproperty/keyword] {listing_type} / "{kw}"')
            for page in range(1, max_pages + 1):
                data = _fetch(sess, kw, page, listing_type)
                if data is None:
                    break
                rows, total_pages = _rows_from_data(data)
                if not rows:
                    break
                for d in rows:
                    title = d.get('localizedTitle', '')
                    if kw.lower() not in title.lower():
                        continue
                    price = (d.get('price') or {}).get('pretty', '')
                    leads.append(Lead(
                        source='iproperty',
                        signal_type='keyword_match',
                        project=title.strip(),
                        city=(d.get('shortAddress', '') or '').strip(),
                        address=d.get('shortAddress', '').strip(),
                        snippet=title.strip(),
                        price=price,
                        developer=d.get('developer', '') or '',
                        url=BASE + d['url'] if d.get('url', '').startswith('/') else d.get('url', ''),
                    ))
                print(f'  page {page}/{total_pages}: running total {len(leads)}')
                if page >= total_pages:
                    break
                time.sleep(delay)
    return leads


def scrape_all(max_pages_structured=5, max_pages_keyword=2, delay=1.2) -> list[Lead]:
    leads = scrape_developer_listed_projects(max_pages=max_pages_structured, delay=delay)
    leads += scrape_keyword_matches(max_pages=max_pages_keyword, delay=delay)
    return leads


if __name__ == '__main__':
    results = scrape_all()
    print(f'\nTotal iProperty leads: {len(results)}')
