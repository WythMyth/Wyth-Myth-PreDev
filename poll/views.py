import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from poll.permission import require_permission



from .forms import PollForm
from .models import Choice, Poll, PollResponse, Question, Vote
from .tasks import send_poll_notification_task


def build_existing_payload_json(poll: Poll) -> str:
    data = {"questions": []}
    qs = poll.questions.prefetch_related("choices").all()
    for q in qs:
        data["questions"].append(
            {
                "title": q.title,
                "type": q.qtype,
                "allow_other": q.allow_other,
                "options": [c.label for c in q.choices.all()],
            }
        )
    return json.dumps(data)


@login_required
def poll_list(request):
    now = timezone.now()

    if request.user.is_superuser:
        polls = (
            Poll.objects.all()
            .prefetch_related("tags")
            .annotate(response_count=Count("responses"))
        )
        return render(
            request,
            "dashboard/polls/poll_list.html",
            {
                "polls": polls,
                "now": now,
                "voted_poll_ids": set(),
            },
        )

    user_tag_ids = []
    if hasattr(request.user, "tags"):
        user_tag_ids = list(request.user.tags.values_list("id", flat=True))

    polls = (
        Poll.objects.filter(status=Poll.STATUS_PUBLISHED)
        .filter(tags__in=user_tag_ids)  # ✅ tag only
        .distinct()
        .prefetch_related("tags")
        .annotate(response_count=Count("responses", distinct=True))
        .order_by("-created_at")
    )

    voted_poll_ids = set(
        PollResponse.objects.filter(user=request.user).values_list("poll_id", flat=True)
    )
    return render(
        request,
        "dashboard/polls/poll_list.html",
        {
            "polls": polls,
            "now": now,
            "voted_poll_ids": voted_poll_ids,
        },
    )


@login_required
@require_permission("is_superuser")
@transaction.atomic
def poll_create(request):
    if request.method == "POST":
        form = PollForm(request.POST)
        if form.is_valid():
            poll = form.save(commit=False)
            poll.created_by = request.user
            poll.save()
            form.save_m2m()

            payload = form.cleaned_data["payload"]
            for idx, q in enumerate(payload["questions"], start=1):
                question = Question.objects.create(
                    poll=poll,
                    title=q["title"].strip(),
                    qtype=q["type"],
                    allow_other=bool(q.get("allow_other", False)),
                    order=idx,
                )
                for c_idx, label in enumerate(q["options"], start=1):
                    Choice.objects.create(
                        question=question, label=label.strip(), order=c_idx
                    )

            # Schedule email to fire at exactly start_at
            send_poll_notification_task.apply_async(
                args=[poll.id],
                eta=poll.start_at,
            )

            messages.success(request, "Poll created successfully.")
            return redirect("polls:list")

        messages.error(request, "Please fix the form errors and try again.")
    else:
        form = PollForm()

    return render(
        request,
        "dashboard/polls/poll_form.html",
        {
            "form": form,
            "mode": "create",
            "existing_payload_json": json.dumps({"questions": []}),
        },
    )


