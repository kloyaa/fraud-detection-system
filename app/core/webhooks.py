"""Webhook HMAC signing and verification — Stripe-style (RFC 2104).

Per @priya: Webhook payloads must be signed with HMAC-SHA256 to prevent
tampering. The signature includes a timestamp to prevent replay attacks.

Pattern (Stripe-style):
  Signature: t=1234567890.v1=abcdef123456...
  - t: Unix timestamp (verified to be within 300s of current time)
  - v1: HMAC-SHA256 of "{timestamp}.{body}" using webhook secret key

Usage:
  # Signing (backend → webhook service)
  signature = sign_webhook("your-secret", body)
  # Send as: X-Webhook-Signature: {signature}

  # Verifying (webhook receiver)
  is_valid = verify_webhook("your-secret", body, signature)
"""

import hashlib
import hmac
import time
from typing import Tuple


def sign_webhook(secret: str, body: bytes) -> str:
    """Sign a webhook payload with HMAC-SHA256.

    Args:
        secret: Shared webhook secret (must be ≥32 bytes in production)
        body: Raw request body (bytes)

    Returns:
        Signature string in format: t=<timestamp>.v1=<hmac>
    """
    timestamp = str(int(time.time()))
    signed_content = f"{timestamp}.{body.decode('utf-8')}"

    # HMAC-SHA256 using constant-time comparison (hmac.compare_digest)
    signature = hmac.new(
        secret.encode("utf-8"),
        signed_content.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return f"t={timestamp}.v1={signature}"


def verify_webhook(secret: str, body: bytes, signature: str, tolerance_s: int = 300) -> Tuple[bool, str]:
    """Verify webhook signature and timestamp.

    Protects against:
    - Tampering (HMAC validation)
    - Replay attacks (timestamp validation within 300s window)
    - Signature stripping (explicit version check v1)

    Args:
        secret: Shared webhook secret
        body: Raw request body (bytes)
        signature: Signature from X-Webhook-Signature header
        tolerance_s: Max age of timestamp in seconds (default 300s / 5 min)

    Returns:
        (is_valid, reason) tuple — (False, "reason") if verification fails
    """
    # Parse signature
    parts = signature.split(".")
    if len(parts) != 2 or not parts[0].startswith("t=") or not parts[1].startswith("v1="):
        return False, "Invalid signature format"

    try:
        timestamp_str = parts[0][2:]  # Remove "t="
        received_signature = parts[1][3:]  # Remove "v1="
        timestamp = int(timestamp_str)
    except ValueError:
        return False, "Invalid timestamp format"

    # Validate timestamp (prevent replay attacks)
    now = int(time.time())
    if abs(now - timestamp) > tolerance_s:
        return False, f"Timestamp outside tolerance window ({abs(now - timestamp)}s > {tolerance_s}s)"

    # Reconstruct expected signature
    signed_content = f"{timestamp_str}.{body.decode('utf-8')}"
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        signed_content.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    # Compare with constant-time comparison (prevents timing attacks)
    if not hmac.compare_digest(received_signature, expected_signature):
        return False, "Signature mismatch"

    return True, "OK"


def extract_webhook_signature(authorization_header: str) -> str:
    """Extract signature from X-Webhook-Signature header.

    Args:
        authorization_header: Value of X-Webhook-Signature header

    Returns:
        Signature string (e.g., "t=1234567890.v1=abcdef...")
    """
    return authorization_header.strip()
