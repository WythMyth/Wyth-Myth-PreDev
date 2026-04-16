from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    ListView,
    UpdateView,
    View,
)

from accounts.models import User
from committee.forms import (
    CommitteeNameForm,
    CommitteeTitleForm,
    CommitteeYearForm,
    ExecutiveCommitteeForm,
)
from committee.models import (
    CommitteeName,
    CommitteeTitle,
    CommitteeYear,
    ExecutiveCommittee,
)
from poll.permission import PermissionRequiredMixin



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
        queryset = ExecutiveCommittee.objects.select_related(
            "user", "committee", "position", "executive_year"
        ).order_by("position__display_order", "executive_year__from_date")

        user_id = self.request.GET.get("user", "").strip()

        committee_id = self.request.GET.get("committee", "").strip()
        position_id = self.request.GET.get("position", "").strip()
        executive_year_id = self.request.GET.get("executive_year", "").strip()

        if user_id.isdigit():
            queryset = queryset.filter(user_id=user_id)
        if committee_id.isdigit():
            queryset = queryset.filter(committee_id=committee_id)
        if position_id.isdigit():
            queryset = queryset.filter(position_id=position_id)
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
            User.objects
            .only("id", "first_name", "middle_name", "last_name")
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
