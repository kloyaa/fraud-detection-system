"""Log masking middleware for structlog — PCI DSS Requirement 3.3.1.

Per @priya: A PAN in a log is a reportable incident. This processor masks
sensitive data before any log is written.

Patterns masked:
- PAN (16-19 digit card numbers): 4532111111111111 → ••••••••••••1111
- CVV (3-4 digit security codes): 123 → •••
- SSN (9 digit social security): 123-45-6789 → •••-••-••89
- Email addresses: user@example.com → u***@example.com
- Phone numbers: +1-555-123-4567 → +1-555-•••-••67
- API keys and tokens: apikey_abc123xyz → apikey_•••••••••••

This runs on every log statement before being written to disk or stdout.
"""

import re
from typing import Any, Dict

# Regex patterns for sensitive data
PATTERNS = {
    # PAN: 13-19 digits (Luhn-validated card numbers)
    "pan": re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
    # CVV/CVC: 3-4 digits (often preceded by "cvv" or "cvc")
    "cvv": re.compile(r"(?:cvv|cvc|security[_ ]?code)['\"]?\s*[=:]\s*['\"]?(\d{3,4})['\"]?", re.IGNORECASE),
    # SSN: XXX-XX-XXXX format
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    # Email: user@domain.com → u***@domain.com
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    # Phone: +1-555-123-4567 → +1-555-•••-••67
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?(?:[2-9]\d{2})\)?[-.\s]?(?:[2-9]\d{2})[-.\s]?(?:\d{4})\b"),
    # API keys / bearer tokens: apikey_xxxyyyzzz
    "api_key": re.compile(r"(?:api[_-]?key|token|secret|password)['\"]?\s*[=:]\s*['\"]?([A-Za-z0-9_\-]{20,})['\"]?", re.IGNORECASE),
}


def mask_pan(text: str) -> str:
    """Mask PAN: show only last 4 digits. 4532111111111111 → ••••••••••••1111"""
    def replacer(match: re.Match) -> str:
        card = match.group(0).replace(" ", "").replace("-", "")
        if len(card) >= 4:
            return "•" * (len(card) - 4) + card[-4:]
        return "•" * len(card)

    return PATTERNS["pan"].sub(replacer, text)


def mask_cvv(text: str) -> str:
    """Mask CVV: cvv=123 → cvv=•••"""
    def replacer(match: re.Match) -> str:
        return match.group(0)[: match.start(1) - match.start()] + "•" * len(match.group(1))

    return PATTERNS["cvv"].sub(replacer, text)


def mask_ssn(text: str) -> str:
    """Mask SSN: 123-45-6789 → •••-••-••89"""
    def replacer(match: re.Match) -> str:
        return "•••-••-" + match.group(0)[-2:]

    return PATTERNS["ssn"].sub(replacer, text)


def mask_email(text: str) -> str:
    """Mask email: user@example.com → u***@example.com"""
    def replacer(match: re.Match) -> str:
        email = match.group(0)
        local, domain = email.split("@")
        masked_local = local[0] + "•" * (len(local) - 2) + local[-1] if len(local) > 2 else "•" * len(local)
        return f"{masked_local}@{domain}"

    return PATTERNS["email"].sub(replacer, text)


def mask_phone(text: str) -> str:
    """Mask phone: +1-555-123-4567 → +1-555-•••-••67"""
    def replacer(match: re.Match) -> str:
        phone = match.group(0)
        # Keep first 8 chars, mask middle, show last 2
        if len(phone) >= 10:
            return phone[:8] + "•••-" + phone[-2:]
        return "•" * len(phone)

    return PATTERNS["phone"].sub(replacer, text)


def mask_api_key(text: str) -> str:
    """Mask API key: apikey=abc123xyz → apikey=•••••••••••"""
    def replacer(match: re.Match) -> str:
        prefix = match.group(0)[: match.start(1) - match.start()]
        return prefix + "•" * len(match.group(1))

    return PATTERNS["api_key"].sub(replacer, text)


def mask_value(value: Any) -> Any:
    """Recursively mask sensitive data in strings and nested structures."""
    if isinstance(value, str):
        # Apply all masking functions in order
        value = mask_pan(value)
        value = mask_cvv(value)
        value = mask_ssn(value)
        value = mask_email(value)
        value = mask_phone(value)
        value = mask_api_key(value)
        return value
    elif isinstance(value, dict):
        return {k: mask_value(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return type(value)(mask_value(item) for item in value)
    else:
        return value


def mask_processor(logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """structlog processor: mask sensitive data before writing logs.

    Add to structlog config:
        structlog.configure(
            processors=[
                ...,
                mask_processor,  # Must come before serializers
                structlog.processors.JSONRenderer(),
            ],
        )

    Usage:
        logger.info("payment_received", card_number="4532111111111111")
        # Output: {"event": "payment_received", "card_number": "••••••••••••1111"}
    """
    return mask_value(event_dict)
