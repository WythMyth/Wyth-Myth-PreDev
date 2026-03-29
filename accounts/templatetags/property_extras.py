from decimal import Decimal, InvalidOperation
from django import template

register = template.Library()


@register.filter
def format_k(value):
    """
    15000 -> 15.00K
    15500 -> 15.50K
    150000 -> 150.00K
    """
    if value in (None, "", "None"):
        return "-"

    try:
        val = Decimal(str(value))
        return f"{(val / Decimal('1000')):.2f}K"
    except (InvalidOperation, ValueError, TypeError):
        return "-"