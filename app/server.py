import logging
from datetime import datetime, timezone

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, g

import log_buffer
import translations
from db import init_db, get_conn, get_setting, set_setting
from notifier import send_discord, send_telegram
from tweakers import validate_url
import monitor

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(name)s  %(message)s',
    datefmt='%H:%M:%S',
)
log_buffer.setup()
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = 'tw-monitor-change-me-in-production'


# ── i18n ──────────────────────────────────────────────────────────────────────
def _lang() -> str:
    if not hasattr(g, 'lang'):
        g.lang = get_setting('language', 'nl')
    return g.lang

def _t() -> dict:
    return translations.get(_lang())

@app.context_processor
def inject_i18n():
    return {'t': _t(), 'lang': _lang()}


# ── Template filters ──────────────────────────────────────────────────────────
@app.template_filter('time_ago')
def time_ago_filter(dt_str: str) -> str:
    t = _t()
    if not dt_str:
        return t['time_unknown']
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        diff = datetime.now(timezone.utc) - dt
        secs = int(diff.total_seconds())
        if secs < 60:
            return f'{secs}{t["time_sec"]}'
        if secs < 3600:
            return f'{secs // 60}{t["time_min"]}'
        if secs < 86400:
            return f'{secs // 3600}{t["time_hour"]}'
        return f'{secs // 86400}{t["time_day"]}'
    except Exception:
        return dt_str


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    with get_conn() as conn:
        items = conn.execute('''
            SELECT si.title, si.price, si.item_url, si.image_url,
                   si.city, si.seller, si.reserved, si.first_seen,
                   s.name AS search_name
            FROM seen_items si
            JOIN searches s ON si.search_id = s.id
            ORDER BY si.first_seen DESC
            LIMIT 60
        ''').fetchall()

        active_count = conn.execute(
            'SELECT COUNT(*) FROM searches WHERE active = 1'
        ).fetchone()[0]

        total_items = conn.execute('SELECT COUNT(*) FROM seen_items').fetchone()[0]

        today = datetime.now(timezone.utc).strftime('%Y-%m-%dT00:00:00Z')
        today_items = conn.execute(
            'SELECT COUNT(*) FROM seen_items WHERE first_seen >= ?', (today,)
        ).fetchone()[0]

    return render_template(
        'index.html',
        items=[dict(i) for i in items],
        active_count=active_count,
        total_items=total_items,
        today_items=today_items,
    )


@app.route('/searches')
def searches():
    with get_conn() as conn:
        rows = conn.execute('''
            SELECT s.*, COUNT(si.id) AS item_count
            FROM searches s
            LEFT JOIN seen_items si ON s.id = si.search_id
            GROUP BY s.id
            ORDER BY s.created_at DESC
        ''').fetchall()
    return render_template('searches.html', searches=[dict(r) for r in rows])


@app.route('/searches/add', methods=['POST'])
def add_search():
    t = _t()
    name = request.form.get('name', '').strip()
    url  = request.form.get('url',  '').strip()
    try:
        interval = max(1, int(request.form.get('interval', 5)))
    except ValueError:
        interval = 5

    keyword = request.form.get('keyword', '').strip()

    if not name or not url:
        flash(t['flash_name_url_required'], 'danger')
        return redirect(url_for('searches'))

    if not validate_url(url):
        flash(t['flash_invalid_url'], 'danger')
        return redirect(url_for('searches'))

    with get_conn() as conn:
        conn.execute(
            'INSERT INTO searches (name, url, keyword, interval_minutes, active) VALUES (?, ?, ?, ?, 1)',
            (name, url, keyword, interval),
        )

    flash(t['flash_search_added'].format(name), 'success')
    return redirect(url_for('searches'))


@app.route('/searches/<int:sid>/edit', methods=['POST'])
def edit_search(sid: int):
    t = _t()
    name    = request.form.get('name',    '').strip()
    keyword = request.form.get('keyword', '').strip()
    try:
        interval = max(1, int(request.form.get('interval', 5)))
    except ValueError:
        interval = 5

    if not name:
        flash(t['flash_name_required'], 'danger')
        return redirect(url_for('searches'))

    with get_conn() as conn:
        conn.execute(
            'UPDATE searches SET name = ?, keyword = ?, interval_minutes = ? WHERE id = ?',
            (name, keyword, interval, sid),
        )

    flash(t['flash_search_updated'], 'success')
    return redirect(url_for('searches'))