@login_required
@require_permission("is_superuser")
@transaction.atomic
def poll_update(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    existing_payload_json = build_existing_payload_json(poll)

    if request.method == "POST":
        form = PollForm(request.POST, instance=poll)
        if form.is_valid():
            poll = form.save(commit=False)
            poll.save()
            form.save_m2m()

            payload = form.cleaned_data["payload"]

            Vote.objects.filter(response__poll=poll).delete()
            PollResponse.objects.filter(poll=poll).delete()
            poll.questions.all().delete()

            for idx, q in enumerate(payload["questions"], start=1):
                question = Question.objects.create(
                    poll=poll,
                    title=q["title"].strip(),
                    qtype=q["type"],
                    allow_other=bool(q.get("allow_other", False)),
                    order=idx,
                )
                for c_idx, label in enumerate(q["options"], start=1):
                    Choice.objects.create(
                        question=question, label=label.strip(), order=c_idx
                    )

            # Reset so the rescheduled task can send again for the updated start_at
            poll.notification_sent_at = None
            poll.save(update_fields=["notification_sent_at"])
            send_poll_notification_task.apply_async(
                args=[poll.id],
                eta=poll.start_at,
            )

            messages.success(request, "Poll updated successfully.")
            return redirect("polls:list")

        messages.error(request, "Please fix the form errors and try again.")
    else:
        form = PollForm(instance=poll)

    return render(
        request,
        "dashboard/polls/poll_form.html",
        {
            "form": form,
            "mode": "edit",
            "poll": poll,
            "existing_payload_json": existing_payload_json,
        },
    )


@login_required
@require_permission("is_superuser")
@transaction.atomic
def poll_copy(request, poll_id):
    src = get_object_or_404(Poll, pk=poll_id)

    # duplicate poll
    new_poll = Poll.objects.create(
        title=f"{src.title} (Copy)",
        message_need_to_be_send=src.message_need_to_be_send,
        start_at=src.start_at,
        end_at=src.end_at,
        status=Poll.STATUS_DRAFT,  # copied poll starts as draft
        vote_visibility=src.vote_visibility,
        created_by=request.user,
    )
    new_poll.tags.set(src.tags.all())

    # duplicate questions & choices
    for q in src.questions.prefetch_related("choices").all():
        new_q = Question.objects.create(
            poll=new_poll,
            title=q.title,
            qtype=q.qtype,
            allow_other=q.allow_other,
            order=q.order,
        )
        for c in q.choices.all():
            Choice.objects.create(question=new_q, label=c.label, order=c.order)

    messages.success(request, "Poll copied successfully.")
    return redirect("polls:list")


class PollDeleteView(LoginRequiredMixin, View):
    permission_flags = ["is_superuser"]

    def delete(self, request, pk, *args, **kwargs):
        poll = get_object_or_404(Poll, pk=pk)
        poll.delete()
        return JsonResponse({"success": True})


@login_required
@transaction.atomic
def poll_vote(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)

    if poll.status != Poll.STATUS_PUBLISHED and not request.user.is_superuser:
        raise Http404("Not found")

    if not poll.can_user_access(request.user) and not request.user.is_superuser:
        raise Http404("Not found")

    now = timezone.now()
    if poll.end_at and now > poll.end_at and not request.user.is_superuser:
        return render(
            request,
            "dashboard/polls/poll_vote.html",
            {"poll": poll, "questions": [], "poll_ended": True},
        )

    if PollResponse.objects.filter(poll=poll, user=request.user).exists():
        return redirect("polls:results", poll_id=poll.id)

    questions = poll.questions.prefetch_related("choices").all()

    if request.method == "POST":
        response = PollResponse.objects.create(poll=poll, user=request.user)

        for q in questions:
            use_other = request.POST.get(f"q_{q.id}_use_other") == "1"
            other_text = (request.POST.get(f"q_{q.id}_other_text") or "").strip()

            if q.allow_other and use_other and other_text:
                Vote.objects.create(
                    response=response, question=q, choice=None, other_text=other_text
                )
                continue

            if q.qtype == Question.TYPE_SINGLE:
                choice_id = request.POST.get(f"q_{q.id}_choice")
                if choice_id:
                    choice = Choice.objects.filter(id=choice_id, question=q).first()
                    if choice:
                        Vote.objects.create(
                            response=response, question=q, choice=choice, other_text=""
                        )
            else:
                choice_ids = request.POST.getlist(f"q_{q.id}_choice")
                choices = Choice.objects.filter(question=q, id__in=choice_ids)
                Vote.objects.bulk_create(
                    [
                        Vote(response=response, question=q, choice=c, other_text="")
                        for c in choices
                    ]
                )

        messages.success(
            request,
            "Thank you! Your response has been recorded. Results will be visible after the poll ends.",
        )
        return redirect("polls:list")

    return render(
        request,
        "dashboard/polls/poll_vote.html",
        {"poll": poll, "questions": questions, "poll_ended": False},
    )


@login_required
def poll_results(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    now = timezone.now()

    # unpublished polls → only superuser
    if poll.status != Poll.STATUS_PUBLISHED and not request.user.is_superuser:
        messages.warning(request, "Results are not available yet.")
        return redirect("polls:list")

    if poll.end_at and now < poll.end_at and not request.user.is_superuser:
        messages.warning(request, "Results will be visible after the poll ends.")
        return redirect("polls:list")

    if not poll.can_user_access(request.user) and not request.user.is_superuser:
        return redirect("polls:list")

    questions = poll.questions.prefetch_related("choices").all()

    show_voters = (
        poll.vote_visibility == Poll.VISIBILITY_SHOW
    ) and request.user.is_superuser

    result = []
    for q in questions:
        total = Vote.objects.filter(question=q).count()
        rows = []

        for c in q.choices.all():
            votes_qs = Vote.objects.filter(question=q, choice=c).select_related(
                "response__user"
            )
            cnt = votes_qs.count()
            pct = (cnt * 100 / total) if total else 0

            voters = []
            voters_json = "[]"
            if show_voters:
                voters = [v.response.user.get_full_name() for v in votes_qs]
                voters_json = json.dumps(voters)

            rows.append(
                {
                    "label": c.label,
                    "count": cnt,
                    "percent": round(pct, 1),
                    "voters": voters,
                    "voters_json": voters_json,
                }
            )

        other_votes_qs = (
            Vote.objects.filter(question=q, choice=None)
            .exclude(other_text="")
            .select_related("response__user")
        )
        other_count = other_votes_qs.count()
        other_pct = round((other_count * 100 / total), 1) if total else 0
        other_votes_list = list(other_votes_qs)
        other_texts = [v.other_text for v in other_votes_list]

        # Build numbered other items (option number continues after regular choices)
        choices_count = len(rows)
        single_pct = round((1 * 100 / total), 1) if total else 0
        other_items = [
            {
                "option_num": choices_count + i + 1,
                "text": v.other_text,
                "percent": single_pct,
                "voters_json": (
                    json.dumps([v.response.user.get_full_name()])
                    if show_voters
                    else "[]"
                ),
            }
            for i, v in enumerate(other_votes_list)
        ]

        result.append(
            {
                "question": q,
                "total": total,
                "choices": rows,
                "show_voters": show_voters,
                "other_count": other_count,
                "other_pct": other_pct,
                "other_texts": other_texts,
                "other_items": other_items,
            }
        )

    total_responses = PollResponse.objects.filter(poll=poll).count()

    return render(
        request,
        "dashboard/polls/poll_results.html",
        {
            "poll": poll,
            "result": result,
            "show_voters": show_voters,
            "total_responses": total_responses,
        },
    )
