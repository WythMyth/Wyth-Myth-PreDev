from django.urls import path
from django.contrib.auth import views as auth_views
from .views import *  
from .forms import CustomPasswordResetForm, CustomSetPasswordForm
app_name = 'accounts'

urlpatterns = [
    path('register/', register, name='register'),
    path('success/', success_message, name='success-message'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', user_logout, name='logout'),
    path('password-reset/', 
        auth_views.PasswordResetView.as_view(
            template_name='password_reset.html',
            email_template_name='password_reset_email.html',
            html_email_template_name='password_reset_email.html',
            subject_template_name='password_reset_subject.txt',
            form_class=CustomPasswordResetForm,
            success_url=reverse_lazy('accounts:password_reset_done')  
        ), 
        name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='password_reset_done.html'
         ), 
         name='password_reset_done'),

    path('reset/<uidb64>/<token>/', 
        auth_views.PasswordResetConfirmView.as_view(
            template_name='password_reset_confirm.html',
            form_class=CustomSetPasswordForm,
            success_url=reverse_lazy('accounts:password_reset_complete')  # 🔧 add this
        ), 
        name='password_reset_confirm'),

    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='password_reset_complete.html'
         ), 
         name='password_reset_complete'),
    path('download-stock-certificate/', download_stock_certificate, name='download_stock_certificate'),
    path('dashboard/', dashboard, name='dashboard'),
    path('expenses/', expense_list.as_view(), name='expense_list'),
    path("expenses/update-status/", update_expense_status, name="update-expense-status"),
    path("expenses/<int:pk>/delete/", expense_delete, name="expense-delete"),
    path('expenses/<int:pk>/copy/', ExpensesCopyView.as_view(), name='expenses-copy'),
    path('expenses/download/', expense_download, name='expense_download'),
    path('expenses/create/', expense_create, name='expense_create'),
    path('expenses/<int:expense_id>/edit/', expense_update, name='expense_update'),  
    path('expenses/<int:expense_id>/', expense_detail, name='expense_details'),
    path("expense/<int:expense_id>/pay/", expense_payment_create, name="expense_payment_create"),
    path("expense-payment/", expense_payment_list.as_view(), name="expense_payment_list"),
    path(
        "expense/<int:pk>/details/",
        ExpenseDetailView.as_view(),
        name="expense_detail"
    ),
    path('expenses/<int:expense_id>/approve/', expense_approve, name='expense_approve'),
    path('expenses/<int:expense_id>/reject/', expense_reject, name='expense_reject'),
    path('expenses/<int:expense_id>/clarify/', expense_clarification, name='expense_clarification'),
    path('profile/', profile_view, name='profile'),
    path('add-beneficiary/', add_beneficiary, name='add_beneficiary'),
    path('edit-profile/', UserProfileUpdateView.as_view(), name='profile-update'),
    path('members/', member_list.as_view(), name='member_list'),
    path('members-card/', member_list_card, name='member_list_card'),
    path('members/<int:pk>/', member_detail, name='member_detail'),
    path('', home, name='home'), 
    path('list/', PropertyListView.as_view(), name='property_list'),
    path('create/', PropertyCreateView.as_view(), name='property_create'),
    path('<int:pk>/', PropertyDetailView.as_view(), name='property_detail'),
    path('<int:pk>/gallery/', PropertyGalleryView.as_view(), name='property_gallery'),
    path('api/properties/<int:pk>/', property_api_detail, name='property_api_detail'),
    path("api/stories/<int:property_id>/",get_property_stories, name="get_property_stories"),
    path('api/property/<int:property_id>/images/', property_images, name='property_images'),
    path('<int:pk>/update/', PropertyUpdateView.as_view(), name='property_update'),
    path('<int:pk>/delete/', PropertyDeleteView.as_view(), name='property_delete'),
    path('payments/banks/', payment_banks, name='payment_banks'),
    path('payments/make/<int:bank_id>/', make_payment, name='make_payment'),
    path('payments/my/', my_payments.as_view(), name='my_payments'),
    path('payments/pending/', pending_payments.as_view(), name='pending_payments'),
    path('payments/detail/<int:payment_id>/', payment_detail, name='payment_detail'),
    path('payments/stripe/', stripe_payment, name='stripe_payment'),
    path('payments/success/', payment_success, name='payment_success'),
    path('payments/webhook/', stripe_webhook, name='stripe_webhook'),
    path('square-create-payment/', square_create_payment, name='square_create_payment'),
    path('square-payment-success/', square_payment_success, name='square_payment_success'),
    path("paypal/create/", paypal_create_payment, name="paypal_create_payment"),
    path("paypal/success/", paypal_success, name="paypal_success"),
    path('upload-agreement/', upload_new_agreement, name='upload_agreement'),
    path('user-agreement/list/', UploadedAgreementsView.as_view(), name='user_agreement_list'),
    path("dashboard/user-agreement/<int:pk>/delete/", UploadedAgreementsDeleteView.as_view(), name="delete-user-agreement"),
    path('announce/', create_announcement, name='create_announcement'),
    path('help/create/', help_create_view, name='help_create'),
    path('help/success/', help_success_view, name='help_success'),
    path('payments/', PaymentListView.as_view(), name='payment-list'),
    path('payments/update-status/', update_payment_status, name='update-payment-status'),
    path('payments/export/', PaymentExportExcelView.as_view(), name='payment-export'),
    path('office-management/payments/', office_management_dashboard, name='office_management_payments'),
    path('office-expenses/', 
         OfficeExpenseListView.as_view(), 
         name='office_expense_list'),
    
    path('office-expenses/<int:expense_id>/pay/', 
         office_expense_payment, 
         name='office_expense_payment'),
    
    path('office-expenses/<int:expense_id>/detail/', 
         office_expense_detail, 
         name='office_expense_detail'),
    path('expense/', expenselist.as_view(), name='expenselist'),
    path('managementexpense/', managementexpenselist.as_view(), name='management_expense_list'),
    
]