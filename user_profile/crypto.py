"""
Field-Level Encryption for Sensitive Profile Data
==================================================
AES-256-GCM encryption for ID number and contact number at rest.
The 256-bit key is read from PROFILE_ENCRYPTION_KEY (64 hex chars) in .env.

Encrypted values are stored as: enc:base64(nonce || ciphertext+tag)
The 'enc:' prefix lets us distinguish encrypted values from legacy plaintext.
"""

import base64
import logging
import os

logger = logging.getLogger(__name__)

_key = None
_key_init_attempted = False


def _get_key():
    """Lazily load the key so PROFILE_ENCRYPTION_KEY is read after dotenv loads."""
    global _key, _key_init_attempted
    if not _key_init_attempted:
        _key_init_attempted = True
        hex_key = os.environ.get('PROFILE_ENCRYPTION_KEY', '')
        try:
            candidate = bytes.fromhex(hex_key)
            if len(candidate) == 32:
                _key = candidate
            else:
                logger.warning('PROFILE_ENCRYPTION_KEY must be 32 bytes (64 hex chars)')
        except ValueError:
            logger.warning('PROFILE_ENCRYPTION_KEY is not valid hex; sensitive fields stored unencrypted')
    return _key


def encrypt_field(value):
    """Encrypt a string field. Empty values and missing key pass through unchanged."""
    if not value or not isinstance(value, str):
        return value
    key = _get_key()
    if key is None:
        return value
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, value.encode('utf-8'), None)
    return 'enc:' + base64.b64encode(nonce + ciphertext).decode('ascii')


def decrypt_field(value):
    """Decrypt a value produced by encrypt_field. Plaintext/legacy values pass through."""
    if not value or not isinstance(value, str) or not value.startswith('enc:'):
        return value
    key = _get_key()
    if key is None:
        return value
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        raw = base64.b64decode(value[4:])
        return AESGCM(key).decrypt(raw[:12], raw[12:], None).decode('utf-8')
    except Exception as e:  # noqa: BLE001
        logger.warning(f'Failed to decrypt profile field: {e}')
        return value
