import decimal
from decimal import Decimal, ROUND_HALF_UP

# Set default context precision for financial math
decimal.getcontext().prec = 28


def to_decimal(value) -> Decimal:
    if value is None or value == "" or (isinstance(value, float) and str(value) == "nan"):
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    # Strip spaces and currency symbols if present
    s = str(value).strip().replace(",", "")
    if not s:
        return Decimal("0")
    try:
        return Decimal(s)
    except Exception:
        return Decimal("0")


def quantize_money(amount: Decimal, places: int = 2) -> Decimal:
    """Quantize decimal to fixed decimal places using ROUND_HALF_UP."""
    if amount is None:
        return Decimal("0")
    q = Decimal("10") ** (-places)
    return amount.quantize(q, rounding=ROUND_HALF_UP)


def format_money_for_plan(amount: Decimal) -> str:
    """Format decimal amount for payment plan strings.
    If amount is an exact integer, format as integer string (e.g. '25256').
    If amount has decimals, format to 2 decimal places (e.g. '15952906.67', '620.40').
    """
    if amount is None:
        return "0"
    q_amount = quantize_money(amount, 2)
    # Check if decimal part is zero
    if q_amount == q_amount.quantize(Decimal("1")):
        return str(int(q_amount))
    else:
        return f"{q_amount:.2f}"


def format_money_general(amount: Decimal) -> str:
    """Format decimal amount for output columns like amount_safe_to_pay."""
    if amount is None:
        return "0"
    q_amount = quantize_money(amount, 2)
    if q_amount == q_amount.quantize(Decimal("1")):
        return str(int(q_amount))
    # Remove trailing zeroes after decimal point if present, up to 2 decimal places
    s = f"{q_amount:.2f}".rstrip("0").rstrip(".")
    return s
