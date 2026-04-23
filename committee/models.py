from django.conf import settings
from django.db import models
from django.db.models import Q

User = settings.AUTH_USER_MODEL


# =====================base model =========================
class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ----------------------
# CommitteeName Model
# ----------------------
class CommitteeName(BaseModel):
    committee_name = models.CharField(max_length=255, blank=True, null=True)
    code = models.CharField(max_length=10, blank=True, null=True)
    is_show_executive = models.BooleanField(default=True)
    is_show_past_sub_committee = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.committee_name


# ----------------------
# CommitteeYear Model
# ----------------------
class CommitteeYear(BaseModel):
    from_date = models.DateField(
        blank=True, null=True, help_text="Start date of the committee period"
    )
    to_date = models.DateField(
        blank=True, null=True, help_text="End date of the committee period"
    )

    def __str__(self):
        """Return readable format like '2020–2021'."""
        if self.from_date and self.to_date:
            return f"{self.from_date.year}-{self.to_date.year}"
        elif self.from_date:
            return str(self.from_date.year)
        return "Unknown"

    @property
    def year_range(self):
        """Return string format of year range (for display)."""
        if self.from_date and self.to_date:
            return f"{self.from_date.year}-{self.to_date.year}"
        return "N/A"


# ----------------------
# CommitteeTitle Model
# ----------------------
class CommitteeTitle(BaseModel):
    title = models.CharField(max_length=255, blank=True, null=True)
    display_order = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return self.title


# ----------------------
# UserCommitteePosition Model
# ----------------------
class ExecutiveCommittee(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE,related_name="executive_committees")
    committee = models.ForeignKey(CommitteeName, on_delete=models.CASCADE, related_name="executive_committees")
    position = models.ManyToManyField(
        CommitteeTitle, blank=True, related_name="executive_committees"
    )
    executive_year = models.ForeignKey(CommitteeYear, on_delete=models.CASCADE, related_name="executive_committees")

    class Meta:
        constraints = [
            # Unique constraint for user, committee, and executive_year
            models.UniqueConstraint(
                fields=["user", "committee", "executive_year"],
                name="unique_user_committee_year",
            ),
        ]

    def __str__(self):
        positions = ", ".join([p.title for p in self.position.all()]) if self.position.exists() else "No Position"
        return f"{self.user.get_full_name()} - {self.committee.committee_name} ({positions})"


class PastExecutiveCommittee(BaseModel):
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True, null=True)
    images = models.ImageField(upload_to="home/committee/images/", blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class PastSubCommittee(BaseModel):
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True, null=True)
    images = models.ImageField(upload_to="home/committee/images/", blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title