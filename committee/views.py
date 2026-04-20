from collections import defaultdict
from itertools import groupby
from operator import attrgetter

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    ListView,
    UpdateView,
)

from accounts.models import User
from committee.forms import (
    CommitteeNameForm,
    CommitteeTitleForm,
    CommitteeYearForm,
    ExecutiveCommitteeForm,
    PastExecutiveCommitteeForm,
    PastSubCommitteeForm,
)
from committee.models import (
    CommitteeName,
    CommitteeTitle,
    CommitteeYear,
    ExecutiveCommittee,
    PastExecutiveCommittee,
    PastSubCommittee,
)
from committee.utils import merge_year_ranges
from poll.permission import PermissionRequiredMixin


class ExecutivePageView(View):
    template_name = "dashboard/committee/executive_page.html"

    def get(self, request):

        committees = CommitteeName.objects.filter(is_show_executive=True).order_by(
            "display_order", "committee_name"
        )

        latest_year = CommitteeYear.objects.aggregate(latest=Max("from_date"))["latest"]

        committee_sections = []

        # queryset
        base_qs = ExecutiveCommittee.objects.select_related(
            "user", "committee", "executive_year"
        ).prefetch_related("position")

        for committee in committees:
            code = (committee.code or "").strip()

            # ==============================
            # Former Presidents (FP)
            # ==============================
            if code == "FP":

                ecs = base_qs.filter(committee__code="FP").order_by("user_id")

                grouped = []

                for user_id, rows in groupby(ecs, key=attrgetter("user_id")):
                    rows = list(rows)
                    user = rows[0].user

                    position_map = defaultdict(list)

                    for r in rows:
                        if not r.executive_year:
                            continue

                        #positions (ManyToMany)
                        for pos in r.position.all():
                            position_map[pos.title].append(
                                {
                                    "from_date": r.executive_year.from_date,
                                    "to_date": r.executive_year.to_date,
                                    "display_order": pos.display_order or 999,
                                }
                            )

                    pairs = []

                    for title, items in position_map.items():

                        # Merge continuous ranges
                        merged_ranges = merge_year_ranges(items)

                        year_strings = []
                        latest_to_date = None

                        for start, end in reversed(merged_ranges):
                            year_strings.append(f"{start.year}-{end.year}")

                            if not latest_to_date or end > latest_to_date:
                                latest_to_date = end

                        pairs.append(
                            {
                                "title": title,
                                "year": ", ".join(year_strings),
                                "latest_to_date": latest_to_date,
                                "display_order": items[0]["display_order"],
                            }
                        )

                    if not pairs:
                        continue

                    # Sort by latest year first
                    pairs.sort(
                        key=lambda p: (-p["latest_to_date"].year, p["display_order"])
                    )

                    top_display_order = min(p["display_order"] for p in pairs)

                    grouped.append(
                        {
                            "user": user,
                            "position_year_pairs": [
                                (p["title"], p["year"]) for p in pairs
                            ],
                            "top_display_order": top_display_order,
                        }
                    )

                grouped.sort(key=lambda x: x["top_display_order"])

                if grouped:
                    committee_sections.append(
                        {
                            "committee": committee,
                            "type": "former_leaders",
                            "former_presidents": grouped,
                        }
                    )

                continue

            # ==============================
            # Latest Executive Committee
            # ==============================
            members = list(
                base_qs.filter(
                    committee=committee,
                    executive_year__from_date=latest_year,
                )
            )

            # Python-side sorting (since ManyToMany)
            members.sort(
                key=lambda m: min(
                    [p.display_order or 999 for p in m.position.all()] or [999]
                )
            )

            if members:
                committee_sections.append(
                    {
                        "committee": committee,
                        "type": "grid",
                        "members": members,
                        "year": members[0].executive_year.year_range,
                    }
                )

        # ==============================
        # Past 3 Executive Years
        # ==============================
        past_years_qs = CommitteeYear.objects.exclude(from_date=latest_year).order_by(
            "-from_date"
        )[:3]

        past_committee_years = [year.year_range for year in past_years_qs]

        # latest_executive = (
        #     PastExecutiveCommittee.objects.filter(is_active=True)
        #     .order_by("-id")
        #     .first()
        # )

        context = {
            "committee_sections": committee_sections,
            "past_executive_committee_years": past_committee_years,
            # "latest_executive": latest_executive,
        }

        return render(request, self.template_name, context)


