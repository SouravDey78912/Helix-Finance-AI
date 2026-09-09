"""
security/password.py
=====================
Password hashing and verification using bcrypt via passlib.

Production note: Same implementation works in production.
Consider adding pepper (app-level secret) for defence-in-depth.
"""

import bcrypt

def hash_password(plain_password: str) -> str:
    """Hash a plain-text password using bcrypt directly."""
    pwd_bytes = plain_password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash directly."""
    try:
        pwd_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False
