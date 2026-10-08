from cryptography.fernet import Fernet

def generate_user_key() -> str:
    """Generate a new encryption key for a user. Call this once during registration."""
    return Fernet.generate_key().decode()  # store this string in MongoDB

def encrypt_image(image_bytes: bytes, key: str) -> bytes:
    f = Fernet(key.encode())
    return f.encrypt(image_bytes)

def decrypt_image(encrypted_bytes: bytes, key: str) -> bytes:
    f = Fernet(key.encode())
    return f.decrypt(encrypted_bytes)