from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

# Load encryption key from environment variable
ENCRYPTION_KEY = (getattr(settings, 'ENCRYPTION_KEY', '') or '').strip()

if not ENCRYPTION_KEY:
    raise ImproperlyConfigured(
        "ENCRYPTION_KEY is not configured. Set it in Legalv1/legalenv before starting Django or Celery."
    )

fernet = Fernet(ENCRYPTION_KEY.encode())

def encrypt_data(data):
    """
    Encrypts the given data string using Fernet symmetric encryption.
    """
    return fernet.encrypt(data.encode()).decode()

def decrypt_data(token):
    """
    Decrypts the given token string using Fernet symmetric encryption.
    """
    return fernet.decrypt(token.encode()).decode()


def encrypt_field(value):
    """
    Encrypts a single MongoDB document field value for at-rest storage
    (Privacy Policy Section 7: "Encryption in transit (TLS 1.3) and at rest
    (AES-256)"). Falsy values (None, '') pass through unchanged — there's
    nothing sensitive to protect and it keeps empty-field checks working
    elsewhere in the codebase.
    """
    if not value:
        return value
    return fernet.encrypt(str(value).encode()).decode()


def decrypt_field(token):
    """
    Decrypts a single MongoDB document field value written by encrypt_field.

    Falls back to returning the value as-is if decryption fails — this is
    the intended behaviour during the migration window, when existing
    documents still hold plaintext content that was never encrypted. Once a
    backfill has run against a collection this fallback becomes dead code
    for that collection, but stays safe to keep.
    """
    if not token:
        return token
    try:
        return fernet.decrypt(str(token).encode()).decode()
    except Exception:
        return token


# from cryptography.fernet import Fernet
# import os
# import base64

# Ensure the encryption key is stored securely as an environment variable
# ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')

# if not ENCRYPTION_KEY:
#     raise ValueError("ENCRYPTION_KEY environment variable not set.")

# # Ensure the key is 32 url-safe base64-encoded bytes
# if len(ENCRYPTION_KEY) != 44:
#     # Generate a key if not correctly set (only for initial setup; in production, set via env variable)
#     ENCRYPTION_KEY = base64.urlsafe_b64encode(Fernet.generate_key())

# cipher_suite = Fernet(ENCRYPTION_KEY.encode())

# def encrypt_data(data: str) -> str:
#     return cipher_suite.encrypt(data.encode()).decode()

# def decrypt_data(token: str) -> str:
#     return cipher_suite.decrypt(token.encode()).decode()
