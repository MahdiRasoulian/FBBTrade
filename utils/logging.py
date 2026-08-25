import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

_RESERVED = set(logging.LogRecord('', 0, '', 0, '', (), None).__dict__)

class ContextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        ctx = {k: v for k, v in record.__dict__.items() if k not in _RESERVED and not k.startswith('_')}
        if ctx:
            try:
                return f"{base} {json.dumps(ctx, default=str, sort_keys=True)}"
            except TypeError:
                return f"{base} {ctx}"
        return base

def configure_logging(level: str = 'INFO', log_file: str | None = None) -> None:
    """Configure console and persistent-file logging for runtime observability."""
    numeric = getattr(logging, str(level).upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(numeric)
    for handler in list(root.handlers):
        root.removeHandler(handler)
    fmt = ContextFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    console.setLevel(numeric)
    root.addHandler(console)
    path = Path(log_file or 'logs/fbbtrade.log')
    path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(path, maxBytes=5_000_000, backupCount=10, encoding='utf-8')
    file_handler.setFormatter(fmt)
    file_handler.setLevel(numeric)
    root.addHandler(file_handler)

def log_event(logger: logging.Logger, level: int, event: str, message: str, **context: Any) -> None:
    logger.log(level, message, extra={'event': event, **context})
