from django import forms

from committee.models import (
    CommitteeName,
    CommitteeTitle,
    CommitteeYear,
    ExecutiveCommittee,
    PastExecutiveCommittee,
    PastSubCommittee,
)


# ----------------------
# CommitteeName Form
# ----------------------
class CommitteeNameForm(forms.ModelForm):
    class Meta:
        model = CommitteeName
        fields = [
            "committee_name",
            "code",
            "is_show_executive",
            "is_show_past_sub_committee",
            "display_order",
        ]


# ----------------------
# CommitteeYear Form
# ----------------------
class CommitteeYearForm(forms.ModelForm):
    class Meta:
        model = CommitteeYear
        fields = ["from_date", "to_date"]


# ----------------------
# CommitteeTitle Form
# ----------------------
class CommitteeTitleForm(forms.ModelForm):
    class Meta:
        model = CommitteeTitle
        fields = ["title", "display_order"]


# ----------------------
# ExecutiveCommittee Form
# ----------------------
class ExecutiveCommitteeForm(forms.ModelForm):
    position = forms.ModelMultipleChoiceField(
        queryset=CommitteeTitle.objects.all().order_by("display_order"),
        widget=forms.SelectMultiple,
        required=False,
        label="Positions",
    )

    class Meta:
        model = ExecutiveCommittee
        fields = ["user", "committee", "position", "executive_year"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["committee"].queryset = (
            self.fields["committee"]
            .queryset.exclude(code__startswith="RE-")
            .order_by("committee_name")
        )

        # Order users by name
        self.fields["user"].queryset = self.fields["user"].queryset.order_by(
            "first_name"
        )
        self.fields["executive_year"].queryset = self.fields[
            "executive_year"
        ].queryset.order_by("from_date")

        # Add custom CSS classes to fields
        self.fields["user"].widget.attrs.update({"class": "w-full"})
        self.fields["committee"].widget.attrs.update({"class": "w-full"})
        self.fields["position"].widget.attrs.update(
            {"class": "w-full", "id": "positionSelect"}
        )
        self.fields["executive_year"].widget.attrs.update(
            {"class": "w-full border border-gray-300 rounded-lg px-3 py-2"}
        )

class PastExecutiveCommitteeForm(forms.ModelForm):
    class Meta:
        model = PastExecutiveCommittee
        fields = ["title", "description", "is_active","images"]


class PastSubCommitteeForm(forms.ModelForm):
    class Meta:
        model = PastSubCommittee
        fields = ["title", "description", "is_active","images"]