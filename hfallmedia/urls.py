from django.urls import path

from hfallmedia.views import *

app_name = "media"

urlpatterns = [
    path('contact-us/', ContactUsView.as_view(), name='contact_us'),

    #  dashboard/ContactUs
    path("dashboard/contact/", ContactUsListView.as_view(), name="contact-list"),
    path("dashboard/contact/<int:pk>/details/", ContactUsDetailView.as_view(), name="detail-contact"),
    path("dashboard/contact/<int:pk>/delete/", ContactUsDeleteView.as_view(), name="delete-contact"),


    # dashboard / vidoes
    path("dashboard/video/", VideoListView.as_view(), name="video-list"),
    path("dashboard/video/create/", VideoCreateView.as_view(), name="video-create"),
    path("dashboard/video/<int:pk>/update/", VideoUpdateView.as_view(), name="video-update"),
    path("dashboard/video/<int:pk>/delete/", VideoDeleteView.as_view(), name="video-delete"),
]


