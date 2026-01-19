from datetime import datetime, timedelta
import json
from django.http import JsonResponse
from datetime import timedelta
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.timezone import now
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)
from django.utils.timezone import localtime, is_naive, make_aware
from openpyxl import load_workbook
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from accounts.models import User

from .forms import MeetingForm, RecordingForm
from .models import ClassRecording, MeetingSchedule


# Meeting Views
# class MeetingListView(LoginRequiredMixin, ListView):
#     model = MeetingSchedule
#     template_name = "meetings/meeting_list.html"
#     context_object_name = "meetings"

#     def get_queryset(self):
#         today = timezone.localtime().date()  # ensure local date in Asia/Dhaka
#         return MeetingSchedule.objects.filter(
#             is_expired=False,
#             date__gte=today
#         ).order_by('title', 'date', 'start_time')

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         now = localtime(timezone.now())  # Asia/Dhaka timezone
#         today = now.date()
#         current_time = now.time()
#         context['now'] = now
#         context['today'] = today
#         context['current_time'] = current_time
#         context['time_plus_15'] = (now + timedelta(minutes=10)).time()

#         for meeting in context["meetings"]:
#             meeting.can_join = False

#             if meeting.date and meeting.end_time:
#                 meeting_end = datetime.combine(meeting.date, meeting.end_time)

#                 if is_naive(meeting_end):
#                     meeting_end = make_aware(meeting_end)

#                 # ✅ Mark meeting as expired if end time is past now
#                 if meeting_end < now and not meeting.is_expired:
#                     meeting.is_expired = True
#                     meeting.save(update_fields=["is_expired"])

#             if meeting.date == today:
#                 meeting_start = datetime.combine(meeting.date, meeting.start_time)
#                 meeting_end = datetime.combine(meeting.date, meeting.end_time)

#                 if is_naive(meeting_start):
#                     meeting_start = make_aware(meeting_start)
#                 if is_naive(meeting_end):
#                     meeting_end = make_aware(meeting_end)

#                 if meeting_end < meeting_start:
#                     meeting_end += timedelta(days=1)

#                 start_with_buffer = meeting_start - timedelta(minutes=15)

#                 if start_with_buffer <= now <= meeting_end:
#                     meeting.can_join = True

#         # ✅ Add balance if user is superuser
#         if self.request.user.is_superuser:
#             total_investment = (
#                 User.objects.aggregate(Sum("balance"))["balance__sum"] or 0
#             )
#             context["total_balance"] = total_investment
#         else:
#             context["total_balance"] = self.request.user.balance

#         return context

class MeetingListView(LoginRequiredMixin, ListView):
    model = MeetingSchedule
    template_name = "meetings/meeting_list.html"
    context_object_name = "meetings"
    paginate_by = 20
    def get_queryset(self):
        today = timezone.localtime().date()
        qs = MeetingSchedule.objects.all()

        # Order latest date first
        qs = qs.order_by('is_expired', '-date', '-start_time')

        # Filters
        title = self.request.GET.get('title', '').strip()
        from_date = self.request.GET.get('from_date')
        to_date = self.request.GET.get('to_date')
        status = self.request.GET.get('status')

        if title:
            qs = qs.filter(title__icontains=title)

        if from_date:
            qs = qs.filter(date__gte=from_date)

        if to_date:
            qs = qs.filter(date__lte=to_date)

        if status == "active":
            qs = qs.filter(is_expired=False)
        elif status == "expired":
            qs = qs.filter(is_expired=True)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Filters in context for template
        context["status_filter"] = self.request.GET.get("status", "")
        context["title_filter"] = self.request.GET.get("title", "")
        context["from_date"] = self.request.GET.get("from_date", "")
        context["to_date"] = self.request.GET.get("to_date", "")

        # ✅ Add balance if user is superuser
        if self.request.user.is_superuser:
            total_investment = (
                User.objects.aggregate(Sum("balance"))["balance__sum"] or 0
            )
            context["total_balance"] = total_investment
        else:
            context["total_balance"] = self.request.user.balance

        return context

class MeetingDetailView(LoginRequiredMixin, DetailView):
    model = MeetingSchedule
    template_name = "meetings/meeting_detail.html"
    context_object_name = "meeting"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["recordings"] = self.object.recording.all()
        # Total balance logic
        if self.request.user.is_superuser:
            total_investment = (
                User.objects.aggregate(Sum("balance"))["balance__sum"] or 0
            )
            context["total_balance"] = total_investment
        else:
            context["total_balance"] = self.request.user.balance
        return context


