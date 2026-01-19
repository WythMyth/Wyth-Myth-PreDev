from django.http import HttpResponseForbidden, JsonResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, View,CreateView,UpdateView
from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from django.db.models import Sum
from accounts.models import User
from hfallmedia.forms import ContactUsForm, HeroVideoForm
from .models import ContactUs, HeroVideo 

class AdminOrSuperuserRequiredMixin:
    """
    Mixin to ensure that only admin or superusers can access a view.
    """

    def dispatch(self, request, *args, **kwargs):
        if not (
            request.user.is_authenticated
            and (request.user.is_superuser or getattr(request.user, "admin", False))
        ):
            return HttpResponseForbidden(
                "You do not have permission to view this page."
            )
        return super().dispatch(request, *args, **kwargs)



class ContactUsView(View):

    def get(self, request):
        form = ContactUsForm()
        context = {
            "form": form,
        }
        return render(request, "contact/contact_us.html", context)
    def post(self, request):
        form = ContactUsForm(request.POST)

        if form.is_valid():
            form.save()
            return JsonResponse({"success": True})
        return JsonResponse({"success": False, "errors": form.errors}, status=400)

class VideoListView(AdminOrSuperuserRequiredMixin, ListView):
    model = HeroVideo
    template_name = "dashboard/media/video_list.html"
    context_object_name = "videos"
    paginate_by=20
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Total balance logic
        if self.request.user.is_superuser:
            total_investment = User.objects.aggregate(Sum('balance'))['balance__sum'] or 0
            context['total_balance'] = total_investment
        else:
            context['total_balance'] = self.request.user.balance
        return context

class VideoCreateView(AdminOrSuperuserRequiredMixin, CreateView):
    model = HeroVideo
    form_class = HeroVideoForm
    template_name = "dashboard/media/video_form.html"
    success_url = reverse_lazy("media:video-list")
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Total balance logic
        if self.request.user.is_superuser:
            total_investment = User.objects.aggregate(Sum('balance'))['balance__sum'] or 0
            context['total_balance'] = total_investment
        else:
            context['total_balance'] = self.request.user.balance
        return context  

class VideoUpdateView(AdminOrSuperuserRequiredMixin, UpdateView):
    model = HeroVideo
    form_class = HeroVideoForm
    template_name = "dashboard/media/video_form.html"
    success_url = reverse_lazy("media:video-list")
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Total balance logic
        if self.request.user.is_superuser:
            total_investment = User.objects.aggregate(Sum('balance'))['balance__sum'] or 0
            context['total_balance'] = total_investment
        else:
            context['total_balance'] = self.request.user.balance
        return context  


class VideoDeleteView(AdminOrSuperuserRequiredMixin, View):
    def delete(self, request, pk, *args, **kwargs):
        video = get_object_or_404(HeroVideo, pk=pk)
        video.delete()
        return JsonResponse({"success": True})

class ContactUsListView(AdminOrSuperuserRequiredMixin, ListView):
    model = ContactUs
    template_name = "dashboard/contact/contact_list.html"
    context_object_name = "contacts"
    paginate_by = 20
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Total balance logic
        if self.request.user.is_superuser:
            total_investment = User.objects.aggregate(Sum('balance'))['balance__sum'] or 0
            context['total_balance'] = total_investment
        else:
            context['total_balance'] = self.request.user.balance
        return context


class ContactUsDetailView(AdminOrSuperuserRequiredMixin, DetailView):
    model = ContactUs
    template_name = "dashboard/contact/contact_details.html"
    context_object_name = "contact"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Total balance logic
        if self.request.user.is_superuser:
            total_investment = User.objects.aggregate(Sum('balance'))['balance__sum'] or 0
            context['total_balance'] = total_investment
        else:
            context['total_balance'] = self.request.user.balance
        return context


class ContactUsDeleteView(AdminOrSuperuserRequiredMixin, View):
    def delete(self, request, pk, *args, **kwargs):
        contact = get_object_or_404(ContactUs, pk=pk)
        contact.delete()
        return JsonResponse({"success": True})
