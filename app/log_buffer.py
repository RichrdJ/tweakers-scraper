import logging
from collections import deque
from datetime import datetime

_buffer: deque = deque(maxlen=500)


class _BufferHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        _buffer.append({
            'time':    datetime.fromtimestamp(record.created).strftime('%H:%M:%S'),
            'level':   record.levelname,
            'message': record.getMessage(),
        })


def setup() -> None:
    handler = _BufferHandler()
    handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(handler)


def get_recent(n: int = 150) -> list[dict]:
    entries = list(_buffer)
    return entries[-n:]
