import re

_SPLIT_PATTERN = re.compile(r"[\s,;]+")


def parse_codes(raw: str) -> list[str]:
    """T-Nummern aus Freitext/CSV extrahieren: Split auf Whitespace/Komma/
    Semikolon, Uppercase, Dedup unter Beibehaltung der Eingabereihenfolge —
    analog parseCodes() im HTML-Prototyp."""
    seen: dict[str, None] = {}
    for part in _SPLIT_PATTERN.split(raw.strip()):
        code = part.strip().upper()
        if code:
            seen[code] = None
    return list(seen.keys())
