from django import forms
from .models import MeetingSchedule, ClassRecording, Tag

# ── Recurrence choice constants ────────────────────────────────────────────
RECURRENCE_TYPE_CHOICES = [
    ("",        "Select"),
    ("daily",   "Daily"),
    ("weekly",  "Weekly"),
    ("monthly", "Monthly"),
    ("yearly",  "Yearly"),
]

WEEKDAY_CHOICES = [
    (0, "Sun"), (1, "Mon"), (2, "Tue"), (3, "Wed"),
    (4, "Thu"), (5, "Fri"), (6, "Sat"),
]

NTH_CHOICES = [
    ("", "Select"),
    (1, "First"), (2, "Second"), (3, "Third"),
    (4, "Fourth"), (5, "Fifth"), (6, "Last"),
]

MONTH_CHOICES = [
    ("",  "Select"),
    (1,  "Jan"), (2,  "Feb"), (3,  "Mar"), (4,  "Apr"),
    (5,  "May"), (6,  "Jun"), (7,  "Jul"), (8,  "Aug"),
    (9,  "Sep"), (10, "Oct"), (11, "Nov"), (12, "Dec"),
]

MONTHLY_MODE_CHOICES = [
    ("",             "Select"),
    ("day_of_month", "Day of Month"),
    ("nth_weekday",  "Nth Weekday"),
]

YEARLY_MODE_CHOICES = [
    ("",             "Select"),
    ("day_of_month", "Day of Month"),
    ("nth_weekday",  "Nth Weekday"),
]

END_MODE_CHOICES = [
    ("on",    "On (date)"),
    ("after", "After (occurrences)"),
]


