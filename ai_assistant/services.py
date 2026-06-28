import json
import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db.models import Sum
from openai import OpenAI

from accounts.models import (
    Property,
    PropertyContribution,
    SharePrice,
    WithdrawalRequest,
)


# ============================================================
# OPENAI CLIENT
# ============================================================

def get_openai_client():
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


# ============================================================
# BASIC HELPERS
# ============================================================

def money(value):
    return str(
        Decimal(str(value or 0)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
    )


def money_decimal(value):
    return Decimal(str(value or 0)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def precise_decimal(value):
    return Decimal(str(value or 0)).quantize(
        Decimal("0.000001"),
        rounding=ROUND_HALF_UP,
    )


def get_running_statuses():
    return ["bought", "ready_to_sell", "rented", "rent", "stayed"]


def is_admin_or_finance(user):
    return user.is_superuser or getattr(user, "is_finnancial", False)


def get_property_acquisition_cost(property_obj):
    """
    Actual property cost.

    IMPORTANT:
    Always calculate buying_price + service_cost first.
    Stored acquisition_cost can be stale/old in DB.

    Priority:
    1. buying_price + service_cost
    2. property.acquisition_cost
    3. fallback: total contribution
    """

    buying_price = Decimal(str(getattr(property_obj, "buying_price", 0) or 0))
    service_cost = Decimal(str(getattr(property_obj, "service_cost", 0) or 0))

    calculated_cost = buying_price + service_cost

    if calculated_cost > 0:
        return calculated_cost

    acquisition_cost = Decimal(str(getattr(property_obj, "acquisition_cost", 0) or 0))

    if acquisition_cost > 0:
        return acquisition_cost

    total_contribution = PropertyContribution.objects.filter(
        property=property_obj,
        contribution__gt=0,
    ).aggregate(
        total=Sum("contribution")
    )["total"] or Decimal("0.00")

    return Decimal(str(total_contribution or 0))


# ============================================================
# LANGUAGE DETECTION
# ============================================================

def detect_language_style(text):
    """
    Detect user input style:
    - bangla: Bengali script
    - english: mostly English
    - banglish: roman Bangla / mixed
    """

    text = (text or "").strip().lower()

    if any("\u0980" <= ch <= "\u09FF" for ch in text):
        return "bangla"

    banglish_words = [
        "amar", "ami", "koto", "taka", "ache", "ase", "parbo",
        "korbo", "korte", "nite", "tulte", "bolen", "bolo",
        "kon", "kothay", "keno", "hoyeche", "hoy nai", "dekhte",
        "valo", "bhalo", "hoile", "korle", "dile", "pabe",
        "kotodin", "ato", "etto", "thik", "hobe", "kemon",
        "invest", "withdraw", "withdrow", "profit", "layer",
    ]

    english_words = [
        "what", "how", "where", "why", "can", "my", "balance",
        "total", "profit", "investment", "withdraw", "request",
        "pending", "status", "property", "sell", "sold", "selling",
        "price", "return", "scenario", "layer",
    ]

    banglish_score = sum(1 for w in banglish_words if w in text)
    english_score = sum(1 for w in english_words if w in text)

    if banglish_score > english_score:
        return "banglish"

    return "english"


# ============================================================
# USER FINANCE CONTEXT
# ============================================================

def get_user_running_invest(user):
    total = PropertyContribution.objects.filter(
        user=user,
        property__status__in=get_running_statuses(),
        property__is_contribution_locked=False,
        contribution__gt=0,
    ).aggregate(total=Sum("contribution"))["total"] or Decimal("0.00")

    return Decimal(str(total))


def get_user_final_profit(user):
    total = PropertyContribution.objects.filter(
        user=user,
        property__status="sold",
    ).aggregate(total=Sum("final_profit"))["total"] or Decimal("0.00")

    return Decimal(str(total))


def get_user_latest_withdrawal_requests(user):
    rows = WithdrawalRequest.objects.filter(
        user=user,
    ).order_by("-created_at")[:10]

    data = []

    for row in rows:
        data.append({
            "id": row.id,
            "amount": money(row.amount),
            "status": row.status,
            "note": row.note or "",
            "finance_note": row.finance_note or "",
            "clarification_note": getattr(row, "clarification_note", "") or "",
            "created_at": str(row.created_at),
            "approved_at": str(row.approved_at) if getattr(row, "approved_at", None) else None,
            "rejected_at": str(row.rejected_at) if getattr(row, "rejected_at", None) else None,
        })

    return data


def build_user_finance_context(user):
    current_balance = Decimal(str(user.balance or 0))
    running_invest = get_user_running_invest(user)
    final_profit = get_user_final_profit(user)
    total_request_limit = current_balance + running_invest

    running_rows = PropertyContribution.objects.filter(
        user=user,
        property__status__in=get_running_statuses(),
        property__is_contribution_locked=False,
        contribution__gt=0,
    ).select_related("property").order_by(
        "property__property_name",
        "investment_sequence",
        "id",
    )

    sold_profit_rows = PropertyContribution.objects.filter(
        user=user,
        property__status="sold",
    ).select_related("property").order_by(
        "-property__selling_date",
        "property__property_name",
        "investment_sequence",
        "id",
    )

    running_investments = []
    for row in running_rows:
        running_investments.append({
            "property_name": row.property.property_name,
            "property_status": row.property.status,
            "investment_sequence": row.investment_sequence,
            "contribution": money(row.contribution),
            "investment_date": str(row.investment_date) if row.investment_date else None,
            "shares": str(row.shares or "0"),
        })

    sold_profits = []
    for row in sold_profit_rows:
        sold_profits.append({
            "property_name": row.property.property_name,
            "investment_sequence": row.investment_sequence,
            "principal_returned": money(row.contribution),
            "gross_profit": money(row.profit),
            "deduction": money(row.deduction),
            "final_profit": money(row.final_profit),
            "selling_date": str(row.property.selling_date) if row.property.selling_date else None,
        })

    return {
        "user": {
            "id": user.id,
            "name": user.get_full_name(),
            "email": user.email,
        },
        "summary": {
            "current_balance": money(current_balance),
            "running_invest": money(running_invest),
            "final_profit": money(final_profit),
            "total_request_limit": money(total_request_limit),
        },
        "rules": {
            "ai_role": "read_only_suggestion_prediction_explanation",
            "ai_can_create_request": False,
            "ai_can_approve_request": False,
            "ai_can_reject_request": False,
            "ai_can_deduct_balance": False,
            "ai_can_update_database": False,
            "withdraw_request_limit": "current_balance + running_invest",
            "withdraw_approval_deducts_from": "current_balance only",
            "if_request_amount_more_than_current_balance": (
                "finance/admin must adjust running investment first before approval"
            ),
        },
        "running_investments": running_investments,
        "sold_property_profits": sold_profits,
        "withdrawal_requests": get_user_latest_withdrawal_requests(user),
    }


def get_recent_chat_messages(session, limit=12):
    messages = session.messages.order_by("-created_at")[:limit]
    messages = list(messages)
    messages.reverse()

    clean_messages = []

    for msg in messages:
        if msg.role in ["user", "assistant"]:
            clean_messages.append({
                "role": msg.role,
                "content": msg.content,
            })

    return clean_messages


# ============================================================
# FALLBACK ANSWERS
# ============================================================

def reply_text(style, key, data=None):
    data = data or {}

    messages = {
        "current_balance": {
            "bangla": f"আপনার current balance ${data['current_balance']}।",
            "english": f"Your current balance is ${data['current_balance']}.",
            "banglish": f"Apnar current balance ${data['current_balance']}.",
        },

        "total_balance": {
            "bangla": (
                f"আপনার total request limit ${data['total_request_limit']}। "
                f"এর মধ্যে current balance ${data['current_balance']} এবং running investment ${data['running_invest']}।"
            ),
            "english": (
                f"Your total available request limit is ${data['total_request_limit']}. "
                f"This includes your current balance of ${data['current_balance']} and your running investment of ${data['running_invest']}."
            ),
            "banglish": (
                f"Apnar total request limit ${data['total_request_limit']}. "
                f"Er moddhe current balance ${data['current_balance']} and running investment ${data['running_invest']}."
            ),
        },

        "withdraw": {
            "bangla": (
                f"আপনি maximum ${data['total_request_limit']} withdraw request করতে পারবেন। "
                f"কিন্তু approve হলে deduction হবে শুধু current balance ${data['current_balance']} থেকে।"
            ),
            "english": (
                f"You can request a maximum withdrawal of ${data['total_request_limit']}. "
                f"But when approved, the deduction will be made only from your current balance of ${data['current_balance']}."
            ),
            "banglish": (
                f"Apni maximum ${data['total_request_limit']} withdraw request korte parben. "
                f"Kintu approve hole deduction hobe sudhu current balance ${data['current_balance']} theke."
            ),
        },

        "profit": {
            "bangla": f"আপনার sold property final profit ${data['final_profit']}।",
            "english": f"Your sold property final profit is ${data['final_profit']}.",
            "banglish": f"Apnar sold property final profit ${data['final_profit']}.",
        },

        "no_running_invest": {
            "bangla": (
                f"আপনার current running investment ${data['running_invest']}। "
                "কোনো running property investment details পাওয়া যায়নি।"
            ),
            "english": (
                f"Your current running investment is ${data['running_invest']}. "
                "No running property investment details were found."
            ),
            "banglish": (
                f"Apnar current running investment ${data['running_invest']}. "
                "Kono running property investment details found hoy nai."
            ),
        },

        "no_request": {
            "bangla": "আপনার কোনো recent withdrawal request পাওয়া যায়নি।",
            "english": "No recent withdrawal request was found.",
            "banglish": "Apnar kono recent withdrawal request found hoy nai.",
        },

        "default": {
            "bangla": (
                f"Current balance ${data['current_balance']}, running investment ${data['running_invest']}, "
                f"final profit ${data['final_profit']}, total request limit ${data['total_request_limit']}।"
            ),
            "english": (
                f"Current balance ${data['current_balance']}, running investment ${data['running_invest']}, "
                f"final profit ${data['final_profit']}, total request limit ${data['total_request_limit']}."
            ),
            "banglish": (
                f"Current balance ${data['current_balance']}, running investment ${data['running_invest']}, "
                f"final profit ${data['final_profit']}, total request limit ${data['total_request_limit']}."
            ),
        },
    }

    return messages[key].get(style, messages[key]["english"])


def simple_fallback_answer(user, question):
    q = (question or "").lower().strip()
    style = detect_language_style(q)

    context = build_user_finance_context(user)
    summary = context["summary"]

    data = {
        "current_balance": summary["current_balance"],
        "running_invest": summary["running_invest"],
        "final_profit": summary["final_profit"],
        "total_request_limit": summary["total_request_limit"],
    }

    withdraw_keywords = [
        "withdraw", "withdrow", "withdrawal", "nite", "nibo", "tulte",
        "tulbo", "parbo", "নিতে", "তুলতে", "উইথড্র", "উত্তোলন",
    ]

    if any(word in q for word in withdraw_keywords):
        return reply_text(style, "withdraw", data)

    request_keywords = [
        "pending", "request status", "withdrawal status", "keno pending",
        "why pending", "পেন্ডিং", "রিকোয়েস্ট স্ট্যাটাস", "কেন পেন্ডিং",
    ]

    if any(word in q for word in request_keywords):
        requests = context.get("withdrawal_requests", [])

        if not requests:
            return reply_text(style, "no_request", data)

        latest = requests[0]

        if latest["status"] == "pending":
            if latest.get("clarification_note"):
                if style == "english":
                    return (
                        f"Your latest withdrawal request of ${latest['amount']} is still pending. "
                        f"Finance requested clarification: {latest['clarification_note']}"
                    )
                if style == "bangla":
                    return (
                        f"আপনার latest withdrawal request ${latest['amount']} এখনো pending। "
                        f"Finance clarification চেয়েছে: {latest['clarification_note']}"
                    )
                return (
                    f"Apnar latest withdrawal request ${latest['amount']} ekhono pending. "
                    f"Finance clarification chaiche: {latest['clarification_note']}"
                )

            if style == "english":
                return (
                    f"Your latest withdrawal request of ${latest['amount']} is still pending. "
                    "Finance will review it and then approve, reject, or request clarification."
                )
            if style == "bangla":
                return (
                    f"আপনার latest withdrawal request ${latest['amount']} এখনো pending। "
                    "Finance review করার পর approve/reject/update করবে।"
                )
            return (
                f"Apnar latest withdrawal request ${latest['amount']} ekhono pending. "
                "Finance review korar por approve/reject/update korbe."
            )

        if latest["status"] == "approved":
            if style == "english":
                return f"Your latest withdrawal request of ${latest['amount']} has been approved/paid."
            if style == "bangla":
                return f"আপনার latest withdrawal request ${latest['amount']} approved/paid হয়েছে।"
            return f"Apnar latest withdrawal request ${latest['amount']} approved/paid hoyeche."

        if latest["status"] == "rejected":
            reason = latest.get("finance_note") or "No reason provided."
            if style == "english":
                return f"Your latest withdrawal request of ${latest['amount']} was rejected. Reason: {reason}"
            if style == "bangla":
                return f"আপনার latest withdrawal request ${latest['amount']} rejected হয়েছে। Reason: {reason}"
            return f"Apnar latest withdrawal request ${latest['amount']} rejected hoyeche. Reason: {reason}"

    profit_keywords = [
        "profit", "final profit", "labh", "লাভ", "gain",
    ]

    if any(word in q for word in profit_keywords):
        return reply_text(style, "profit", data)

    invest_keywords = [
        "total invest", "running invest", "investment", "invest",
        "property te", "property", "বিনিয়োগ", "ইনভেস্ট", "প্রপার্টি",
    ]

    if any(word in q for word in invest_keywords):
        running = context.get("running_investments", [])

        if not running:
            return reply_text(style, "no_running_invest", data)

        if style == "english":
            lines = [f"Your current running investment is ${data['running_invest']}."]
        elif style == "bangla":
            lines = [f"আপনার current running investment ${data['running_invest']}।"]
        else:
            lines = [f"Apnar current running investment ${data['running_invest']}."]

        for item in running:
            lines.append(
                f"- {item['property_name']}: ${item['contribution']} ({item['property_status']})"
            )

        return "\n".join(lines)

    total_balance_keywords = [
        "total balance", "total request limit", "request limit",
        "total capacity", "total available", "total taka", "total amount",
        "সব মিলিয়ে", "মোট", "টোটাল",
    ]

    if any(word in q for word in total_balance_keywords):
        return reply_text(style, "total_balance", data)

    current_balance_keywords = [
        "current balance", "my balance", "balance", "amar balance",
        "taka ache", "money", "cash", "ব্যালেন্স", "টাকা",
    ]

    if any(word in q for word in current_balance_keywords):
        return reply_text(style, "current_balance", data)

    return reply_text(style, "default", data)


# ============================================================
# SUPERUSER PROPERTY SALE SIMULATOR - READ ONLY
# ============================================================

def parse_money_from_question(question, property_obj=None):
    """
    Extract selling price from question.
    It will not pick number inside property name like test1.
    """

    q = (question or "").replace(",", " ").strip()

    if property_obj and property_obj.property_name:
        q = re.sub(
            re.escape(property_obj.property_name),
            " ",
            q,
            flags=re.IGNORECASE,
        )

    pattern = r"(?<![A-Za-z0-9_])\$?\s*(\d+(?:\.\d+)?)\s*(?:dollar|usd|tk|taka|টাকা)?(?![A-Za-z0-9_])"

    matches = re.findall(pattern, q, flags=re.IGNORECASE)

    numbers = []

    for m in matches:
        try:
            value = Decimal(str(m))
            if value > 0:
                numbers.append(value)
        except Exception:
            pass

    if not numbers:
        return None

    return max(numbers)


def find_property_from_question(question):
    q = (question or "").lower().strip()

    properties = Property.objects.all().order_by("property_name")

    exact_match = None
    partial_match = None

    for prop in properties:
        name = (prop.property_name or "").lower().strip()

        if not name:
            continue

        if q == name:
            exact_match = prop
            break

        if name in q:
            partial_match = prop
            break

    return exact_match or partial_match


def question_wants_property_sale_simulation(question):
    q = (question or "").lower()

    property_words = [
        "property", "sold", "sell", "selling", "sale",
        "profit", "valo", "bhalo", "ভালো", "বিক্রি",
        "কত", "koto", "korle", "hoile", "pabe",
        "kotodin", "invest holo", "acquisition", "acquistion",
        "layer", "group", "deduction",
    ]

    return any(word in q for word in property_words)


def question_wants_best_selling_price(question):
    q = (question or "").lower()

    keywords = [
        "koto taka sold hoile valo",
        "koto sold korle valo",
        "koto price valo",
        "best price",
        "good price",
        "valo hobe",
        "bhalo hobe",
        "ভালো হবে",
        "কত টাকায়",
        "কত দামে",
        "suggest price",
        "selling price suggestion",
        "koto taka sold korle",
        "koto taka sell korle",
        "koto taka sale korle",
        "koto takay sold korle",
        "koto takay sell korle",
        "koto takay sale korle",
        "koto profit pabe",
        "kon user koto taka profit pabe",
        "kon user koto profit pabe",
        "kotodin invest holo",
        "ato din invest korle",
        "etto din invest korle",
        "profit pabe ta ki thik hobe",
        "profit valo kina",
        "profit bhalo kina",
        "fair profit",
        "reasonable profit",
    ]

    return any(k in q for k in keywords)


def simulate_property_sale(property_obj, selling_price=None, simulation_date=None):
    """
    READ-ONLY AI sale simulation.

    DB UPDATE KORE NA:
    - No save()
    - No balance update
    - No property update
    - No contribution update

    Business rules:
    - acquisition_cost = buying_price + service_cost
    - total_profit = selling_price - acquisition_cost
    - per layer/user profit share = layer contribution / acquisition_cost
    - deduction = layer gross profit * user's group percentage / 100
    """

    simulation_date = simulation_date or date.today()

    contributions = PropertyContribution.objects.filter(
        property=property_obj,
        contribution__gt=0,
    ).select_related(
        "user",
        "user__user_group",
        "property",
    ).order_by(
        "user_id",
        "investment_sequence",
        "investment_date",
        "id",
    )

    if not contributions.exists():
        return {
            "success": False,
            "message": "No active contribution found for this property.",
        }

    property_cost = get_property_acquisition_cost(property_obj)

    if property_cost <= 0:
        return {
            "success": False,
            "message": "Property acquisition cost is zero. Simulation not possible.",
        }

    if selling_price is None:
        if property_obj.selling_price and property_obj.selling_price > 0:
            selling_price = Decimal(str(property_obj.selling_price))
        else:
            selling_price = property_cost

    selling_price = money_decimal(selling_price)
    total_profit = money_decimal(selling_price - property_cost)

    contribution_total = contributions.aggregate(
        total=Sum("contribution")
    )["total"] or Decimal("0.00")
    contribution_total = Decimal(str(contribution_total or 0))

    share_price = Decimal(str(SharePrice.get_current_price() or 0))
    if share_price <= 0:
        share_price = Decimal("1.00")

    layer_rows = []
    user_summary = {}

    distributed_gross_profit = Decimal("0.00")
    distributed_loss = Decimal("0.00")
    total_deduction = Decimal("0.00")
    total_final_profit = Decimal("0.00")
    total_loss_amount = Decimal("0.00")

    contribution_list = list(contributions)
    total_rows = len(contribution_list)

    for index, contrib in enumerate(contribution_list):
        user = contrib.user
        contribution_amount = Decimal(str(contrib.contribution or 0))

        investment_date = (
            contrib.investment_date
            or property_obj.buying_date
            or simulation_date
        )

        invested_days = max(1, (simulation_date - investment_date).days)

        shares = (contribution_amount / share_price).quantize(
            Decimal("0.000001"),
            rounding=ROUND_HALF_UP,
        )

        if property_cost > 0:
            layer_ratio = (contribution_amount / property_cost).quantize(
                Decimal("0.000001"),
                rounding=ROUND_HALF_UP,
            )
        else:
            layer_ratio = Decimal("0.000000")

        gross_profit = Decimal("0.00")
        deduction_amount = Decimal("0.00")
        final_profit = Decimal("0.00")
        loss_amount = Decimal("0.00")

        group_name = "No Group"
        deduction_percentage = Decimal("0.00")

        if user.user_group:
            group_name = user.user_group.name or "Group"
            deduction_percentage = Decimal(str(user.user_group.percentage or 0))

        # Profit case
        if total_profit > 0:
            if index == total_rows - 1:
                gross_profit = money_decimal(total_profit - distributed_gross_profit)
            else:
                gross_profit = (
                    total_profit * layer_ratio
                ).quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP,
                )
                distributed_gross_profit += gross_profit

            # Deduction applies per layer based on user's own group percentage
            deduction_amount = (
                gross_profit * deduction_percentage / Decimal("100")
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )

            final_profit = (
                gross_profit - deduction_amount
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )

        # Loss case
        elif total_profit < 0:
            total_loss = abs(total_profit)

            if index == total_rows - 1:
                loss_amount = money_decimal(total_loss - distributed_loss)
            else:
                loss_amount = (
                    total_loss * layer_ratio
                ).quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP,
                )
                distributed_loss += loss_amount

        total_return = (
            contribution_amount + final_profit - loss_amount
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        total_deduction += deduction_amount
        total_final_profit += final_profit
        total_loss_amount += loss_amount

        layer_data = {
            "user_id": user.id,
            "user_name": user.get_full_name(),
            "email": user.email,
            "group": group_name,
            "deduction_percentage": money(deduction_percentage),
            "investment_sequence": contrib.investment_sequence,
            "investment_date": str(investment_date),
            "invested_days": invested_days,
            "contribution": money(contribution_amount),
            "acquisition_ratio": money(layer_ratio * Decimal("100")),
            "shares": str(shares),
            "gross_profit": money(gross_profit),
            "deduction": money(deduction_amount),
            "final_profit": money(final_profit),
            "loss_amount": money(loss_amount),
            "total_return": money(total_return),
        }

        layer_rows.append(layer_data)

        if user.id not in user_summary:
            user_summary[user.id] = {
                "user_id": user.id,
                "user_name": user.get_full_name(),
                "email": user.email,
                "group": group_name,
                "deduction_percentage": money(deduction_percentage),
                "total_contribution": Decimal("0.00"),
                "gross_profit": Decimal("0.00"),
                "deduction": Decimal("0.00"),
                "final_profit": Decimal("0.00"),
                "loss_amount": Decimal("0.00"),
                "total_return": Decimal("0.00"),
                "max_invested_days": 0,
                "layers": [],
            }

        user_summary[user.id]["total_contribution"] += contribution_amount
        user_summary[user.id]["gross_profit"] += gross_profit
        user_summary[user.id]["deduction"] += deduction_amount
        user_summary[user.id]["final_profit"] += final_profit
        user_summary[user.id]["loss_amount"] += loss_amount
        user_summary[user.id]["total_return"] += total_return
        user_summary[user.id]["max_invested_days"] = max(
            user_summary[user.id]["max_invested_days"],
            invested_days,
        )
        user_summary[user.id]["layers"].append(layer_data)

    user_summary_list = []

    for data in user_summary.values():
        user_summary_list.append({
            "user_id": data["user_id"],
            "user_name": data["user_name"],
            "email": data["email"],
            "group": data["group"],
            "deduction_percentage": data["deduction_percentage"],
            "total_contribution": money(data["total_contribution"]),
            "gross_profit": money(data["gross_profit"]),
            "deduction": money(data["deduction"]),
            "final_profit": money(data["final_profit"]),
            "loss_amount": money(data["loss_amount"]),
            "total_return": money(data["total_return"]),
            "max_invested_days": data["max_invested_days"],
            "layers": data["layers"],
        })

    roi_percentage = Decimal("0.00")
    if property_cost > 0:
        roi_percentage = (
            total_profit / property_cost * Decimal("100")
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

    profit_quality = "loss"
    if roi_percentage >= Decimal("50.00"):
        profit_quality = "excellent"
    elif roi_percentage >= Decimal("30.00"):
        profit_quality = "good"
    elif roi_percentage >= Decimal("20.00"):
        profit_quality = "reasonable"
    elif roi_percentage >= Decimal("10.00"):
        profit_quality = "low_but_positive"
    elif roi_percentage >= Decimal("0.00"):
        profit_quality = "very_low"

    return {
        "success": True,
        "simulation_only": True,
        "read_only": True,
        "database_updated": False,
        "property": {
            "id": property_obj.id,
            "name": property_obj.property_name,
            "status": property_obj.status,
            "buying_price": money(property_obj.buying_price),
            "service_cost": money(property_obj.service_cost),
            "acquisition_cost": money(property_cost),
            "contribution_total": money(contribution_total),
            "existing_selling_price": money(property_obj.selling_price),
        },
        "sale_simulation": {
            "simulation_date": str(simulation_date),
            "selling_price": money(selling_price),
            "acquisition_cost": money(property_cost),
            "estimated_total_profit": money(total_profit),
            "roi_percentage": str(roi_percentage),
            "profit_quality": profit_quality,
            "total_deduction": money(total_deduction),
            "total_final_profit": money(total_final_profit),
            "total_loss_amount": money(total_loss_amount),
        },
        "user_summary": user_summary_list,
        "contribution_rows": layer_rows,
        "warning": (
            "This is AI simulation only. No user balance, property selling price, "
            "or contribution record was changed."
        ),
    }


def generate_best_price_scenarios(property_obj):
    """
    AI suggested selling scenarios based on acquisition cost.
    Not market appraisal.
    """

    acquisition_cost = get_property_acquisition_cost(property_obj)

    if acquisition_cost <= 0:
        return {
            "success": False,
            "message": "Acquisition cost is zero. No scenario found.",
        }

    margins = [
        Decimal("0.20"),
        Decimal("0.30"),
        Decimal("0.40"),
        Decimal("0.50"),
    ]

    scenarios = []

    for margin in margins:
        target_selling_price = (
            acquisition_cost * (Decimal("1.00") + margin)
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        simulation = simulate_property_sale(
            property_obj=property_obj,
            selling_price=target_selling_price,
        )

        if simulation.get("success"):
            scenarios.append({
                "target_roi": str((margin * Decimal("100")).quantize(Decimal("0.01"))),
                "selling_price": simulation["sale_simulation"]["selling_price"],
                "acquisition_cost": simulation["sale_simulation"]["acquisition_cost"],
                "estimated_total_profit": simulation["sale_simulation"]["estimated_total_profit"],
                "total_final_profit": simulation["sale_simulation"]["total_final_profit"],
                "total_deduction": simulation["sale_simulation"]["total_deduction"],
                "profit_quality": simulation["sale_simulation"]["profit_quality"],
                "user_summary": simulation["user_summary"],
            })

    recommended = None

    for s in scenarios:
        if s["target_roi"] == "50.00":
            recommended = s
            break

    if not recommended and scenarios:
        recommended = scenarios[-1]

    return {
        "success": True,
        "read_only": True,
        "database_updated": False,
        "property_name": property_obj.property_name,
        "acquisition_cost": money(acquisition_cost),
        "recommended": recommended,
        "scenarios": scenarios,
        "warning": (
            "These are internal AI simulation scenarios based on acquisition cost, "
            "not market appraisal. No database record was changed."
        ),
    }


# ============================================================
# FORMATTERS IF OPENAI FAILS
# ============================================================

def format_sale_simulation_answer(simulation, style="banglish"):
    if not simulation.get("success"):
        return simulation.get("message", "Simulation failed.")

    prop = simulation["property"]
    sale = simulation["sale_simulation"]

    lines = [
        "AI Property Sale Simulation",
        "",
        f"Property: {prop['name']}",
        f"Buying price: ${prop['buying_price']}",
        f"Service cost: ${prop['service_cost']}",
        f"Acquisition cost: ${sale['acquisition_cost']}",
        f"Simulated selling price: ${sale['selling_price']}",
        f"Estimated total profit: ${sale['estimated_total_profit']}",
        f"Estimated ROI: {sale['roi_percentage']}%",
        f"Profit quality: {sale['profit_quality']}",
        f"Total final profit after deductions: ${sale['total_final_profit']}",
        "",
        "| User | Group | Deduction % | Invested | Profit Share % | Gross Profit | Deduction | Final Profit | Total Return |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for row in simulation["user_summary"]:
        # User total profit share percentage from all layers
        profit_share_percent = Decimal("0.00")
        for layer in row.get("layers", []):
            profit_share_percent += Decimal(str(layer.get("acquisition_ratio", "0") or "0"))

        lines.append(
            f"| {row['user_name']} | {row['group']} | {row['deduction_percentage']}% | "
            f"${row['total_contribution']} | {money(profit_share_percent)}% | "
            f"${row['gross_profit']} | ${row['deduction']} | "
            f"${row['final_profit']} | ${row['total_return']} |"
        )

    has_multi_layer = any(len(row.get("layers", [])) > 1 for row in simulation["user_summary"])

    if has_multi_layer:
        lines.extend([
            "",
            "Layer-wise detail:",
            "",
            "| User | Layer | Date | Days | Invested | Profit Share % | Gross Profit | Deduction | Final Profit | Return |",
            "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|",
        ])

        for row in simulation["user_summary"]:
            for layer in row.get("layers", []):
                lines.append(
                    f"| {row['user_name']} | #{layer['investment_sequence']} | "
                    f"{layer['investment_date']} | {layer['invested_days']} | "
                    f"${layer['contribution']} | {layer['acquisition_ratio']}% | "
                    f"${layer['gross_profit']} | ${layer['deduction']} | "
                    f"${layer['final_profit']} | ${layer['total_return']} |"
                )

    lines.extend([
        "",
        "Suggestion:",
        "Eta internal acquisition cost, contribution percentage, and user group deduction er upor based simulation. Market appraisal na.",
        "",
        "Note: Eta simulation only. Kono database record change hoy nai.",
    ])

    return "\n".join(lines)


def format_best_price_answer(result, style="banglish"):
    if not result.get("success"):
        return result.get("message", "No suggestion found.")

    recommended = result.get("recommended")

    lines = [
        f"{result['property_name']} property selling price guideline:",
        f"Acquisition cost: ${result['acquisition_cost']}",
        "",
        "Acquisition cost er upor based suggested scenarios:",
        "",
        "| Target ROI | Selling Price | Estimated Profit | Deduction | Final Profit | Quality |",
        "|---:|---:|---:|---:|---:|---|",
    ]

    for s in result["scenarios"]:
        lines.append(
            f"| {s['target_roi']}% | ${s['selling_price']} | "
            f"${s['estimated_total_profit']} | ${s['total_deduction']} | "
            f"${s['total_final_profit']} | {s['profit_quality']} |"
        )

    if recommended:
        lines.extend([
            "",
            f"Recommended internal guideline: around ${recommended['selling_price']} "
            f"price, target ROI {recommended['target_roi']}%.",
            "",
            "Recommended price e user-wise estimated profit:",
            "",
            "| User | Group | Deduction % | Invested | Gross Profit | Deduction | Final Profit | Total Return |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ])

        for row in recommended["user_summary"]:
            lines.append(
                f"| {row['user_name']} | {row['group']} | {row['deduction_percentage']}% | "
                f"${row['total_contribution']} | ${row['gross_profit']} | "
                f"${row['deduction']} | ${row['final_profit']} | ${row['total_return']} |"
            )

        has_multi_layer = any(len(row.get("layers", [])) > 1 for row in recommended["user_summary"])

        if has_multi_layer:
            lines.extend([
                "",
                "Layer-wise detail:",
                "",
                "| User | Layer | Date | Days | Invested | Profit Share % | Gross Profit | Deduction | Final Profit |",
                "|---|---:|---|---:|---:|---:|---:|---:|---:|",
            ])

            for row in recommended["user_summary"]:
                for layer in row.get("layers", []):
                    lines.append(
                        f"| {row['user_name']} | #{layer['investment_sequence']} | "
                        f"{layer['investment_date']} | {layer['invested_days']} | "
                        f"${layer['contribution']} | {layer['acquisition_ratio']}% | "
                        f"${layer['gross_profit']} | ${layer['deduction']} | "
                        f"${layer['final_profit']} |"
                    )

        lines.extend([
            "",
            "Suggestion:",
            "Jodi real market ei recommended price ba tar beshi support kore, tahole internal calculation onujayi profit valo. "
            "Kintu final decision-er age market value, repair cost, tax, holding cost, closing cost compare korte hobe.",
        ])

    lines.append("")
    lines.append("Note: Eta simulation only. Kono database record change hoy nai.")

    return "\n".join(lines)


# ============================================================
# OPENAI EXPLANATION - READ ONLY
# ============================================================

def explain_simulation_with_llm(question, calculation_result, style="banglish"):
    """
    OpenAI only explains already-calculated result.
    It must not change numbers.
    """

    client = get_openai_client()
    if not client:
        return None

    language_instruction = {
        "english": "Reply in clear English.",
        "bangla": "Reply in Bangla script.",
        "banglish": "Reply in Banglish / roman Bangla.",
    }.get(style, "Reply in Banglish / roman Bangla.")

    instructions = f"""
You are an AI finance advisor inside a real estate investment software.

{language_instruction}

Very important rules:
- You are read-only.
- Do not approve, reject, deduct, update, or modify anything.
- Do not invent or change any number.
- Use only the provided calculation JSON.
- Explain like ChatGPT: clear, helpful, conversational.
- If user has multiple layers, explain layer-wise profit and deduction.
- Mention deduction is applied per layer based on the user's own group percentage.
- Do not assume a fixed deduction percentage.
- Mention this is not market appraisal.
- Mention final decision should consider market value, repair cost, tax, holding cost, and closing cost.
- Clearly say no database record was changed.

Business rules:
- Acquisition cost = buying_price + service_cost.
- Estimated profit = selling_price - acquisition_cost.
- Profit share percentage = layer contribution / acquisition cost.
- Each PropertyContribution row is a separate layer.
- Per-layer deduction = layer gross profit × that user's group percentage / 100.
- Per-layer final profit = layer gross profit - layer deduction.
- User final profit = sum of all layer final profits.

Answer format:
- Give a short summary first.
- Then show a markdown table with columns:
  User | Group | Deduction % | Invested | Profit Share % | Gross Profit | Deduction | Final Profit | Total Return
- If a user has multiple layers, show a second layer-wise table.
- Do not change the numbers from JSON.
"""

    try:
        response = client.responses.create(
            model=getattr(settings, "OPENAI_AI_MODEL", "gpt-5.5"),
            instructions=instructions,
            input=[
                {
                    "role": "user",
                    "content": (
                        "User question:\n"
                        f"{question}\n\n"
                        "Calculation JSON:\n"
                        f"{json.dumps(calculation_result, indent=2)}"
                    ),
                }
            ],
        )

        return response.output_text

    except Exception:
        return None


# ============================================================
# MAIN AI CHATBOT
# ============================================================

def ask_ai_finance_chatbot(user, question, session=None):
    context = build_user_finance_context(user)
    style = detect_language_style(question)

    # Superuser / finance property sale simulator
    # This block is local calculation first. No database update.
    if is_admin_or_finance(user) and question_wants_property_sale_simulation(question):
        property_obj = find_property_from_question(question)

        if property_obj:
            selling_price = parse_money_from_question(
                question,
                property_obj=property_obj,
            )

            # User did not give selling price but asks guideline/profit/days
            if question_wants_best_selling_price(question) and not selling_price:
                best_price_result = generate_best_price_scenarios(property_obj)

                llm_answer = explain_simulation_with_llm(
                    question=question,
                    calculation_result=best_price_result,
                    style=style,
                )

                if llm_answer:
                    return llm_answer

                return format_best_price_answer(best_price_result, style=style)

            # User gave selling price
            if selling_price:
                simulation = simulate_property_sale(
                    property_obj=property_obj,
                    selling_price=selling_price,
                )

                llm_answer = explain_simulation_with_llm(
                    question=question,
                    calculation_result=simulation,
                    style=style,
                )

                if llm_answer:
                    return llm_answer

                return format_sale_simulation_answer(simulation, style=style)

            # Property found but price missing/unclear: show guideline
            best_price_result = generate_best_price_scenarios(property_obj)

            llm_answer = explain_simulation_with_llm(
                question=question,
                calculation_result=best_price_result,
                style=style,
            )

            if llm_answer:
                return llm_answer

            return format_best_price_answer(best_price_result, style=style)

        if style == "english":
            return (
                "I could not find the property from your question. "
                "Please include the exact property name."
            )

        if style == "bangla":
            return (
                "আপনার question থেকে property খুঁজে পাইনি। "
                "অনুগ্রহ করে exact property name লিখুন।"
            )

        return (
            "Apnar question theke property khuje pai nai. "
            "Please exact property name likhun."
        )

    # Normal OpenAI chatbot
    recent_messages = []
    if session:
        recent_messages = get_recent_chat_messages(session)

    instructions = """
You are a read-only AI chatbot inside a real estate investment software.

Language rule:
- If the user's latest question is in Bangla script, reply in Bangla script.
- If the user's latest question is in English, reply in English.
- If the user's latest question is in Banglish / roman Bangla, reply in Banglish.
- Match the user's latest question language only.
- Do not copy previous chat language.

Intent rule:
- If user asks current balance, answer only current_balance.
- If user asks total balance, answer total_request_limit and explain it includes current_balance + running_invest.
- If user asks total invest or running investment, answer running_invest and list running properties.
- If user asks withdraw amount, answer total_request_limit and explain approval deducts only from current_balance.
- If user asks final profit, answer final_profit.
- If user asks request pending/status, answer latest withdrawal request status.

Strict safety rules:
- You cannot create withdrawal request.
- You cannot approve withdrawal request.
- You cannot reject withdrawal request.
- You cannot deduct user balance.
- You cannot update property contribution.
- You cannot approve payment.
- You cannot distribute profit.
- You cannot update database.
- Never say “done”, “approved”, “deducted”, or “created” as if you performed an action.
- If user asks you to do an action, tell them which page/button to use.

Business rules:
- User request limit = current_balance + running_invest.
- Final approval deducts only from current_balance.
- If requested amount is greater than current_balance, finance/admin must first adjust running investment so balance becomes enough.
- Use only the provided JSON context.
- Do not invent numbers.
"""

    input_messages = []

    for msg in recent_messages:
        input_messages.append(msg)

    input_messages.append({
        "role": "user",
        "content": (
            "Database context JSON:\n"
            f"{json.dumps(context, indent=2)}\n\n"
            f"User question:\n{question}"
        ),
    })

    client = get_openai_client()

    if not client:
        return simple_fallback_answer(user, question)

    try:
        response = client.responses.create(
            model=getattr(settings, "OPENAI_AI_MODEL", "gpt-5.5"),
            instructions=instructions,
            input=input_messages,
        )

        return response.output_text

    except Exception:
        return simple_fallback_answer(user, question)


# ============================================================
# WITHDRAWAL PREDICTION
# ============================================================

def build_withdrawal_prediction_context(withdrawal):
    user = withdrawal.user
    finance_context = build_user_finance_context(user)

    current_balance = Decimal(str(user.balance or 0))
    requested_amount = Decimal(str(withdrawal.amount or 0))
    running_invest = Decimal(str(finance_context["summary"]["running_invest"]))
    total_request_limit = current_balance + running_invest

    balance_shortage = requested_amount - current_balance
    if balance_shortage < 0:
        balance_shortage = Decimal("0.00")

    return {
        "withdrawal_request": {
            "id": withdrawal.id,
            "status": withdrawal.status,
            "requested_amount": money(requested_amount),
            "user_note": withdrawal.note or "",
            "finance_note": withdrawal.finance_note or "",
            "clarification_note": getattr(withdrawal, "clarification_note", "") or "",
            "created_at": str(withdrawal.created_at),
        },
        "prediction": {
            "current_balance": money(current_balance),
            "running_invest": money(running_invest),
            "total_request_limit": money(total_request_limit),
            "balance_shortage": money(balance_shortage),
            "request_valid_by_total_limit": requested_amount <= total_request_limit,
            "can_approve_now": current_balance >= requested_amount,
        },
        "rules": finance_context["rules"],
        "running_investments": finance_context["running_investments"],
        "sold_property_profits": finance_context["sold_property_profits"],
    }


def ai_predict_withdrawal(withdrawal):
    context = build_withdrawal_prediction_context(withdrawal)

    instructions = """
You are a read-only AI finance reviewer.

Language:
- Reply in Bangla/Banglish.

Strict safety rules:
- Do not approve.
- Do not reject.
- Do not deduct.
- Do not update database.
- Only prediction and suggestion.

Explain:
1. Request amount
2. Current balance
3. Running investment
4. Total request limit
5. Whether request is valid
6. Whether approve is possible now
7. If not possible, what finance/admin should do
8. Suggested clarification note if needed

Use only the JSON context. Do not invent numbers.
"""

    fallback_prediction = (
        f"Request amount: ${context['withdrawal_request']['requested_amount']}\n"
        f"Current balance: ${context['prediction']['current_balance']}\n"
        f"Running investment: ${context['prediction']['running_invest']}\n"
        f"Total request limit: ${context['prediction']['total_request_limit']}\n"
        f"Balance shortage: ${context['prediction']['balance_shortage']}\n\n"
        "AI service unavailable, so this is database fallback prediction.\n"
        "Approve possible now: "
        f"{'Yes' if context['prediction']['can_approve_now'] else 'No'}.\n"
        "No balance was changed."
    )

    client = get_openai_client()

    if not client:
        return fallback_prediction, context

    try:
        response = client.responses.create(
            model=getattr(settings, "OPENAI_AI_MODEL", "gpt-5.5"),
            instructions=instructions,
            input=[
                {
                    "role": "user",
                    "content": (
                        "Withdrawal prediction JSON:\n"
                        f"{json.dumps(context, indent=2)}"
                    ),
                }
            ],
        )

        return response.output_text, context

    except Exception:
        return fallback_prediction, context




# import json
# from decimal import Decimal, ROUND_HALF_UP

# from django.conf import settings
# from django.db.models import Sum
# from openai import OpenAI

# from accounts.models import (
#     PropertyContribution,
#     WithdrawalRequest,
# )


# client = OpenAI(api_key=settings.OPENAI_API_KEY)


# def money(value):
#     return str(
#         Decimal(str(value or 0)).quantize(
#             Decimal("0.01"),
#             rounding=ROUND_HALF_UP,
#         )
#     )


# def get_running_statuses():
#     return ["bought", "ready_to_sell", "rented"]


# def get_user_running_invest(user):
#     total = PropertyContribution.objects.filter(
#         user=user,
#         property__status__in=get_running_statuses(),
#         property__is_contribution_locked=False,
#         contribution__gt=0,
#     ).aggregate(total=Sum("contribution"))["total"] or Decimal("0.00")

#     return Decimal(str(total))


# def get_user_final_profit(user):
#     total = PropertyContribution.objects.filter(
#         user=user,
#         property__status="sold",
#     ).aggregate(total=Sum("final_profit"))["total"] or Decimal("0.00")

#     return Decimal(str(total))


# def get_user_latest_withdrawal_requests(user):
#     rows = WithdrawalRequest.objects.filter(
#         user=user,
#     ).order_by("-created_at")[:10]

#     data = []

#     for row in rows:
#         data.append({
#             "id": row.id,
#             "amount": money(row.amount),
#             "status": row.status,
#             "note": row.note or "",
#             "finance_note": row.finance_note or "",
#             "clarification_note": getattr(row, "clarification_note", "") or "",
#             "created_at": str(row.created_at),
#             "approved_at": str(row.approved_at) if row.approved_at else None,
#             "rejected_at": str(row.rejected_at) if row.rejected_at else None,
#         })

#     return data


# def build_user_finance_context(user):
#     current_balance = Decimal(str(user.balance or 0))
#     running_invest = get_user_running_invest(user)
#     final_profit = get_user_final_profit(user)
#     total_request_limit = current_balance + running_invest

#     running_rows = PropertyContribution.objects.filter(
#         user=user,
#         property__status__in=get_running_statuses(),
#         property__is_contribution_locked=False,
#         contribution__gt=0,
#     ).select_related("property").order_by(
#         "property__property_name",
#         "investment_sequence",
#         "id",
#     )

#     sold_profit_rows = PropertyContribution.objects.filter(
#         user=user,
#         property__status="sold",
#     ).select_related("property").order_by(
#         "-property__selling_date",
#         "property__property_name",
#         "investment_sequence",
#         "id",
#     )

#     running_investments = []
#     for row in running_rows:
#         running_investments.append({
#             "property_name": row.property.property_name,
#             "property_status": row.property.status,
#             "investment_sequence": row.investment_sequence,
#             "contribution": money(row.contribution),
#             "investment_date": str(row.investment_date) if row.investment_date else None,
#             "shares": str(row.shares or "0"),
#         })

#     sold_profits = []
#     for row in sold_profit_rows:
#         sold_profits.append({
#             "property_name": row.property.property_name,
#             "investment_sequence": row.investment_sequence,
#             "principal_returned": money(row.contribution),
#             "gross_profit": money(row.profit),
#             "deduction": money(row.deduction),
#             "final_profit": money(row.final_profit),
#             "selling_date": str(row.property.selling_date) if row.property.selling_date else None,
#         })

#     return {
#         "user": {
#             "id": user.id,
#             "name": user.get_full_name(),
#             "email": user.email,
#         },
#         "summary": {
#             "current_balance": money(current_balance),
#             "running_invest": money(running_invest),
#             "final_profit": money(final_profit),
#             "total_request_limit": money(total_request_limit),
#         },
#         "rules": {
#             "ai_role": "read_only_suggestion_prediction_explanation",
#             "ai_can_create_request": False,
#             "ai_can_approve_request": False,
#             "ai_can_reject_request": False,
#             "ai_can_deduct_balance": False,
#             "ai_can_update_database": False,
#             "withdraw_request_limit": "current_balance + running_invest",
#             "withdraw_approval_deducts_from": "current_balance only",
#             "if_request_amount_more_than_current_balance": (
#                 "finance/admin must adjust running investment first before approval"
#             ),
#         },
#         "running_investments": running_investments,
#         "sold_property_profits": sold_profits,
#         "withdrawal_requests": get_user_latest_withdrawal_requests(user),
#     }


# def get_recent_chat_messages(session, limit=12):
#     messages = session.messages.order_by("-created_at")[:limit]
#     messages = list(messages)
#     messages.reverse()

#     clean_messages = []

#     for msg in messages:
#         if msg.role in ["user", "assistant"]:
#             clean_messages.append({
#                 "role": msg.role,
#                 "content": msg.content,
#             })

#     return clean_messages


# def ask_ai_finance_chatbot(user, question, session=None):
#     context = build_user_finance_context(user)

#     recent_messages = []
#     if session:
#         recent_messages = get_recent_chat_messages(session)

#     instructions = """
# You are a read-only AI chatbot inside a real estate investment software.

# Language:
# - Reply in Bangla/Banglish naturally.
# - User can ask in Bangla, English, or Banglish.
# - Understand natural language. Do not require exact fixed questions.

# Your job:
# - Explain current balance.
# - Explain running property investment.
# - Explain sold property final profit.
# - Explain withdrawal request limit.
# - Explain pending/rejected/approved withdrawal request status.
# - Predict whether a withdrawal request can be approved now.
# - Suggest next step.

# Strict safety rules:
# - You cannot create withdrawal request.
# - You cannot approve withdrawal request.
# - You cannot reject withdrawal request.
# - You cannot deduct user balance.
# - You cannot update property contribution.
# - You cannot approve payment.
# - You cannot distribute profit.
# - You cannot update database.
# - Never say “done”, “approved”, “deducted”, or “created” as if you performed an action.
# - If user asks you to do an action, tell them which page/button to use.

# Business rules:
# - User request limit = current_balance + running_invest.
# - Final approval deducts only from current_balance.
# - If requested amount is greater than current_balance, finance/admin must first adjust running investment so balance becomes enough.
# - Use only the provided JSON context.
# - Do not invent numbers.
# """

#     input_messages = []

#     for msg in recent_messages:
#         input_messages.append(msg)

#     input_messages.append({
#         "role": "user",
#         "content": (
#             "Database context JSON:\n"
#             f"{json.dumps(context, indent=2)}\n\n"
#             f"User question:\n{question}"
#         ),
#     })

#     response = client.responses.create(
#         model=getattr(settings, "OPENAI_AI_MODEL", "gpt-5.5"),
#         instructions=instructions,
#         input=input_messages,
#     )

#     return response.output_text


# def build_withdrawal_prediction_context(withdrawal):
#     user = withdrawal.user
#     finance_context = build_user_finance_context(user)

#     current_balance = Decimal(str(user.balance or 0))
#     requested_amount = Decimal(str(withdrawal.amount or 0))
#     running_invest = Decimal(str(finance_context["summary"]["running_invest"]))
#     total_request_limit = current_balance + running_invest

#     balance_shortage = requested_amount - current_balance
#     if balance_shortage < 0:
#         balance_shortage = Decimal("0.00")

#     return {
#         "withdrawal_request": {
#             "id": withdrawal.id,
#             "status": withdrawal.status,
#             "requested_amount": money(requested_amount),
#             "user_note": withdrawal.note or "",
#             "finance_note": withdrawal.finance_note or "",
#             "clarification_note": getattr(withdrawal, "clarification_note", "") or "",
#             "created_at": str(withdrawal.created_at),
#         },
#         "prediction": {
#             "current_balance": money(current_balance),
#             "running_invest": money(running_invest),
#             "total_request_limit": money(total_request_limit),
#             "balance_shortage": money(balance_shortage),
#             "request_valid_by_total_limit": requested_amount <= total_request_limit,
#             "can_approve_now": current_balance >= requested_amount,
#         },
#         "rules": finance_context["rules"],
#         "running_investments": finance_context["running_investments"],
#         "sold_property_profits": finance_context["sold_property_profits"],
#     }


# def ai_predict_withdrawal(withdrawal):
#     context = build_withdrawal_prediction_context(withdrawal)

#     instructions = """
# You are a read-only AI finance reviewer.

# Language:
# - Reply in Bangla/Banglish.

# Strict safety rules:
# - Do not approve.
# - Do not reject.
# - Do not deduct.
# - Do not update database.
# - Only prediction and suggestion.

# Explain:
# 1. Request amount
# 2. Current balance
# 3. Running investment
# 4. Total request limit
# 5. Whether request is valid
# 6. Whether approve is possible now
# 7. If not possible, what finance/admin should do
# 8. Suggested clarification note if needed

# Use only the JSON context. Do not invent numbers.
# """

#     response = client.responses.create(
#         model=getattr(settings, "OPENAI_AI_MODEL", "gpt-5.5"),
#         instructions=instructions,
#         input=[
#             {
#                 "role": "user",
#                 "content": (
#                     "Withdrawal prediction JSON:\n"
#                     f"{json.dumps(context, indent=2)}"
#                 ),
#             }
#         ],
#     )

#     return response.output_text, context


# # def simple_fallback_answer(user, question):
# #     q = (question or "").lower()

# #     context = build_user_finance_context(user)
# #     summary = context["summary"]

# #     if (
# #         "balance" in q
# #         or "taka" in q
# #         or "টাকা" in q
# #         or "balanc" in q
# #         or "amar taka" in q
# #     ):
# #         return (
# #             f"Apnar current balance ${summary['current_balance']}. "
# #             f"Running investment ${summary['running_invest']}. "
# #             f"Total request limit ${summary['total_request_limit']}."
# #         )

# #     if "profit" in q or "labh" in q or "লাভ" in q:
# #         return (
# #             f"Apnar sold property final profit ${summary['final_profit']}."
# #         )

# #     if (
# #         "withdraw" in q
# #         or "withdrow" in q
# #         or "nite" in q
# #         or " নিতে" in q
# #         or "tulte" in q
# #         or "তুলতে" in q
# #     ):
# #         return (
# #             f"Apni maximum ${summary['total_request_limit']} withdraw request korte parben. "
# #             f"Kintu approval hole deduction hobe sudhu current balance ${summary['current_balance']} theke."
# #         )

# #     if "invest" in q or "investment" in q or "property" in q:
# #         running = context.get("running_investments", [])

# #         if not running:
# #             return (
# #                 f"Apnar current running investment ${summary['running_invest']}. "
# #                 "Currently kono running property investment details found hoy nai."
# #             )

# #         lines = [
# #             f"Apnar current running investment ${summary['running_invest']}."
# #         ]

# #         for item in running:
# #             lines.append(
# #                 f"- {item['property_name']}: ${item['contribution']} ({item['property_status']})"
# #             )

# #         return "\n".join(lines)

# #     if "pending" in q or "request" in q:
# #         requests = context.get("withdrawal_requests", [])

# #         if not requests:
# #             return "Apnar kono recent withdrawal request found hoy nai."

# #         latest = requests[0]

# #         if latest["status"] == "pending":
# #             if latest.get("clarification_note"):
# #                 return (
# #                     f"Apnar latest withdrawal request ${latest['amount']} ekhono pending. "
# #                     f"Finance clarification chaiche: {latest['clarification_note']}"
# #                 )

# #             return (
# #                 f"Apnar latest withdrawal request ${latest['amount']} ekhono pending. "
# #                 "Finance review korar por approve/reject/update korbe."
# #             )

# #         if latest["status"] == "approved":
# #             return (
# #                 f"Apnar latest withdrawal request ${latest['amount']} approved/paid hoyeche."
# #             )

# #         if latest["status"] == "rejected":
# #             return (
# #                 f"Apnar latest withdrawal request ${latest['amount']} rejected hoyeche. "
# #                 f"Reason: {latest.get('finance_note') or 'No reason provided.'}"
# #             )

# #     return (
# #         "AI service currently unavailable because API billing/quota is not active. "
# #         f"Your current balance is ${summary['current_balance']}, "
# #         f"running investment is ${summary['running_invest']}, "
# #         f"final profit is ${summary['final_profit']}, "
# #         f"and total request limit is ${summary['total_request_limit']}."
# #     )

# def detect_language_style(text):
#     """
#     Detect user input style:
#     - bangla: Bengali script
#     - english: mostly English words
#     - banglish: roman Bangla / mixed
#     """
#     text = (text or "").strip().lower()

#     bangla_chars = any("\u0980" <= ch <= "\u09FF" for ch in text)

#     if bangla_chars:
#         return "bangla"

#     banglish_words = [
#         "amar", "ami", "koto", "taka", "ache", "ase", "parbo",
#         "korbo", "korte", "nite", "tulte", "bolen", "bolo",
#         "kon", "kothay", "keno", "hoyeche", "hoy nai", "dekhte",
#         "invest", "withdraw", "withdrow"
#     ]

#     english_words = [
#         "what", "how", "where", "why", "can", "my", "balance",
#         "total", "profit", "investment", "withdraw", "request",
#         "pending", "status"
#     ]

#     banglish_score = sum(1 for w in banglish_words if w in text)
#     english_score = sum(1 for w in english_words if w in text)

#     if banglish_score > english_score:
#         return "banglish"

#     return "english"


# def reply_text(style, key, data=None):
#     data = data or {}

#     messages = {
#         "current_balance": {
#             "bangla": (
#                 f"আপনার বর্তমান balance ${data['current_balance']}। "
#                 f"Running investment ${data['running_invest']}। "
#                 f"Total request limit ${data['total_request_limit']}।"
#             ),
#             "english": (
#                 f"Your current balance is ${data['current_balance']}. "
#                 f"Your running investment is ${data['running_invest']}. "
#                 f"Your total request limit is ${data['total_request_limit']}."
#             ),
#             "banglish": (
#                 f"Apnar current balance ${data['current_balance']}. "
#                 f"Running investment ${data['running_invest']}. "
#                 f"Total request limit ${data['total_request_limit']}."
#             ),
#         },

#         "total_balance": {
#             "bangla": (
#                 f"আপনার total balance/request capacity হলো ${data['total_request_limit']}। "
#                 f"এর মধ্যে current balance ${data['current_balance']} এবং running investment ${data['running_invest']}।"
#             ),
#             "english": (
#                 f"Your total balance/request capacity is ${data['total_request_limit']}. "
#                 f"This includes current balance ${data['current_balance']} and running investment ${data['running_invest']}."
#             ),
#             "banglish": (
#                 f"Apnar total balance/request capacity ${data['total_request_limit']}. "
#                 f"Er moddhe current balance ${data['current_balance']} and running investment ${data['running_invest']}."
#             ),
#         },

#         "withdraw": {
#             "bangla": (
#                 f"আপনি maximum ${data['total_request_limit']} withdraw request করতে পারবেন। "
#                 f"কিন্তু approve হলে deduction হবে শুধু current balance ${data['current_balance']} থেকে।"
#             ),
#             "english": (
#                 f"You can request a maximum withdrawal of ${data['total_request_limit']}. "
#                 f"But when approved, the deduction will be made only from your current balance of ${data['current_balance']}."
#             ),
#             "banglish": (
#                 f"Apni maximum ${data['total_request_limit']} withdraw request korte parben. "
#                 f"Kintu approve hole deduction hobe sudhu current balance ${data['current_balance']} theke."
#             ),
#         },

#         "profit": {
#             "bangla": f"আপনার sold property final profit ${data['final_profit']}।",
#             "english": f"Your sold property final profit is ${data['final_profit']}.",
#             "banglish": f"Apnar sold property final profit ${data['final_profit']}.",
#         },

#         "no_running_invest": {
#             "bangla": f"আপনার current running investment ${data['running_invest']}। কোনো running property investment details পাওয়া যায়নি।",
#             "english": f"Your current running investment is ${data['running_invest']}. No running property investment details were found.",
#             "banglish": f"Apnar current running investment ${data['running_invest']}. Kono running property investment details found hoy nai.",
#         },

#         "no_request": {
#             "bangla": "আপনার কোনো recent withdrawal request পাওয়া যায়নি।",
#             "english": "No recent withdrawal request was found.",
#             "banglish": "Apnar kono recent withdrawal request found hoy nai.",
#         },

#         "default": {
#             "bangla": (
#                 f"AI service এখন unavailable, তাই database fallback answer দেখাচ্ছি। "
#                 f"Current balance ${data['current_balance']}, running investment ${data['running_invest']}, "
#                 f"final profit ${data['final_profit']}, total request limit ${data['total_request_limit']}।"
#             ),
#             "english": (
#                 f"AI service is currently unavailable, so I am showing a database fallback answer. "
#                 f"Current balance ${data['current_balance']}, running investment ${data['running_invest']}, "
#                 f"final profit ${data['final_profit']}, total request limit ${data['total_request_limit']}."
#             ),
#             "banglish": (
#                 f"AI service currently unavailable, tai database fallback answer dekhacchi. "
#                 f"Current balance ${data['current_balance']}, running investment ${data['running_invest']}, "
#                 f"final profit ${data['final_profit']}, total request limit ${data['total_request_limit']}."
#             ),
#         },
#     }

#     return messages[key].get(style, messages[key]["english"])


# def simple_fallback_answer(user, question):
#     q = (question or "").lower().strip()
#     style = detect_language_style(q)

#     context = build_user_finance_context(user)
#     summary = context["summary"]

#     data = {
#         "current_balance": summary["current_balance"],
#         "running_invest": summary["running_invest"],
#         "final_profit": summary["final_profit"],
#         "total_request_limit": summary["total_request_limit"],
#     }

#     # 1. Withdraw intent
#     withdraw_keywords = [
#         "withdraw", "withdrow", "withdrawal", "nite", "nibo", "tulte",
#         "tulbo", "parbo", "নিতে", "তুলতে", "উইথড্র", "উত্তোলন"
#     ]

#     if any(word in q for word in withdraw_keywords):
#         return reply_text(style, "withdraw", data)

#     # 2. Pending/request status intent
#     request_keywords = [
#         "pending", "request", "status", "keno", "why",
#         "পেন্ডিং", "রিকোয়েস্ট", "স্ট্যাটাস", "কেন"
#     ]

#     if any(word in q for word in request_keywords):
#         requests = context.get("withdrawal_requests", [])

#         if not requests:
#             return reply_text(style, "no_request", data)

#         latest = requests[0]

#         if latest["status"] == "pending":
#             if latest.get("clarification_note"):
#                 if style == "bangla":
#                     return (
#                         f"আপনার latest withdrawal request ${latest['amount']} এখনো pending। "
#                         f"Finance clarification চেয়েছে: {latest['clarification_note']}"
#                     )
#                 if style == "english":
#                     return (
#                         f"Your latest withdrawal request of ${latest['amount']} is still pending. "
#                         f"Finance requested clarification: {latest['clarification_note']}"
#                     )
#                 return (
#                     f"Apnar latest withdrawal request ${latest['amount']} ekhono pending. "
#                     f"Finance clarification chaiche: {latest['clarification_note']}"
#                 )

#             if style == "bangla":
#                 return (
#                     f"আপনার latest withdrawal request ${latest['amount']} এখনো pending। "
#                     "Finance review করার পর approve/reject/update করবে।"
#                 )
#             if style == "english":
#                 return (
#                     f"Your latest withdrawal request of ${latest['amount']} is still pending. "
#                     "Finance will review it and then approve, reject, or request clarification."
#                 )
#             return (
#                 f"Apnar latest withdrawal request ${latest['amount']} ekhono pending. "
#                 "Finance review korar por approve/reject/update korbe."
#             )

#         if latest["status"] == "approved":
#             if style == "bangla":
#                 return f"আপনার latest withdrawal request ${latest['amount']} approved/paid হয়েছে।"
#             if style == "english":
#                 return f"Your latest withdrawal request of ${latest['amount']} has been approved/paid."
#             return f"Apnar latest withdrawal request ${latest['amount']} approved/paid hoyeche."

#         if latest["status"] == "rejected":
#             reason = latest.get("finance_note") or "No reason provided."
#             if style == "bangla":
#                 return f"আপনার latest withdrawal request ${latest['amount']} rejected হয়েছে। Reason: {reason}"
#             if style == "english":
#                 return f"Your latest withdrawal request of ${latest['amount']} was rejected. Reason: {reason}"
#             return f"Apnar latest withdrawal request ${latest['amount']} rejected hoyeche. Reason: {reason}"

#     # 3. Profit intent
#     profit_keywords = [
#         "profit", "labh", " লাভ", "লাভ", "final profit", "gain"
#     ]

#     if any(word in q for word in profit_keywords):
#         return reply_text(style, "profit", data)

#     # 4. Running investment / total invest intent
#     invest_keywords = [
#         "total invest", "running invest", "investment", "invest",
#         "property te", "property", "বিনিয়োগ", "ইনভেস্ট", "প্রপার্টি"
#     ]

#     if any(word in q for word in invest_keywords):
#         running = context.get("running_investments", [])

#         if not running:
#             return reply_text(style, "no_running_invest", data)

#         if style == "bangla":
#             lines = [f"আপনার current running investment ${data['running_invest']}।"]
#             for item in running:
#                 lines.append(
#                     f"- {item['property_name']}: ${item['contribution']} ({item['property_status']})"
#                 )
#             return "\n".join(lines)

#         if style == "english":
#             lines = [f"Your current running investment is ${data['running_invest']}."]
#             for item in running:
#                 lines.append(
#                     f"- {item['property_name']}: ${item['contribution']} ({item['property_status']})"
#                 )
#             return "\n".join(lines)

#         lines = [f"Apnar current running investment ${data['running_invest']}."]
#         for item in running:
#             lines.append(
#                 f"- {item['property_name']}: ${item['contribution']} ({item['property_status']})"
#             )
#         return "\n".join(lines)

#     # 5. Total balance intent
#     total_balance_keywords = [
#         "total balance", "total taka", "total amount", "total capacity",
#         "request limit", "সব মিলিয়ে", "মোট", "টোটাল"
#     ]

#     if any(word in q for word in total_balance_keywords):
#         return reply_text(style, "total_balance", data)

#     # 6. Current balance intent
#     balance_keywords = [
#         "balance", "taka", "amount", "money", "cash",
#         "টাকা", "ব্যালেন্স", "ক্যাশ"
#     ]

#     if any(word in q for word in balance_keywords):
#         return reply_text(style, "current_balance", data)

#     # 7. Default
#     return reply_text(style, "default", data)