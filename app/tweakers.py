import re
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'nl-NL,nl;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}


def validate_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme in ('http', 'https') and 'tweakers.net' in p.netloc
    except Exception:
        return False


def _larger_thumb(url: str) -> str:
    """Swap the 84x63 thumbnail size for a larger 400x300 variant."""
    return re.sub(r'/\d+x\d+/', '/400x300/', url) if url else url


def fetch_listings(url: str) -> list[dict]:
    """Fetch and parse listings from a Tweakers V&A search page."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        logger.error('Failed to fetch %s: %s', url, e)
        return []

    soup = BeautifulSoup(r.text, 'lxml')
    table = soup.find('table', class_='valisting')
    if not table:
        logger.warning('No listing table found at %s', url)
        return []

    items = []
    seen: set[str] = set()

    for row in table.find_all('tr'):
        title_cell = row.find('p', class_='title')
        if not title_cell:
            continue

        link_tag = title_cell.find('a')
        if not link_tag:
            continue

        item_url = (link_tag.get('href') or '').strip()
        title = (link_tag.get('title') or link_tag.get_text(strip=True))

        m = re.search(r'/aanbod/(\d+)/', item_url)
        if not m:
            continue
        item_id = m.group(1)

        if item_id in seen:
            continue
        seen.add(item_id)

        # Price
        price_cell = row.find('td', class_='vaprice')
        price = ''
        if price_cell:
            price = price_cell.get_text(' ', strip=True)
            # strip duplicate whitespace
            price = re.sub(r'\s+', ' ', price).strip()

        # City
        city_cell = row.find('td', class_='city')
        city = ''
        if city_cell:
            p = city_cell.find('p')
            city = p.get_text(strip=True) if p else city_cell.get_text(strip=True)

        # Seller (gallery link)
        seller_link = row.find('a', href=re.compile(r'/gallery/\d+/aanbod/'))
        seller = ''
        if seller_link:
            seller = re.sub(r'\s*\(\d+\)\s*$', '', seller_link.get_text(strip=True))

        # Thumbnail — upgrade to larger size for notifications
        img_cell = row.find('td', class_='pwimage')
        image_url = ''
        if img_cell:
            img = img_cell.find('img')
            if img:
                image_url = _larger_thumb(img.get('src', ''))

        # Reserved status
        reserved = bool(
            img_cell and 'reserved' in img_cell.get('class', [])
        )

        items.append({
            'id': item_id,
            'title': title,
            'price': price,
            'url': item_url,
            'image_url': image_url,
            'city': city,
            'seller': seller,
            'reserved': reserved,
        })

    logger.info('Fetched %d items from %s', len(items), url)
    return items