class MeetingForm(forms.ModelForm):
    # ── Recurring toggle & core recurrence ────────────────────────────────
    is_recurring = forms.BooleanField(required=False, label="Recurring Meeting")

    recurrence_type = forms.ChoiceField(
        required=False,
        choices=RECURRENCE_TYPE_CHOICES,
        label="Recurrence Type",
    )
    interval = forms.IntegerField(
        required=False, min_value=1, label="Every (interval)", initial=1
    )

    # Weekly
    days_of_week = forms.MultipleChoiceField(
        required=False,
        choices=WEEKDAY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label="On (days)",
    )

    # End mode
    end_mode = forms.ChoiceField(
        required=False,
        choices=END_MODE_CHOICES,
        widget=forms.RadioSelect,
        label="End",
    )
    end_on_date = forms.DateField(required=False, label="End On Date")
    end_after_occurrences = forms.IntegerField(
        required=False, min_value=1, label="End After Occurrences"
    )

    # Monthly
    monthly_mode = forms.ChoiceField(
        required=False, choices=MONTHLY_MODE_CHOICES, label="Monthly Mode"
    )
    monthly_day_of_month = forms.IntegerField(
        required=False, min_value=1, max_value=31, label="Day of Month"
    )
    monthly_nth = forms.ChoiceField(
        required=False, choices=NTH_CHOICES, label="Nth"
    )
    monthly_weekday = forms.ChoiceField(
        required=False, choices=[("", "Select")] + list(WEEKDAY_CHOICES), label="Weekday"
    )

    # Yearly
    yearly_mode = forms.ChoiceField(
        required=False, choices=YEARLY_MODE_CHOICES, label="Yearly Mode"
    )
    yearly_month = forms.ChoiceField(
        required=False, choices=MONTH_CHOICES, label="Month"
    )
    yearly_day_of_month = forms.IntegerField(
        required=False, min_value=1, max_value=31, label="Day of Month"
    )
    yearly_nth = forms.ChoiceField(
        required=False, choices=NTH_CHOICES, label="Nth"
    )
    yearly_weekday = forms.ChoiceField(
        required=False, choices=[("", "Select")] + list(WEEKDAY_CHOICES), label="Weekday"
    )

    class Meta:
        model = MeetingSchedule
        fields = [
            'title', 'description', 'date', 'start_time', 'end_time',
            'meeting_url', 'password', 'is_sms',
            # notice toggles
            'enable_all_email_notification',
            'notice_3_weeks', 'notice_2_weeks', 'notice_1_week',
            'notice_1_day', 'notice_10_min',
        ]
        widgets = {
            'date':        forms.DateInput(attrs={'type': 'date'}),
            'start_time':  forms.TimeInput(attrs={'type': 'time'}),
            'end_time':    forms.TimeInput(attrs={'type': 'time'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['start_time'].input_formats = ['%H:%M']
        self.fields['end_time'].input_formats   = ['%H:%M']

    # ── Validation ─────────────────────────────────────────────────────────
    def clean(self):
        cleaned = super().clean()

        if not cleaned.get('is_recurring'):
            return cleaned  # Non-recurring: nothing extra to validate

        rtype    = cleaned.get('recurrence_type')
        interval = cleaned.get('interval')
        end_mode = cleaned.get('end_mode')

        if not rtype:
            self.add_error('recurrence_type', 'Recurrence type is required.')
        if not interval:
            self.add_error('interval', 'Interval is required.')
        if not end_mode:
            self.add_error('end_mode', 'End mode is required.')
        elif end_mode == 'on' and not cleaned.get('end_on_date'):
            self.add_error('end_on_date', 'End-on date is required.')
        elif end_mode == 'after' and not cleaned.get('end_after_occurrences'):
            self.add_error('end_after_occurrences', 'Number of occurrences is required.')

        if rtype == 'weekly' and not cleaned.get('days_of_week'):
            self.add_error('days_of_week', 'Select at least one day.')

        if rtype == 'monthly':
            mode = cleaned.get('monthly_mode')
            if not mode:
                self.add_error('monthly_mode', 'Monthly mode is required.')
            elif mode == 'day_of_month' and not cleaned.get('monthly_day_of_month'):
                self.add_error('monthly_day_of_month', 'Day of month is required.')
            elif mode == 'nth_weekday':
                if not cleaned.get('monthly_nth'):
                    self.add_error('monthly_nth', 'Nth is required.')
                if cleaned.get('monthly_weekday') in (None, ''):
                    self.add_error('monthly_weekday', 'Weekday is required.')

        if rtype == 'yearly':
            if not cleaned.get('yearly_month'):
                self.add_error('yearly_month', 'Month is required.')
            mode = cleaned.get('yearly_mode')
            if not mode:
                self.add_error('yearly_mode', 'Yearly mode is required.')
            elif mode == 'day_of_month' and not cleaned.get('yearly_day_of_month'):
                self.add_error('yearly_day_of_month', 'Day of month is required.')
            elif mode == 'nth_weekday':
                if not cleaned.get('yearly_nth'):
                    self.add_error('yearly_nth', 'Nth is required.')
                if cleaned.get('yearly_weekday') in (None, ''):
                    self.add_error('yearly_weekday', 'Weekday is required.')

        return cleaned


class RecordingForm(forms.ModelForm):
    class Meta:
        model = ClassRecording
        fields = ['meeting', 'recording_url', 'description']


# -------------------- Tag --------------------
class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = [
            "name",
            "order",
        ]



# from django import forms
# from .models import MeetingSchedule, ClassRecording

# class MeetingForm(forms.ModelForm):
#     class Meta:
#         model = MeetingSchedule
#         fields = ['title', 'description', 'date', 'start_time', 'end_time', 
#                   'meeting_url', 'password', 'is_sms']
#         widgets = {
#             'date': forms.DateInput(attrs={'type': 'date'}),
#             'start_time': forms.TimeInput(attrs={'type': 'time'}),
#             'end_time': forms.TimeInput(attrs={'type': 'time'}),
#             'description': forms.Textarea(attrs={'rows': 4}),
#         }

#     def __init__(self, *args, **kwargs):
#         super(MeetingForm, self).__init__(*args, **kwargs)
#         self.fields['start_time'].input_formats = ['%H:%M']
#         self.fields['end_time'].input_formats = ['%H:%M']

# class RecordingForm(forms.ModelForm):
#     class Meta:
#         model = ClassRecording
#         fields = ['meeting', 'recording_url', 'description']