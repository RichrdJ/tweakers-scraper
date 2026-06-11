import logging
import threading
import time
from datetime import datetime, timezone

from db import get_conn, get_setting
from tweakers import fetch_listings
from notifier import send_discord, send_telegram

logger = logging.getLogger(__name__)
_stop_event = threading.Event()


def _store(search_id: int, items: list[dict]) -> list[dict]:
    """Insert new items; return only those that were genuinely new.
    On first run (no prior items) all items are seeded silently."""
    if not items:
        return []

    with get_conn() as conn:
        existing = conn.execute(
            'SELECT COUNT(*) FROM seen_items WHERE search_id = ?', (search_id,)
        ).fetchone()[0]

        new_items = []
        for item in items:
            try:
                conn.execute(
                    '''INSERT INTO seen_items
                       (search_id, item_id, title, price, item_url, image_url, city, seller, reserved)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (
                        search_id,
                        item['id'],
                        item['title'],
                        item['price'],
                        item['url'],
                        item['image_url'],
                        item['city'],
                        item['seller'],
                        1 if item.get('reserved') else 0,
                    ),
                )
                if existing > 0:
                    new_items.append(item)
            except Exception:
                pass  # UNIQUE constraint violation = already seen

    return new_items


def _notify(items: list[dict], search_name: str) -> None:
    if not items:
        return

    webhook = get_setting('discord_webhook')
    if webhook and get_setting('discord_enabled', '1') == '1':
        send_discord(webhook, items, search_name)

    token   = get_setting('telegram_token')
    chat_id = get_setting('telegram_chat_id')
    if token and chat_id and get_setting('telegram_enabled', '1') == '1':
        send_telegram(token, chat_id, items, search_name)


def _run_search(search: dict) -> None:
    sid  = search['id']
    name = search['name']
    url  = search['url']
    logger.info('Running search "%s" (%s)', name, url)

    items     = fetch_listings(url, search.get('keyword', ''))
    new_items = _store(sid, items)

    with get_conn() as conn:
        conn.execute(
            "UPDATE searches SET last_run = strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id = ?",
            (sid,),
        )

    if new_items:
        logger.info('%d new item(s) for "%s"', len(new_items), name)
        _notify(new_items, name)
    else:
        logger.debug('No new items for "%s"', name)


def _loop() -> None:
    # Track when each search last ran (monotonic seconds)
    last_run: dict[int, float] = {}

    while not _stop_event.is_set():
        with get_conn() as conn:
            searches = conn.execute(
                'SELECT * FROM searches WHERE active = 1'
            ).fetchall()

        now = time.monotonic()
        for row in searches:
            search = dict(row)
            sid      = search['id']
            interval = search['interval_minutes'] * 60
            if now - last_run.get(sid, 0) >= interval:
                last_run[sid] = now
                t = threading.Thread(target=_run_search, args=(search,), daemon=True)
                t.start()

        _stop_event.wait(30)


def start() -> None:
    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    logger.info('Monitor started')
