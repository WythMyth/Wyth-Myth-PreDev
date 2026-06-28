from django.urls import path

from . import views


app_name = "ai_assistant"

urlpatterns = [
    path(
        "chat/",
        views.ai_chat_page,
        name="chat",
    ),
    path(
        "chat/api/",
        views.ai_chat_api,
        name="chat_api",
    ),
    path(
        "chat/clear/",
        views.ai_clear_chat,
        name="clear_chat",
    ),
    path(
        "withdrawal/<int:pk>/prediction/",
        views.ai_withdrawal_prediction_api,
        name="withdrawal_prediction_api",
    ),
]