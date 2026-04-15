from django.conf import settings
from django.db import models



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
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    committee = models.ForeignKey(CommitteeName, on_delete=models.CASCADE)
    position = models.ForeignKey(CommitteeTitle, on_delete=models.CASCADE)
    executive_year = models.ForeignKey(CommitteeYear, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user", "committee", "position", "executive_year")

    def __str__(self):
        return (
            f"{self.user} - {self.position} - {self.committee} - {self.executive_year}"
        )
