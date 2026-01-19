from django import forms
from .models import MeetingSchedule, ClassRecording

class MeetingForm(forms.ModelForm):
    class Meta:
        model = MeetingSchedule
        fields = ['title', 'description', 'date', 'start_time', 'end_time', 
                  'meeting_url', 'password', 'is_sms']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super(MeetingForm, self).__init__(*args, **kwargs)
        self.fields['start_time'].input_formats = ['%H:%M']
        self.fields['end_time'].input_formats = ['%H:%M']

class RecordingForm(forms.ModelForm):
    class Meta:
        model = ClassRecording
        fields = ['meeting', 'recording_url', 'description']