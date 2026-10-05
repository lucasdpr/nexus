import json
import logging
from datetime import UTC, datetime
from typing import Any

_STANDARD_ATTRS = frozenset(vars(logging.makeLogRecord({})))


class JsonFormatter(logging.Formatter):
    """Uma linha JSON por evento, pronta para agregadores de log.

    Campos passados em `extra=` entram no objeto; nunca registre conteúdo de documentos
    nem o texto de perguntas.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        payload.update({k: v for k, v in vars(record).items() if k not in _STANDARD_ATTRS})
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
