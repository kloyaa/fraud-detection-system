"""Structured logging configuration using structlog with JSON output.

All logs are emitted as JSON to stdout for production. Never use print() or
logging.info() — use the configured logger instead.

Per PCI DSS Requirement 3.3.1: Sensitive data (PAN, CVV, SSN) is masked
before logs are written via the mask_processor.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import FilteringBoundLogger

from app.config import settings
from app.core.log_masking import mask_processor


def setup_logging() -> None:
    """Configure structlog with JSON output to stdout.

    All logs are structured JSON for easy parsing in cloud environments.
    Development logs use pretty-printed format; production uses compact JSON.
    """
    # Structlog processors
    timestamper = structlog.processors.TimeStamper(fmt="iso")

    shared_processors = [
        structlog.stdlib.add_logger_name,
        timestamper,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        mask_processor,  # PCI DSS Req 3.3.1: Mask PAN, CVV, SSN before serialization
    ]

    if settings.environment == "production":
        # Production: compact JSON
        processors = shared_processors + [
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: pretty-printed format
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(),
        ]

    # Configure stdlib logging first (required for structlog.stdlib processors)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> FilteringBoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name, typically __name__

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)
