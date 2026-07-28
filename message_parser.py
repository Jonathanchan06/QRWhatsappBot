import re
from dataclasses import dataclass

_AMOUNT_PATTERN = re.compile(r"=\s*\$?\s*([\d,]+(?:\.\d+)?)")


@dataclass
class ParsedRequest:
    class_type: str
    name: str
    phone: str
    amount: float


def parse_request(body: str) -> ParsedRequest:
    """Parses a fixed-format request message:

        <classtype>
        <name>
        <phone>
        <pricing/promo text>

    The amount charged is the value from the LAST "=$X" pattern found in the
    pricing text (e.g. a discount calculation ending in "...=$15453"), not
    necessarily the only number present.

    Raises ValueError with a user-facing message on malformed input.
    """
    lines = body.strip().splitlines()
    if len(lines) < 4:
        raise ValueError(
            "Expected format:\n<classtype>\n<name>\n<phone>\n<pricing message>\n\n"
            "e.g.\nSG\nJohnWong\n91234567\n...price details ending in =$15453..."
        )

    class_type = lines[0].strip()
    name = lines[1].strip()
    phone = lines[2].strip()
    pricing_text = "\n".join(lines[3:])

    matches = _AMOUNT_PATTERN.findall(pricing_text)
    if not matches:
        raise ValueError(
            "Couldn't find an amount in the pricing message — make sure it contains "
            "a calculation ending in \"=$X\" (e.g. \"...=$15453\")."
        )

    amount = float(matches[-1].replace(",", ""))
    return ParsedRequest(class_type=class_type, name=name, phone=phone, amount=amount)