# ----------------------
# CommitteeName Views
# ----------------------
class CommitteeNameListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = CommitteeName
    template_name = "dashboard/committee/committee_name_list.html"
    context_object_name = "committee_names"
    paginate_by = 50
    ordering = ["display_order"]
    permission_flags = ["is_superuser", "is_committee"]


class CommitteeNameCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = CommitteeName
    form_class = CommitteeNameForm
    template_name = "dashboard/committee/committee_name_form.html"
    success_url = reverse_lazy("committee:committee_name_list")
    permission_flags = ["is_superuser", "is_committee"]


class CommitteeNameUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = CommitteeName
    form_class = CommitteeNameForm
    template_name = "dashboard/committee/committee_name_form.html"
    success_url = reverse_lazy("committee:committee_name_list")
    permission_flags = ["is_superuser", "is_committee"]


class CommitteeNameDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    model = CommitteeName
    permission_flags = ["is_superuser", "is_committee"]

    def delete(self, request, *args, **kwargs):
        obj = get_object_or_404(CommitteeName, pk=kwargs["pk"])
        obj.delete()
        return JsonResponse({"success": True})


# ----------------------
# CommitteeYear Views
# ----------------------
class CommitteeYearListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = CommitteeYear
    template_name = "dashboard/committee/committee_year_list.html"
    context_object_name = "committee_years"
    paginate_by = 50
    ordering = ["from_date"]
    permission_flags = ["is_superuser", "is_committee"]


class CommitteeYearCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = CommitteeYear
    form_class = CommitteeYearForm
    template_name = "dashboard/committee/committee_year_form.html"
    success_url = reverse_lazy("committee:committee_year_list")
    permission_flags = ["is_superuser", "is_committee"]


class CommitteeYearUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = CommitteeYear
    form_class = CommitteeYearForm
    template_name = "dashboard/committee/committee_year_form.html"
    success_url = reverse_lazy("committee:committee_year_list")
    permission_flags = ["is_superuser", "is_committee"]


class CommitteeYearDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    model = CommitteeYear
    permission_flags = ["is_superuser", "is_committee"]

    def delete(self, request, *args, **kwargs):
        obj = get_object_or_404(CommitteeYear, pk=kwargs["pk"])
        obj.delete()
        return JsonResponse({"success": True})


# ----------------------
# CommitteeTitle Views
# ----------------------
class CommitteeTitleListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = CommitteeTitle
    template_name = "dashboard/committee/committee_title_list.html"
    context_object_name = "committee_titles"
    paginate_by = 50
    ordering = [
        "display_order",
    ]
    permission_flags = ["is_superuser", "is_committee"]


class CommitteeTitleCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = CommitteeTitle
    form_class = CommitteeTitleForm
    template_name = "dashboard/committee/committee_title_form.html"
    success_url = reverse_lazy("committee:committee_title_list")
    permission_flags = ["is_superuser", "is_committee"]


class CommitteeTitleUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = CommitteeTitle
    form_class = CommitteeTitleForm
    template_name = "dashboard/committee/committee_title_form.html"
    success_url = reverse_lazy("committee:committee_title_list")
    permission_flags = ["is_superuser", "is_committee"]


class CommitteeTitleDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    model = CommitteeTitle
    permission_flags = ["is_superuser", "is_committee"]

    def delete(self, request, *args, **kwargs):
        obj = get_object_or_404(CommitteeTitle, pk=kwargs["pk"])
        obj.delete()
        return JsonResponse({"success": True})


# ----------------------
# ExecutiveCommittee Views
# ----------------------
class ExecutiveCommitteeListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = ExecutiveCommittee
    template_name = "dashboard/committee/executivecommittee_list.html"
    context_object_name = "executive_committees"
    paginate_by = 50
    permission_flags = ["is_superuser", "is_committee"]

    def get_queryset(self):
        queryset = (
            ExecutiveCommittee.objects.select_related(
                "user", "committee", "executive_year"
            )
            .prefetch_related("position")
            .order_by(
                "committee__display_order",
                "executive_year__from_date",
                "user__first_name",
            )
        )

        user_id = self.request.GET.get("user", "").strip()

        committee_id = self.request.GET.get("committee", "").strip()
        position_id = self.request.GET.get("position", "").strip()
        executive_year_id = self.request.GET.get("executive_year", "").strip()

        if user_id.isdigit():
            queryset = queryset.filter(user_id=user_id)
        if committee_id.isdigit():
            queryset = queryset.filter(committee_id=committee_id)
        if position_id.isdigit():
            queryset = queryset.filter(position__id=position_id)
        if executive_year_id.isdigit():
            queryset = queryset.filter(executive_year_id=executive_year_id)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Preserve filter values in template
        context["user_filter"] = self.request.GET.get("user", "")
        context["committee_filter"] = self.request.GET.get("committee", "")
        context["position_filter"] = self.request.GET.get("position", "")
        context["executive_year_filter"] = self.request.GET.get("executive_year", "")
        context["user_choices"] = (
            User.objects.only("id", "first_name", "middle_name", "last_name")
            .filter(is_active=True)
            .order_by("first_name")
        )

        # Pass choices dynamically from the related models
        context["committee_choices"] = CommitteeName.objects.exclude(
            code__startswith="RE-"
        ).order_by("committee_name")

        context["position_choices"] = CommitteeTitle.objects.all()
        context["executive_year_choices"] = CommitteeYear.objects.all().order_by(
            "from_date"
        )

        return context


class ExecutiveCommitteeCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, CreateView
):
    model = ExecutiveCommittee
    form_class = ExecutiveCommitteeForm
    template_name = "dashboard/committee/executivecommittee_form.html"
    success_url = reverse_lazy("committee:executive_committee_list")
    permission_flags = ["is_superuser", "is_committee"]


class ExecutiveCommitteeUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, UpdateView
):
    model = ExecutiveCommittee
    form_class = ExecutiveCommitteeForm
    template_name = "dashboard/committee/executivecommittee_form.html"
    success_url = reverse_lazy("committee:executive_committee_list")
    permission_flags = ["is_superuser", "is_committee"]


class ExecutiveCommitteeDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    model = ExecutiveCommittee
    permission_flags = ["is_superuser", "is_committee"]

    def delete(self, request, *args, **kwargs):
        executive_committee = get_object_or_404(ExecutiveCommittee, pk=kwargs["pk"])
        executive_committee.delete()
        return JsonResponse({"success": True})


# -------------------- Past Executive Committee --------------------
class PastExecutiveCommitteeListView(
    LoginRequiredMixin, PermissionRequiredMixin, ListView
):
    model = PastExecutiveCommittee
    template_name = "dashboard/page/past_executive_list.html"
    context_object_name = "committees"
    ordering = ["title"]
    permission_flags = ["is_superuser"]


class PastExecutiveCommitteeCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, CreateView
):
    model = PastExecutiveCommittee
    form_class = PastExecutiveCommitteeForm
    template_name = "dashboard/page/past_executive_form.html"
    success_url = reverse_lazy("committee:past_executive_list")
    permission_flags = ["is_superuser"]


class PastExecutiveCommitteeUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, UpdateView
):
    model = PastExecutiveCommittee
    form_class = PastExecutiveCommitteeForm
    template_name = "dashboard/page/past_executive_form.html"
    success_url = reverse_lazy("committee:past_executive_list")
    permission_flags = ["is_superuser"]


class PastExecutiveCommitteeDeleteView(
    LoginRequiredMixin, PermissionRequiredMixin, View
):
    permission_flags = ["is_superuser"]

    def delete(self, request, *args, **kwargs):
        committee = get_object_or_404(PastExecutiveCommittee, pk=kwargs["pk"])
        committee.delete()
        return JsonResponse({"success": True})


# -------------------- Past Sub Committee --------------------
class PastSubCommitteeListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = PastSubCommittee
    template_name = "dashboard/page/past_sub_list.html"
    context_object_name = "subcommittees"
    ordering = ["title"]
    permission_flags = ["is_superuser"]


class PastSubCommitteeCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, CreateView
):
    model = PastSubCommittee
    form_class = PastSubCommitteeForm
    template_name = "dashboard/page/past_sub_form.html"
    success_url = reverse_lazy("committee:past_sub_list")
    permission_flags = ["is_superuser"]


class PastSubCommitteeUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, UpdateView
):
    model = PastSubCommittee
    form_class = PastSubCommitteeForm
    template_name = "dashboard/page/past_sub_form.html"
    success_url = reverse_lazy("committee:past_sub_list")
    permission_flags = ["is_superuser"]


class PastSubCommitteeDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_flags = ["is_superuser"]

    def delete(self, request, *args, **kwargs):
        subcommittee = get_object_or_404(PastSubCommittee, pk=kwargs["pk"])
        subcommittee.delete()
        return JsonResponse({"success": True})