@app.route('/searches/<int:sid>/toggle', methods=['POST'])
def toggle_search(sid: int):
    with get_conn() as conn:
        row = conn.execute('SELECT active FROM searches WHERE id = ?', (sid,)).fetchone()
        if row:
            conn.execute('UPDATE searches SET active = ? WHERE id = ?', (1 - row['active'], sid))
    return redirect(url_for('searches'))


@app.route('/searches/<int:sid>/reset', methods=['POST'])
def reset_search(sid: int):
    with get_conn() as conn:
        conn.execute('DELETE FROM seen_items WHERE search_id = ?', (sid,))
    flash(_t()['flash_reset_done'], 'info')
    return redirect(url_for('searches'))


@app.route('/searches/<int:sid>/delete', methods=['POST'])
def delete_search(sid: int):
    with get_conn() as conn:
        conn.execute('DELETE FROM searches WHERE id = ?', (sid,))
    flash(_t()['flash_search_deleted'], 'success')
    return redirect(url_for('searches'))


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        set_setting('discord_webhook',  request.form.get('discord_webhook',  '').strip())
        set_setting('telegram_token',   request.form.get('telegram_token',   '').strip())
        set_setting('telegram_chat_id', request.form.get('telegram_chat_id', '').strip())
        flash(_t()['flash_settings_saved'], 'success')
        return redirect(url_for('settings'))

    return render_template(
        'settings.html',
        discord_webhook=get_setting('discord_webhook'),
        telegram_token=get_setting('telegram_token'),
        telegram_chat_id=get_setting('telegram_chat_id'),
        discord_enabled=get_setting('discord_enabled', '1') == '1',
        telegram_enabled=get_setting('telegram_enabled', '1') == '1',
    )


@app.route('/settings/toggle/<string:service>', methods=['POST'])
def toggle_notification(service: str):
    if service not in ('discord', 'telegram'):
        return redirect(url_for('settings'))
    t = _t()
    key = f'{service}_enabled'
    new_val = '0' if get_setting(key, '1') == '1' else '1'
    set_setting(key, new_val)
    label = 'Discord' if service == 'discord' else 'Telegram'
    msg_key = 'flash_notif_paused' if new_val == '0' else 'flash_notif_resumed'
    flash(t[msg_key].format(label), 'success')
    return redirect(url_for('settings'))


@app.route('/settings/language/<string:lang>', methods=['POST'])
def set_language(lang: str):
    if lang in ('nl', 'en'):
        set_setting('language', lang)
    return redirect(url_for('settings'))


# ── API ───────────────────────────────────────────────────────────────────────
@app.route('/api/logs')
def api_logs():
    return jsonify(log_buffer.get_recent())


@app.route('/api/test/discord', methods=['POST'])
def api_test_discord():
    t = _t()
    webhook = get_setting('discord_webhook')
    if not webhook:
        return jsonify({'error': t['api_no_discord']}), 400
    try:
        send_discord(webhook, [_test_item()], 'Test')
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/test/telegram', methods=['POST'])
def api_test_telegram():
    t = _t()
    token   = get_setting('telegram_token')
    chat_id = get_setting('telegram_chat_id')
    if not token or not chat_id:
        return jsonify({'error': t['api_no_telegram']}), 400
    try:
        send_telegram(token, chat_id, [_test_item()], 'Test')
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _test_item() -> dict:
    return {
        'title':     'Test advertentie — Tweakers Monitor',
        'price':     '€ 99,-',
        'url':       'https://tweakers.net/aanbod/',
        'image_url': None,
        'city':      'Amsterdam',
        'seller':    'testuser',
        'reserved':  False,
    }


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    monitor.start()
    logger.info('Web interface running on http://0.0.0.0:8000')
    app.run(host='0.0.0.0', port=8000, debug=False, use_reloader=False)
