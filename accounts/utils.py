import os
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from itertools import zip_longest

from django.conf import settings
from django.utils.timezone import now
from PIL import Image, ImageDraw, ImageFont

from .models import PropertyContribution, Story


def format_currency(value):
    if value is None:
        return "0"
    return f"{value:,.0f}"  # 200000 -> 200,000


def create_story(message, date, property_instance=None):
    if date is None:
        return
    formatted_date = date.strftime("%d/%m/%Y")  # 4/1/2025
    full_message = f"{formatted_date} – {message}"
    Story.objects.create(message=full_message, related_property=property_instance)


def chunked(iterable, size):
    """
    Break an iterable into chunks of given size.
    Fills with None if last chunk is incomplete.
    """
    args = [iter(iterable)] * size
    return list(zip_longest(*args, fillvalue=None))


def calculate_user_investment_summary(user):
    if user.is_staff or user.is_superuser:
        return None

    today = now()
    month = today.month
    year = today.year

    # Get all contributions for the user
    all_contributions = PropertyContribution.objects.filter(user=user)
    monthly_contributions = all_contributions.filter(
        property__buying_date__month=month, property__buying_date__year=year
    )
    yearly_contributions = all_contributions.filter(property__buying_date__year=year)

    # Get all contributions (all users)
    all_contributions_all_users = PropertyContribution.objects.all()
    monthly_all_contributions = all_contributions_all_users.filter(
        property__buying_date__month=month, property__buying_date__year=year
    )
    yearly_all_contributions = all_contributions_all_users.filter(
        property__buying_date__year=year
    )

    # Initialize user and total values
    monthly_user_contribution = Decimal("0")
    monthly_user_profit = Decimal("0")
    yearly_user_contribution = Decimal("0")
    yearly_user_profit = Decimal("0")

    for c in monthly_contributions:
        monthly_user_contribution += c.contribution
        if c.property.selling_price:
            total_contributions = PropertyContribution.objects.filter(
                property=c.property
            )
            total_amount = sum(p.contribution for p in total_contributions) or Decimal(
                "1"
            )
            ratio = c.contribution / total_amount
            monthly_user_profit += c.property.selling_price * ratio

    for c in yearly_contributions:
        yearly_user_contribution += c.contribution
        if c.property.selling_price:
            total_contributions = PropertyContribution.objects.filter(
                property=c.property
            )
            total_amount = sum(p.contribution for p in total_contributions) or Decimal(
                "1"
            )
            ratio = c.contribution / total_amount
            yearly_user_profit += c.property.selling_price * ratio

    # Totals across all users
    monthly_total = sum(c.contribution for c in monthly_all_contributions) or Decimal(
        "0"
    )
    yearly_total = sum(c.contribution for c in yearly_all_contributions) or Decimal("0")

    # Total user balance across all contributions
    total_user_investment = sum(c.contribution for c in all_contributions)
    total_all_users_investment = sum(
        c.contribution for c in all_contributions_all_users
    ) or Decimal("1")

    return {
        # Monthly
        "monthly_total_investment": monthly_total,
        "monthly_contribution": monthly_user_contribution,
        "monthly_percentage": (
            (monthly_user_contribution / monthly_total * 100)
            if monthly_total > 0
            else Decimal("0")
        ),
        "monthly_profit": (monthly_user_profit-monthly_user_contribution),
        # Yearly
        "yearly_total_investment": yearly_total,
        "yearly_contribution": yearly_user_contribution,
        "yearly_percentage": (
            (yearly_user_contribution / yearly_total * 100)
            if yearly_total > 0
            else Decimal("0")
        ),
        "yearly_profit": (yearly_user_profit-yearly_user_contribution),
        # Overall
        "user_contribution": total_user_investment,
        "user_contribution_percentage": (
            total_user_investment / total_all_users_investment * 100
        ),
        # Time metadata
        "current_month_name": today.strftime("%B"),
        "current_year": year,
    }


def generate_stock_certificate_image(name, shares, date=None):
    # Load background image
    base_path = os.path.join(settings.BASE_DIR, "static", "assets", "images", "certificate.jpeg")
    image = Image.open(base_path).convert("RGB")
    draw = ImageDraw.Draw(image)

    # Load Acorn font
    font_path = os.path.join(settings.BASE_DIR, "static", "assets", "fonts", "Acorn-Regular.ttf")
    font_large = ImageFont.truetype(font_path, size=34)  # Name
    font_medium = ImageFont.truetype(font_path, size=26) # Shares
    font_small = ImageFont.truetype(font_path, size=22)  # Date

    # Current date fallback
    now = datetime.now()
    if not date:
        date = now

    # Draw text onto the certificate (adjust positions as needed)
    draw.text((660, 300), name, font=font_large, fill="black")         # Name
    draw.text((380, 370), str(shares), font=font_medium, fill="black") # Shares
    draw.text((500, 590), now.strftime("%d"), font=font_small, fill="black")  # Day
    draw.text((780, 590), now.strftime("%B"), font=font_small, fill="black")  # Month
    draw.text((1060, 590), now.strftime("%Y"), font=font_small, fill="black")  # Year

    # Save as PDF
    buffer = BytesIO()
    image.save(buffer, format="PDF")
    buffer.seek(0)
    return buffer