import json

from django import forms

from schedule.models import Tag

from .models import Poll


class PollForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all().order_by("order", "name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "hidden", "id": "id_tags_hidden"}),
    )

    payload = forms.CharField(widget=forms.HiddenInput(), required=True)

    class Meta:
        model = Poll
        fields = [
            "title",
            "message_need_to_be_send",
            "start_at",
            "end_at",
            "status",
            "vote_visibility",
            "tags",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "w-full rounded border px-3 py-2",
                    "placeholder": "Enter...",
                }
            ),
            "message_need_to_be_send": forms.Textarea(
                attrs={
                    "class": "w-full rounded border px-3 py-2",
                    "rows": 3,
                    "placeholder": "Enter...",
                }
            ),
            "start_at": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "w-full rounded border px-3 py-2",
                }
            ),
            "end_at": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "w-full rounded border px-3 py-2",
                }
            ),
            "status": forms.Select(attrs={"class": "w-full rounded border px-3 py-2"}),
            "vote_visibility": forms.Select(
                attrs={"class": "w-full rounded border px-3 py-2"}
            ),
        }

    def clean_payload(self):
        raw = self.cleaned_data["payload"]
        try:
            data = json.loads(raw)
        except Exception:
            raise forms.ValidationError("Invalid payload format.")

        questions = data.get("questions", [])
        if not isinstance(questions, list) or len(questions) < 1:
            raise forms.ValidationError("At least one question is required.")

        for q in questions:
            title = (q.get("title") or "").strip()
            qtype = q.get("type")
            options = q.get("options", [])

            if not title:
                raise forms.ValidationError("Each question must have a title.")
            if qtype not in ("single", "multi"):
                raise forms.ValidationError("Invalid question type.")
            if not isinstance(options, list) or len(options) < 1:
                raise forms.ValidationError(
                    "Each question must have at least one option."
                )

            cleaned = [str(x).strip() for x in options if str(x).strip()]
            if len(cleaned) < 1:
                raise forms.ValidationError(
                    "Each question must have at least one valid option."
                )
            q["options"] = cleaned

        return {"questions": questions}
