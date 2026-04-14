from django.urls import path

from . import views

app_name = "polls"

urlpatterns = [
    path("dashboard/polls/list/", views.poll_list, name="list"),
    path("dashboard/polls/create/", views.poll_create, name="create"),
    path("dashboard/polls/<int:poll_id>/edit/", views.poll_update, name="update"),
    path("dashboard/polls/<int:poll_id>/vote/", views.poll_vote, name="vote"),
    path("dashboard/polls/<int:poll_id>/results/", views.poll_results, name="results"),
    path("dashboard/polls/<int:poll_id>/copy/", views.poll_copy, name="copy"),
    path(
        "dashboard/polls/<int:pk>/delete/",
        views.PollDeleteView.as_view(),
        name="delete",
    ),
]
