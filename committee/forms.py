from django import forms

from committee.models import (
    CommitteeName,
    CommitteeTitle,
    CommitteeYear,
    ExecutiveCommittee,
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

        # Order users by name (choose the field you use)
        self.fields["user"].queryset = self.fields["user"].queryset.order_by(
            "first_name"
        )
        self.fields["executive_year"].queryset = self.fields[
            "executive_year"
        ].queryset.order_by("from_date")
