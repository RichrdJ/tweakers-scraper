import html
import logging
import requests

logger = logging.getLogger(__name__)

TW_COLOR = 0xe8770e   # Tweakers orange


def _discord_embed(item: dict, search_name: str) -> dict:
    embed = {
        'title': item['title'][:256],
        'url': item['url'],
        'color': TW_COLOR,
        'fields': [
            {'name': 'Prijs',        'value': item['price'] or 'Onbekend', 'inline': True},
            {'name': 'Locatie',      'value': item['city']  or 'Onbekend', 'inline': True},
            {'name': 'Verkoper',     'value': item['seller'] or 'Onbekend', 'inline': True},
            {'name': 'Zoekopdracht', 'value': search_name,                  'inline': False},
        ],
        'footer': {'text': 'Tweakers Monitor'},
    }
    if item.get('reserved'):
        embed['description'] = '⚠️ **Gereserveerd**'
    if item.get('image_url'):
        embed['thumbnail'] = {'url': item['image_url']}
    return embed


def send_discord(webhook_url: str, items: list[dict], search_name: str) -> None:
    for item in items:
        payload = {'embeds': [_discord_embed(item, search_name)]}
        try:
            r = requests.post(webhook_url, json=payload, timeout=10)
            r.raise_for_status()
        except Exception as e:
            logger.error('Discord notification failed for "%s": %s', item.get('title'), e)


def _tg_text(item: dict, search_name: str) -> str:
    title  = html.escape(item['title'])
    price  = html.escape(item['price']  or 'Onbekend')
    city   = html.escape(item['city']   or 'Onbekend')
    seller = html.escape(item['seller'] or 'Onbekend')
    sname  = html.escape(search_name)
    url    = item['url']
    reserved = ' ⚠️ <i>Gereserveerd</i>' if item.get('reserved') else ''
    return (
        f'🔔 <b>{sname}</b>{reserved}\n'
        f'<b>{title}</b>\n'
        f'💶 {price}\n'
        f'📍 {city}  ·  👤 {seller}\n'
        f'<a href="{url}">Bekijk advertentie</a>'
    )


def send_telegram(token: str, chat_id: str, items: list[dict], search_name: str) -> None:
    base = f'https://api.telegram.org/bot{token}'
    for item in items:
        text = _tg_text(item, search_name)
        image_url = item.get('image_url') or ''
        sent = False

        if image_url:
            try:
                r = requests.post(
                    f'{base}/sendPhoto',
                    json={'chat_id': chat_id, 'photo': image_url,
                          'caption': text, 'parse_mode': 'HTML'},
                    timeout=15,
                )
                r.raise_for_status()
                sent = True
            except Exception as e:
                logger.warning('sendPhoto failed, falling back to text: %s', e)

        if not sent:
            try:
                r = requests.post(
                    f'{base}/sendMessage',
                    json={'chat_id': chat_id, 'text': text,
                          'parse_mode': 'HTML', 'disable_web_page_preview': False},
                    timeout=10,
                )
                r.raise_for_status()
            except Exception as e:
                logger.error('Telegram notification failed for "%s": %s', item.get('title'), e)
