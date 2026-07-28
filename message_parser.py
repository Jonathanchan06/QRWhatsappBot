from dataclasses import dataclass


@dataclass
class ParsedRequest:
    class_type: str
    name: str
    phone: str
    amount: float


def parse_request(body: str) -> ParsedRequest:
    """Parses a fixed-format request message: <classtype>-<name>-<phone>-<amount>

    e.g. "SG-JohnWong-91234567-15453" or "SG-JohnWong-91234567-15453.50"

    Raises ValueError with a user-facing message on malformed input.
    """
    parts = body.strip().split("-")
    if len(parts) != 4:
        raise ValueError(
            "Expected format: <classtype>-<name>-<phone>-<amount>\n\n"
            "e.g. SG-JohnWong-91234567-15453"
        )

    class_type, name, phone, amount_str = (p.strip() for p in parts)

    try:
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError
    except ValueError:
        raise ValueError(
            "The last part must be a valid amount (e.g. 15453 or 15453.50)."
        )

    return ParsedRequest(class_type=class_type, name=name, phone=phone, amount=amount)
