import hashlib
import hmac
import os


def password_hash(password, salt=None):
    salt = salt or os.urandom(16).hex()
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return salt + ':' + digest


def verify_manager(username, password):
    expected = os.getenv('PROMOTION_MANAGER_PASSWORD_HASH', '')
    configured_user = os.getenv('PROMOTION_MANAGER_USERNAME', '')
    if not expected or not configured_user or not hmac.compare_digest(username, configured_user):
        return False
    try:
        actual = password_hash(password, expected.split(':')[0])
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False
