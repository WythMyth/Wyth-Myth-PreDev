from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404

from accounts.models import WithdrawalRequest

from .models import AIChatSession, AIChatMessage, AIPredictionLog
from .services import ask_ai_finance_chatbot, ai_predict_withdrawal
from .services import ask_ai_finance_chatbot, simple_fallback_answer

def is_finance_user(user):
    return user.is_superuser or getattr(user, "is_finnancial", False)


@login_required
def ai_chat_page(request):
    session, created = AIChatSession.objects.get_or_create(
        user=request.user,
        chat_type="user_finance",
        defaults={"title": "AI Finance Assistant"},
    )

    chat_messages = session.messages.order_by("created_at")[:100]

    return render(request, "ai_assistant/chat.html", {
        "session": session,
        "chat_messages": chat_messages,
    })


# @login_required
# def ai_chat_api(request):
#     if request.method != "POST":
#         return JsonResponse({
#             "success": False,
#             "message": "Invalid request method.",
#         }, status=405)

#     question = request.POST.get("question", "").strip()

#     if not question:
#         return JsonResponse({
#             "success": False,
#             "message": "Question is required.",
#         }, status=400)

#     session, created = AIChatSession.objects.get_or_create(
#         user=request.user,
#         chat_type="user_finance",
#         defaults={"title": "AI Finance Assistant"},
#     )

#     AIChatMessage.objects.create(
#         session=session,
#         role="user",
#         content=question,
#     )

#     try:
#         answer = ask_ai_finance_chatbot(
#             user=request.user,
#             question=question,
#             session=session,
#         )

#         AIChatMessage.objects.create(
#             session=session,
#             role="assistant",
#             content=answer,
#             metadata={
#                 "read_only": True,
#                 "can_update_database": False,
#                 "can_deduct_balance": False,
#             },
#         )

#         return JsonResponse({
#             "success": True,
#             "answer": answer,
#         })

#     except Exception as e:
#         return JsonResponse({
#             "success": False,
#             "message": str(e),
#         }, status=500)

@login_required
def ai_chat_api(request):
    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "message": "Invalid request method.",
        }, status=405)

    question = request.POST.get("question", "").strip()

    if not question:
        return JsonResponse({
            "success": False,
            "message": "Question is required.",
        }, status=400)

    session, created = AIChatSession.objects.get_or_create(
        user=request.user,
        chat_type="user_finance",
        defaults={"title": "AI Finance Assistant"},
    )

    AIChatMessage.objects.create(
        session=session,
        role="user",
        content=question,
    )

    try:
        answer = ask_ai_finance_chatbot(
            user=request.user,
            question=question,
            session=session,
        )

        AIChatMessage.objects.create(
            session=session,
            role="assistant",
            content=answer,
            metadata={
                "read_only": True,
                "can_update_database": False,
                "can_deduct_balance": False,
                "fallback": False,
            },
        )

        return JsonResponse({
            "success": True,
            "answer": answer,
            "fallback": False,
        })

    except Exception as e:
        error_text = str(e)

        # OpenAI billing/quota problem fallback
        if (
            "insufficient_quota" in error_text
            or "exceeded your current quota" in error_text
            or "429" in error_text
        ):
            fallback = simple_fallback_answer(request.user, question)

            AIChatMessage.objects.create(
                session=session,
                role="assistant",
                content=fallback,
                metadata={
                    "read_only": True,
                    "can_update_database": False,
                    "can_deduct_balance": False,
                    "fallback": True,
                    "reason": "openai_insufficient_quota",
                },
            )

            return JsonResponse({
                "success": True,
                "answer": fallback,
                "fallback": True,
                "message": "OpenAI quota unavailable. Showing database fallback answer.",
            })

        # Other AI errors
        AIChatMessage.objects.create(
            session=session,
            role="assistant",
            content="AI service error. Please contact admin.",
            metadata={
                "read_only": True,
                "fallback": True,
                "reason": "ai_service_error",
                "error": error_text,
            },
        )

        return JsonResponse({
            "success": False,
            "message": "AI service error. Please contact admin.",
        }, status=500)

@login_required
def ai_clear_chat(request):
    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "message": "Invalid request method.",
        }, status=405)

    session = AIChatSession.objects.filter(
        user=request.user,
        chat_type="user_finance",
    ).first()

    if session:
        session.messages.all().delete()

    messages.success(request, "AI chat cleared successfully.")
    return JsonResponse({"success": True})


@login_required
def ai_withdrawal_prediction_api(request, pk):
    if not is_finance_user(request.user):
        return JsonResponse({
            "success": False,
            "message": "Permission denied.",
        }, status=403)

    withdrawal = get_object_or_404(
        WithdrawalRequest.objects.select_related("user"),
        pk=pk,
    )

    try:
        prediction, context = ai_predict_withdrawal(withdrawal)

        AIPredictionLog.objects.create(
            user=withdrawal.user,
            prediction_type="withdrawal_review",
            input_snapshot=context,
            ai_response=prediction,
            created_by=request.user,
        )

        return JsonResponse({
            "success": True,
            "prediction": prediction,
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e),
        }, status=500)