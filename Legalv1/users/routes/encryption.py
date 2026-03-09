from cryptography.fernet import Fernet
import os
import base64

# Load encryption key from environment variable
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')

if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY is not set in environment variables.")

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
