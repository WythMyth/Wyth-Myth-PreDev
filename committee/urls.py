from django.urls import path

from committee import views

app_name = "committee"

urlpatterns = [
    # ===================committee name url ==========================
    path(
        "dashboard/committee-name/",
        views.CommitteeNameListView.as_view(),
        name="committee_name_list",
    ),
    path(
        "dashboard/committee-name/add/",
        views.CommitteeNameCreateView.as_view(),
        name="committee_name_add",
    ),
    path(
        "dashboard/committee-name/<int:pk>/edit/",
        views.CommitteeNameUpdateView.as_view(),
        name="committee_name_edit",
    ),
    path(
        "dashboard/committee-name/<int:pk>/delete/",
        views.CommitteeNameDeleteView.as_view(),
        name="committee_name_delete",
    ),
    # ===================committee year url ==========================
    path(
        "dashboard/committee-year/",
        views.CommitteeYearListView.as_view(),
        name="committee_year_list",
    ),
    path(
        "dashboard/committee-year/add/",
        views.CommitteeYearCreateView.as_view(),
        name="committee_year_add",
    ),
    path(
        "dashboard/committee-year/<int:pk>/edit/",
        views.CommitteeYearUpdateView.as_view(),
        name="committee_year_edit",
    ),
    path(
        "dashboard/committee-year/<int:pk>/delete/",
        views.CommitteeYearDeleteView.as_view(),
        name="committee_year_delete",
    ),
    # ===================committee title url ==========================
    path(
        "dashboard/committee-title/",
        views.CommitteeTitleListView.as_view(),
        name="committee_title_list",
    ),
    path(
        "dashboard/committee-title/add/",
        views.CommitteeTitleCreateView.as_view(),
        name="committee_title_add",
    ),
    path(
        "dashboard/committee-title/<int:pk>/edit/",
        views.CommitteeTitleUpdateView.as_view(),
        name="committee_title_edit",
    ),
    path(
        "dashboard/committee-title/<int:pk>/delete/",
        views.CommitteeTitleDeleteView.as_view(),
        name="committee_title_delete",
    ),
    # ===================executive committee url ==========================
    path(
        "dashboard/executive-committee/",
        views.ExecutiveCommitteeListView.as_view(),
        name="executive_committee_list",
    ),
    path(
        "dashboard/executive-committee/add/",
        views.ExecutiveCommitteeCreateView.as_view(),
        name="executive_committee_add",
    ),
    path(
        "dashboard/executive-committee/<int:pk>/edit/",
        views.ExecutiveCommitteeUpdateView.as_view(),
        name="executive_committee_edit",
    ),
    path(
        "dashboard/executive-committee/<int:pk>/delete/",
        views.ExecutiveCommitteeDeleteView.as_view(),
        name="executive_committee_delete",
    ),
]
