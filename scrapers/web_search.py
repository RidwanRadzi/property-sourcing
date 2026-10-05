"""
Generic web-search scraper for 'unsold developer unit' leads.

Uses DuckDuckGo's no-JS HTML endpoint (html.duckduckgo.com/html/) -- no API
key needed, confirmed live via curl_cffi POST. Runs a handful of targeted
area+keyword queries and keeps results whose title or snippet contains one
of the developer-unit keywords, tagging the matched phrase. This is the
noisiest/lowest-precision source (news articles, aggregator sites, forum
threads can all show up) but it's the only path to developer-website mentions
that aren't on the three listing platforms.
"""
import time
from curl_cffi import requests as cffi_req
from bs4 import BeautifulSoup

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.models import Lead
from common.keywords import DEVELOPER_UNIT_KEYWORDS, text_matches_keyword

DDG_URL = 'https://html.duckduckgo.com/html/'
AREAS = ['Kuala Lumpur', 'Penang', 'Johor Bahru', 'Selangor', 'Negeri Sembilan']
QUERY_TEMPLATES = [
    '{area} developer unit for sale',
    '{area} developer unit for rent',
    '{area} unsold units developer',
]


def _search(sess, query: str) -> list[dict]:
    try:
        r = sess.post(DDG_URL, data={'q': query}, timeout=20)
    except Exception as e:
        print(f'  [web_search] fetch error: {e}')
        return []
    if r.status_code != 200:
        return []
    soup = BeautifulSoup(r.text, 'html.parser')
    out = []
    for result in soup.select('div.result'):
        title_el = result.select_one('a.result__a')
        snippet_el = result.select_one('a.result__snippet, div.result__snippet')
        if not title_el:
            continue
        out.append({
            'title': title_el.get_text(strip=True),
            'url': title_el.get('href', ''),
            'snippet': snippet_el.get_text(strip=True) if snippet_el else '',
        })
    return out


def scrape_all(areas=AREAS, templates=QUERY_TEMPLATES, delay=1.5) -> list[Lead]:
    sess = cffi_req.Session(impersonate='chrome124')
    leads = []
    seen_urls = set()
    for area in areas:
        for template in templates:
            query = template.format(area=area)
            print(f'[web_search] "{query}"')
            results = _search(sess, query)
            for r in results:
                matched_kw = text_matches_keyword(r['title']) or text_matches_keyword(r['snippet'])
                if not matched_kw:
                    continue
                if r['url'] in seen_urls:
                    continue
                seen_urls.add(r['url'])
                leads.append(Lead(
                    source='web_search',
                    signal_type='keyword_match',
                    project=r['title'],
                    city=area,
                    snippet=r['snippet'],
                    url=r['url'],
                ))
            print(f'  {len(results)} results, running total leads {len(leads)}')
            time.sleep(delay)
    return leads


if __name__ == '__main__':
    results = scrape_all()
    print(f'\nTotal web search leads: {len(results)}')
