from django.urls import path

from schedule import views

urlpatterns = [
    path("meetings/", views.MeetingListView.as_view(), name="meeting-list"),
    path(
        "meetings/<int:pk>/", views.MeetingDetailView.as_view(), name="meeting-detail"
    ),
    path("meetings/create/", views.MeetingCreateView.as_view(), name="meeting-create"),
    path(
        "meetings/update/<int:pk>/",
        views.MeetingUpdateView.as_view(),
        name="meeting-update",
    ),
    path(
        "meetings/delete/<int:pk>/",
        views.MeetingDeleteView.as_view(),
        name="meeting-delete",
    ),
    path(
        "meeting/<int:pk>/copy/", views.MeetingCopyView.as_view(), name="meeting-copy"
    ),
    path("recordings/", views.RecordingListView.as_view(), name="recording-list"),
    path(
        "recordings/<int:pk>/",
        views.RecordingDetailView.as_view(),
        name="recording-detail",
    ),
    path(
        "recordings/create/",
        views.RecordingCreateView.as_view(),
        name="recording-create",
    ),
    path(
        "recordings/update/<int:pk>/",
        views.RecordingUpdateView.as_view(),
        name="recording-update",
    ),
    path(
        "recordings/delete/<int:pk>/",
        views.RecordingDeleteView.as_view(),
        name="recording-delete",
    ),
    path("upload/", views.meeting_upload, name="meeting_upload"),
    path(
        "download-template/",
        views.download_meeting_template,
        name="download-meeting-template",
    ),
    path("calendar/", views.CalendarView.as_view(), name="calendar"),
    #====================tags======================
    path(
        "dashboard/tag/",
        views.TagListView.as_view(),
        name="tag_list",
    ),
    path(
        "dashboard/tag/add/",
        views.TagCreateView.as_view(),
        name="tag_add",
    ),
    path(
        "dashboard/tag/<int:pk>/edit/",
        views.TagUpdateView.as_view(),
        name="tag_edit",
    ),
    path(
        "dashboard/tag/<int:pk>/delete/",
        views.TagDeleteView.as_view(),
        name="tag_delete",
    ),
]
