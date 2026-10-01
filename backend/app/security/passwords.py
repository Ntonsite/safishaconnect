import os

import bcrypt

# 12 rounds in normal operation; the test-suite lowers this via BCRYPT_ROUNDS for speed.
_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=_ROUNDS)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


# Used to keep login timing similar whether or not the account exists.
DUMMY_HASH = hash_password("timing-equaliser-not-a-real-password")
