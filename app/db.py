import sqlite3
import logging
import os

DB_PATH = os.environ.get('DB_PATH', '/data/tweakers.db')
logger = logging.getLogger(__name__)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    return conn


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_conn() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS searches (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                name             TEXT    NOT NULL,
                url              TEXT    NOT NULL,
                keyword          TEXT    NOT NULL DEFAULT '',
                interval_minutes INTEGER NOT NULL DEFAULT 5,
                active           INTEGER NOT NULL DEFAULT 1,
                last_run         TEXT,
                created_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
            );

            CREATE TABLE IF NOT EXISTS seen_items (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id  INTEGER NOT NULL REFERENCES searches(id) ON DELETE CASCADE,
                item_id    TEXT    NOT NULL,
                title      TEXT,
                price      TEXT,
                item_url   TEXT,
                image_url  TEXT,
                city       TEXT,
                seller     TEXT,
                reserved   INTEGER NOT NULL DEFAULT 0,
                first_seen TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
                UNIQUE(search_id, item_id)
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
        ''')
        # Migrate: add keyword column if absent (idempotent)
        cols = [r[1] for r in conn.execute('PRAGMA table_info(searches)').fetchall()]
        if 'keyword' not in cols:
            conn.execute("ALTER TABLE searches ADD COLUMN keyword TEXT NOT NULL DEFAULT ''")
    logger.info('Database initialised at %s', DB_PATH)


def get_setting(key: str, default: str = '') -> str:
    with get_conn() as conn:
        row = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
    return row['value'] if row else default


def set_setting(key: str, value: str) -> None:
    with get_conn() as conn:
        conn.execute(
            'INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
            (key, value),
        )
