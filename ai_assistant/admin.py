from django.contrib import admin


from .models import AIChatSession, AIChatMessage, AIPredictionLog


class AIChatMessageInline(admin.TabularInline):
    model = AIChatMessage
    extra = 0
    readonly_fields = ("role", "content", "metadata", "created_at")


@admin.register(AIChatSession)
class AIChatSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "chat_type", "title", "is_active", "created_at", "updated_at")
    list_filter = ("chat_type", "is_active", "created_at")
    search_fields = ("user__email", "user__first_name", "user__last_name", "title")
    inlines = [AIChatMessageInline]


@admin.register(AIChatMessage)
class AIChatMessageAdmin(admin.ModelAdmin):
    list_display = ("session", "role", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("content", "session__user__email")


@admin.register(AIPredictionLog)
class AIPredictionLogAdmin(admin.ModelAdmin):
    list_display = ("prediction_type", "user", "created_by", "created_at")
    list_filter = ("prediction_type", "created_at")
    search_fields = ("user__email", "created_by__email", "ai_response")
    readonly_fields = ("input_snapshot", "ai_response", "created_at")