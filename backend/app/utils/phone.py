import re

_TZ_MOBILE = re.compile(r"^\+255[67]\d{8}$")


def normalise_tz_phone(raw: str) -> str:
    """Normalise Tanzanian mobile numbers to E.164 (+2557XXXXXXXX).

    Accepts ``0712 345 678``, ``712345678``, ``255712345678`` and ``+255 712 345 678``.
    Raises ``ValueError`` for anything that is not a Tanzanian mobile number.
    """
    digits = re.sub(r"[\s\-()]", "", raw or "")
    if digits.startswith("+"):
        candidate = digits
    elif digits.startswith("255"):
        candidate = "+" + digits
    elif digits.startswith("0"):
        candidate = "+255" + digits[1:]
    else:
        candidate = "+255" + digits
    if not _TZ_MOBILE.match(candidate):
        raise ValueError("Enter a valid Tanzanian mobile number, e.g. 0712 345 678")
    return candidate
