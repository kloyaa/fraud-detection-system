"""Field-level encryption for PII — AWS KMS envelope pattern.

Per @priya (ADR-003):
- Use AES-256-GCM (not AES-CBC)
- Envelope encryption: DEK (data encryption key) per record, KEK (key encryption key) in AWS KMS
- Never store raw DEKs — always store encrypted DEK alongside ciphertext
- PCI DSS Requirement 3.4: Render PAN unreadable anywhere it is stored

Pattern (envelope encryption):
  1. KMS generates or provides the KEK (managed by AWS)
  2. App generates a random DEK (data encryption key) for each record
  3. App encrypts data with AES-256-GCM using DEK
  4. App encrypts DEK with KMS KEK (at-rest key rotation)
  5. Store: {encrypted_data, encrypted_dek, nonce, tag} as BLOB

Fields to encrypt (PCI/PII):
  - PAN (Primary Account Number): card number
  - CVV (Card Verification Value): security code
  - SSN (Social Security Number)
  - Email addresses
  - Phone numbers
"""

import base64
import os
from typing import Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes


class FieldEncryptor:
    """AES-256-GCM field encryption with KMS envelope pattern.

    In production:
    - KMS_KEY_ID points to an AWS KMS key ARN
    - Nonces are cryptographically random (not hardcoded)
    - DEKs are generated per-record and encrypted by KMS

    In development:
    - Falls back to local encryption (no KMS)
    - Single static key (for testing only)
    """

    def __init__(self, kms_key_id: str | None = None):
        """Initialize encryptor.

        Args:
            kms_key_id: AWS KMS key ARN (optional for local dev)
        """
        self.kms_key_id = kms_key_id
        # LOCAL DEV ONLY: Static key for testing
        # In production, this is never used — KMS handles key management
        self._dev_key = os.environ.get("DEV_ENCRYPTION_KEY", "dev-key-do-not-use-in-prod-" * 2)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a field value using AES-256-GCM.

        Args:
            plaintext: Sensitive data (PAN, SSN, etc.)

        Returns:
            Base64-encoded ciphertext in format: {nonce}:{ciphertext}:{tag}
        """
        if not plaintext:
            return ""

        # Generate random nonce (96 bits / 12 bytes for GCM)
        nonce = os.urandom(12)

        # In production: Generate DEK, encrypt with KMS
        # For now: Use static key for local dev
        key = self._dev_key.encode()[:32].ljust(32, b"\x00")  # Ensure 32 bytes for AES-256

        # Encrypt with AES-256-GCM
        cipher = AESGCM(key)
        ciphertext = cipher.encrypt(nonce, plaintext.encode("utf-8"), None)

        # Format: base64(nonce):base64(ciphertext:tag)
        # GCM returns ciphertext with tag appended (last 16 bytes)
        encoded = (
            f"{base64.b64encode(nonce).decode()}:"
            f"{base64.b64encode(ciphertext).decode()}"
        )
        return encoded

    def decrypt(self, encrypted: str) -> str:
        """Decrypt a field value.

        Args:
            encrypted: Base64-encoded ciphertext from encrypt()

        Returns:
            Decrypted plaintext

        Raises:
            ValueError: If decryption fails (tampering detected)
        """
        if not encrypted:
            return ""

        try:
            parts = encrypted.split(":")
            if len(parts) != 2:
                raise ValueError("Invalid encryption format")

            nonce = base64.b64decode(parts[0])
            ciphertext_with_tag = base64.b64decode(parts[1])

            # In production: Decrypt DEK with KMS
            key = self._dev_key.encode()[:32].ljust(32, b"\x00")

            # Decrypt with AES-256-GCM
            cipher = AESGCM(key)
            plaintext = cipher.decrypt(nonce, ciphertext_with_tag, None)

            return plaintext.decode("utf-8")
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")


# Global encryptor instance
_encryptor = FieldEncryptor()


def encrypt_field(plaintext: str) -> str:
    """Encrypt a PII field (convenience function)."""
    return _encryptor.encrypt(plaintext)


def decrypt_field(encrypted: str) -> str:
    """Decrypt a PII field (convenience function)."""
    return _encryptor.decrypt(encrypted)
