"""Shared Lead record shape used by every scraper module."""
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone


@dataclass
class Lead:
    source: str            # 'propertyguru' | 'nuprop' | 'iproperty' | 'web_search'
    signal_type: str       # 'developer_listed_project' | 'keyword_match' | 'new_launch_unsold'
    project: str
    city: str = ''
    address: str = ''
    snippet: str = ''
    price: str = ''
    developer: str = ''
    url: str = ''
    scraped_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


def dedupe_leads(leads: list[Lead]) -> list[Lead]:
    """Dedupe by URL, merging signal_type when the same listing matches multiple signals."""
    by_url: dict[str, Lead] = {}
    for lead in leads:
        key = lead.url or f'{lead.source}:{lead.project}:{lead.city}'
        if key in by_url:
            existing = by_url[key]
            if lead.signal_type not in existing.signal_type.split('+'):
                existing.signal_type = existing.signal_type + '+' + lead.signal_type
        else:
            by_url[key] = lead
    return list(by_url.values())
