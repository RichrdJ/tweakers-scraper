import re
import logging
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

RSS_URL = 'https://tweakers.net/feeds/va.xml'

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'nl-NL,nl;q=0.9',
}


def validate_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme in ('http', 'https') and 'tweakers.net' in p.netloc
    except Exception:
        return False


def _parse_price(raw_title: str) -> str:
    """Extract price string from RSS title like 'A: Item naam - € 45,-'"""
    m = re.search(r'\s+[-–]\s+(€\s*[\d.,]+[-,]?|N\.o\.t\.k\.|Gratis|[A-Z][^\-–]*)$', raw_title)
    return m.group(1).strip() if m else ''


def _parse_title(raw_title: str) -> str:
    """Strip 'A: ' prefix and ' - price' suffix."""
    body = re.sub(r'^[AV]:\s*', '', raw_title.strip())
    body = re.sub(r'\s+[-–]\s+(€\s*[\d.,]+[-,]?|N\.o\.t\.k\.|Gratis|[A-Z][^\-–]*)$', '', body)
    return body.strip()


def _parse_item(el) -> dict | None:
    title_el = el.find('title')
    link_el  = el.find('link')
    desc_el  = el.find('description')
    cat_el   = el.find('category')
    guid_el  = el.find('guid')
    auth_el  = el.find('author')

    if title_el is None or link_el is None:
        return None

    raw = (title_el.text or '').strip()
    if not raw.startswith('A:'):    # skip 'V:' (Vraag) items
        return None

    link = (link_el.text or '').strip()
    guid = (guid_el.text if guid_el is not None else '') or link

    m = re.search(r'/aanbod/(\d+)', guid + link)
    if not m:
        return None

    return {
        'id':          m.group(1),
        'title':       _parse_title(raw),
        'price':       _parse_price(raw),
        'url':         link,
        'image_url':   '',
        'city':        '',
        'seller':      (auth_el.text or '').strip() if auth_el is not None else '',
        'reserved':    False,
        '_category':   (cat_el.text or '').strip()  if cat_el  is not None else '',
        '_desc':       (desc_el.text or '').strip() if desc_el is not None else '',
    }


def fetch_listings(url: str, keyword: str = '') -> list[dict]:
    """Fetch RSS feed and filter by keyword (space-separated terms, all must match)."""
    terms = [t.lower() for t in keyword.split() if t]

    try:
        r = requests.get(RSS_URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        logger.error('RSS fetch failed: %s', e)
        return []

    try:
        root = ET.fromstring(r.content)
    except Exception as e:
        logger.error('RSS parse failed: %s', e)
        return []

    items = []
    for el in root.findall('.//item'):
        item = _parse_item(el)
        if item is None:
            continue

        if terms:
            haystack = f"{item['title']} {item['_desc']} {item['_category']}".lower()
            if not all(t in haystack for t in terms):
                continue

        item.pop('_category', None)
        item.pop('_desc', None)
        items.append(item)

    logger.info('RSS: %d item(s) matched (keyword: "%s")', len(items), keyword or '*')
    return items
