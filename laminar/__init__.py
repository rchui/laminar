import logging.config

from laminar.components import Flow as Flow  # noqa
from laminar.components import Response as Response  # noqa

logging.config.dictConfig(
    {
        "version": 1,
        "formatters": {"laminar": {"format": "%(levelname)8s | %(message)s"}},
        "handlers": {
            "laminar": {
                "level": "INFO",
                "formatter": "laminar",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {"laminar": {"handlers": ["laminar"], "level": "INFO", "propagate": True}},
    }
)