class MeetingCreateView(LoginRequiredMixin, CreateView):
    model = MeetingSchedule
    form_class = MeetingForm
    template_name = "meetings/meeting_form.html"
    success_url = reverse_lazy("meeting-list")

    def form_valid(self, form):
        form.instance.meeting_user = self.request.user
        messages.success(self.request, "Meeting created successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Total balance logic
        if self.request.user.is_superuser:
            total_investment = (
                User.objects.aggregate(Sum("balance"))["balance__sum"] or 0
            )
            context["total_balance"] = total_investment
        else:
            context["total_balance"] = self.request.user.balance
        return context


class MeetingUpdateView(LoginRequiredMixin, UpdateView):
    model = MeetingSchedule
    form_class = MeetingForm
    template_name = "meetings/meeting_form.html"
    success_url = reverse_lazy("meeting-list")

    def form_valid(self, form):
        messages.success(self.request, "Meeting updated successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Total balance logic
        if self.request.user.is_superuser:
            total_investment = (
                User.objects.aggregate(Sum("balance"))["balance__sum"] or 0
            )
            context["total_balance"] = total_investment
        else:
            context["total_balance"] = self.request.user.balance
        return context


# class MeetingDeleteView(LoginRequiredMixin, DeleteView):
#     model = MeetingSchedule
#     template_name = "meetings/meeting_confirm_delete.html"
#     success_url = reverse_lazy("meeting-list")

#     def delete(self, request, *args, **kwargs):
#         messages.success(request, "Meeting deleted successfully!")
#         return super().delete(request, *args, **kwargs)
class MeetingDeleteView(LoginRequiredMixin, DeleteView):
    model = MeetingSchedule
    template_name = "meetings/meeting_confirm_delete.html"
    success_url = reverse_lazy("meeting-list")

    def delete(self, request, *args, **kwargs):
        # Store meeting details before deletion
        meeting = self.get_object()
        meeting_title = meeting.title
        meeting_date = meeting.date
        meeting_time = meeting.start_time
        deleted_by = request.user.get_full_name() or request.user.username
        
        # Check if the user is a superuser
        if request.user.is_superuser:
            # Get all users with valid email addresses
            users = User.objects.filter(email__isnull=False).exclude(email='')
            
            # Send email to all users
            self.send_deletion_notification_email(
                users, meeting_title, meeting_date, meeting_time, deleted_by
            )
        
        messages.success(request, "Meeting deleted successfully!")
        return super().delete(request, *args, **kwargs)
    
    def send_deletion_notification_email(self, users, meeting_title, meeting_date, meeting_time, deleted_by):
        """Send HTML email notification to all users about meeting deletion"""
        subject = f"Meeting Cancelled: {meeting_title}"
        
        # Context data for the template
        context = {
            'meeting_title': meeting_title,
            'meeting_date': meeting_date,
            'meeting_time': meeting_time,
            'deleted_by': deleted_by,
        }
        
        # Render HTML template
        html_content = render_to_string('emails/meeting_deleted_email.html', context)
        
        # Optional: Create a plain text version as fallback
        text_content = f"""
Dear User,

We would like to inform you that the following meeting has been cancelled:

Meeting Details:
- Title: {meeting_title}
- Date: {meeting_date}
- Time: {meeting_time}
- Cancelled by: {deleted_by}

We apologize for any inconvenience this may cause.

Best regards,
Meeting Management Team
        """
        
        # Get recipient email addresses
        recipient_emails = [user.email for user in users if user.email]
        
        if recipient_emails:
            try:
                # Create EmailMultiAlternatives instance
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,  # Plain text version
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=recipient_emails,
                )
                
                # Attach HTML version
                email.attach_alternative(html_content, "text/html")
                
                # Send the email
                email.send(fail_silently=False)
                
                print(f"Meeting deletion notification sent to {len(recipient_emails)} users")
            except Exception as e:
                print(f"Error sending meeting deletion notification: {str(e)}")


class MeetingCopyView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        original = get_object_or_404(MeetingSchedule, pk=pk)
        copied = MeetingSchedule.objects.create(
            meeting_user=request.user,
            title=f"{original.title} (Copy)",
            description=original.description,
            date=original.date,
            start_time=original.start_time,
            end_time=original.end_time,
            meeting_url=original.meeting_url,
            password=original.password,
            is_sms=original.is_sms,
        )
        return JsonResponse({'status': 'success', 'copied_id': copied.pk})

# Recording Views
# class RecordingListView(LoginRequiredMixin, ListView):
#     model = ClassRecording
#     template_name = "recordings/recording_list.html"
#     context_object_name = "recordings"

#     def get_queryset(self):
#         return ClassRecording.objects.select_related('meeting').order_by('-meeting__date')

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         # Total balance logic
#         if self.request.user.is_superuser:
#             total_investment = (
#                 User.objects.aggregate(Sum("balance"))["balance__sum"] or 0
#             )
#             context["total_balance"] = total_investment
#         else:
#             context["total_balance"] = self.request.user.balance
#         return context

class RecordingListView(LoginRequiredMixin, ListView):
    model = ClassRecording
    template_name = "recordings/recording_list.html"
    context_object_name = "recordings"
    paginate_by= 20

    def get_queryset(self):
        queryset = ClassRecording.objects.select_related('meeting').order_by('-meeting__date')

        # filters
        title = self.request.GET.get('title', '').strip()
        from_date = self.request.GET.get('from_date', '').strip()
        to_date = self.request.GET.get('to_date', '').strip()

        if title:
            queryset = queryset.filter(meeting__title__icontains=title)

        if from_date:
            queryset = queryset.filter(meeting__date__gte=from_date)

        if to_date:
            queryset = queryset.filter(meeting__date__lte=to_date)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Total balance logic
        if self.request.user.is_superuser:
            total_investment = (
                User.objects.aggregate(Sum("balance"))["balance__sum"] or 0
            )
            context["total_balance"] = total_investment
        else:
            context["total_balance"] = self.request.user.balance

        # Preserve filter values in template
        context['title_filter'] = self.request.GET.get('title', '')
        context['from_date_filter'] = self.request.GET.get('from_date', '')
        context['to_date_filter'] = self.request.GET.get('to_date', '')

        return context

class RecordingDetailView(LoginRequiredMixin, DetailView):
    model = ClassRecording
    template_name = "recordings/recording_detail.html"
    context_object_name = "recording"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Total balance logic
        if self.request.user.is_superuser:
            total_investment = (
                User.objects.aggregate(Sum("balance"))["balance__sum"] or 0
            )
            context["total_balance"] = total_investment
        else:
            context["total_balance"] = self.request.user.balance
        return context


class RecordingCreateView(LoginRequiredMixin, CreateView):
    model = ClassRecording
    form_class = RecordingForm
    template_name = "recordings/recording_form.html"
    success_url = reverse_lazy("recording-list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Only show meetings created by the current user
        form.fields["meeting"].queryset = MeetingSchedule.objects.filter(
            meeting_user=self.request.user, is_expired=False
        )
        return form

    def form_valid(self, form):
        messages.success(self.request, "Recording created successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Total balance logic
        if self.request.user.is_superuser:
            total_investment = (
                User.objects.aggregate(Sum("balance"))["balance__sum"] or 0
            )
            context["total_balance"] = total_investment
        else:
            context["total_balance"] = self.request.user.balance
        return context


class RecordingUpdateView(LoginRequiredMixin, UpdateView):
    model = ClassRecording
    form_class = RecordingForm
    template_name = "recordings/recording_form.html"
    success_url = reverse_lazy("recording-list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Only show meetings created by the current user
        form.fields["meeting"].queryset = MeetingSchedule.objects.filter(
            meeting_user=self.request.user
        )
        return form

    def form_valid(self, form):
        messages.success(self.request, "Recording updated successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Total balance logic
        if self.request.user.is_superuser:
            total_investment = (
                User.objects.aggregate(Sum("balance"))["balance__sum"] or 0
            )
            context["total_balance"] = total_investment
        else:
            context["total_balance"] = self.request.user.balance
        return context


class RecordingDeleteView(LoginRequiredMixin, DeleteView):
    model = ClassRecording
    template_name = "recordings/recording_confirm_delete.html"
    success_url = reverse_lazy("recording-list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Recording deleted successfully!")
        return super().delete(request, *args, **kwargs)


@login_required
def meeting_upload(request):
    """
    View function to upload Excel file containing meeting data.
    The file should have the following columns:
    - title
    - description
    - date (YYYY-MM-DD)
    - start_time
    - end_time
    - meeting_url
    - password
    - is_sms (optional, True/False)
    """
    template = "meetings/meeting_upload.html"

    if request.method == "POST" and "file" in request.FILES:
        file = request.FILES["file"]

        # Check if the file is an Excel file
        if file.name.endswith(".xlsx"):
            try:
                wb = load_workbook(file)
                sheet = wb.active
                success_count = 0
                error_count = 0
                errors = []

                # Start from row 2 (assuming row 1 has headers)
                for row in range(2, sheet.max_row + 1):
                    try:
                        # Extract values from the sheet
                        title = sheet.cell(row=row, column=1).value
                        description = sheet.cell(row=row, column=2).value
                        date_value = sheet.cell(row=row, column=3).value
                        start_time = str(sheet.cell(row=row, column=4).value)
                        end_time = str(sheet.cell(row=row, column=5).value)
                        meeting_url = sheet.cell(row=row, column=6).value
                        password = sheet.cell(row=row, column=7).value

                        # Check for is_sms column, default to False if not present
                        is_sms = False
                        if sheet.max_column >= 8:
                            is_sms_value = sheet.cell(row=row, column=8).value
                            if isinstance(is_sms_value, bool):
                                is_sms = is_sms_value
                            elif isinstance(is_sms_value, str):
                                is_sms = is_sms_value.lower() in ["true", "yes", "1"]

                        # Skip empty rows
                        if not title:
                            continue

                        # Check if meeting with same title and date exists
                        existing_meetings = MeetingSchedule.objects.filter(
                            meeting_user=request.user, title=title, date=date_value
                        )

                        # Delete existing meetings with same title and date if found
                        if existing_meetings.exists():
                            existing_meetings.delete()

                        # Create new meeting
                        MeetingSchedule.objects.create(
                            meeting_user=request.user,
                            title=title,
                            description=description,
                            date=date_value,
                            start_time=start_time,
                            end_time=end_time,
                            meeting_url=meeting_url,
                            password=password,
                            is_sms=is_sms,
                        )
                        success_count += 1

                    except Exception as e:
                        error_count += 1
                        errors.append(f"Error at row {row}: {str(e)}")
                        continue

                # Prepare result message
                if success_count > 0:
                    messages.success(
                        request, f"{success_count} meetings uploaded successfully."
                    )

                if error_count > 0:
                    error_message = f"{error_count} meetings failed to upload. "
                    if errors:
                        error_message += f"First error: {errors[0]}"
                    messages.error(request, error_message)

                return redirect("meeting-list")

            except Exception as e:
                messages.error(request, f"Error processing file: {str(e)}")
        else:
            messages.error(request, "Please upload a valid Excel (.xlsx) file!")
    context = {}
    if request.user.is_superuser:
        # Calculate total investment from all users
        total_investment = (
            User.objects.all().aggregate(Sum("balance"))["balance__sum"] or 0
        )
        context["total_balance"] = total_investment
    else:
        context["total_balance"] = request.user.balance
    return render(request, template, context)

@login_required
def download_meeting_template(request):
    """Provides a template Excel file for meeting uploads"""
    from django.http import HttpResponse
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active

    # Add headers
    headers = [
        "Title",
        "Description",
        "Date (YYYY-MM-DD)",
        "Start Time",
        "End Time",
        "Meeting URL",
        "Password",
        "Send SMS (True/False)",
    ]

    for col_num, header in enumerate(headers, 1):
        ws.cell(row=1, column=col_num).value = header

    # Example row
    example_data = [
        "Weekly Team Meeting",
        "Regular team sync-up meeting",
        "2025-05-27",
        "10:00",
        "11:00",
        "https://example.com/meeting",
        "pass123",
        "False",
    ]

    for col_num, value in enumerate(example_data, 1):
        ws.cell(row=2, column=col_num).value = value

    # Create the HTTP response
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        'attachment; filename="meeting_upload_template.xlsx"'
    )

    wb.save(response)
    return response

class CalendarView(LoginRequiredMixin, View):
    template_name = "meetings/calendar.html"

    def get(self, request, *args, **kwargs):
        today = timezone.localdate()
        meetings = MeetingSchedule.objects.filter(date__gte=today).order_by("date", "start_time")

        event_data = []
        for meeting in meetings:
            try:
                if not meeting.start_time or not meeting.end_time:
                    continue

                start_datetime = datetime.combine(meeting.date, meeting.start_time)
                end_datetime = datetime.combine(meeting.date, meeting.end_time)

                if timezone.is_naive(start_datetime):
                    start_datetime = timezone.make_aware(start_datetime)
                if timezone.is_naive(end_datetime):
                    end_datetime = timezone.make_aware(end_datetime)  

                # Handle crossing midnight
                if end_datetime < start_datetime:
                    end_datetime += timedelta(days=1)

                event_data.append(
                    {
                        "id": meeting.id,
                        "title": meeting.title,
                        "start": start_datetime.isoformat(),
                        "end": end_datetime.isoformat(),
                    }
                )
            except Exception as e:
                print(f"Error processing meeting id {meeting.id}: {e}")
                continue

        context = {"event_data": json.dumps(event_data)}

        if request.user.is_superuser:
            total_investment = User.objects.aggregate(Sum("balance"))["balance__sum"] or 0
            context["total_balance"] = total_investment
        else:
            context["total_balance"] = request.user.balance

        return render(request, self.template_name, context)

