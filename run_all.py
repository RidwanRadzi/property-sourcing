"""
Orchestrates every scraper, dedupes the combined results, and writes
docs/data/leads.json -- the single file the GitHub Pages site (docs/index.html)
reads. Run from the project root: `python3 run_all.py`.
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common.models import dedupe_leads
from scrapers import propertyguru, nuprop, iproperty, web_search

OUT_PATH = Path(__file__).parent / 'docs' / 'data' / 'leads.json'


def main():
    all_leads = []

    print('\n=== PropertyGuru ===')
    pg_leads = propertyguru.scrape_all()
    print(f'PropertyGuru: {len(pg_leads)} leads')
    all_leads += pg_leads

    print('\n=== NuProp ===')
    np_leads = nuprop.scrape_all()
    print(f'NuProp: {len(np_leads)} leads')
    all_leads += np_leads

    print('\n=== iProperty ===')
    ip_leads = iproperty.scrape_all()
    print(f'iProperty: {len(ip_leads)} leads')
    all_leads += ip_leads

    print('\n=== Web search ===')
    ws_leads = web_search.scrape_all()
    print(f'Web search: {len(ws_leads)} leads')
    all_leads += ws_leads

    deduped = dedupe_leads(all_leads)
    deduped.sort(key=lambda l: (l.source, l.city, l.project))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'total': len(deduped),
        'by_source': {
            src: sum(1 for l in deduped if l.source == src)
            for src in sorted({l.source for l in deduped})
        },
        'leads': [l.to_dict() for l in deduped],
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    print(f'\n=== TOTAL: {len(all_leads)} raw -> {len(deduped)} deduped leads ===')
    for src, count in payload['by_source'].items():
        print(f'  {src}: {count}')
    print(f'Written to {OUT_PATH}')


if __name__ == '__main__':
    main()
