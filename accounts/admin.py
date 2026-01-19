from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import ExpenseBalance, ExpensePayment, Payment, PropertyContribution, User, Agreement, UserAgreement, Bank, Property, Expense, Help, OfficeCost, SharePrice
from decimal import Decimal
from django.urls import path
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import PropertyProfitDistribution, BuyerLevelHistory, Group
from django.shortcuts import redirect, get_object_or_404
from django.utils.html import format_html
from django.contrib import messages
class ShortNameDropdownFilter(admin.SimpleListFilter):
    title = 'Short Name'
    parameter_name = 'short_name'

    def lookups(self, request, model_admin):
        qs = (
            model_admin.get_queryset(request)
            .exclude(short_name__isnull=True)
            .exclude(short_name='')
            .order_by('short_name')
            .values_list('short_name', flat=True)
            .distinct()
        )
        return [(name, name) for name in qs]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(short_name=self.value())
        return queryset
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ('email', 'get_full_name', 'member_id', 'user_group', 'balance', 'investor', 'is_superuser', 'is_finnancial', 'is_expense', 'is_property', 'office_management')
    list_filter = ( 'is_active', 'investor', ShortNameDropdownFilter,)
    search_fields = ('email', 'first_name', 'last_name', 'short_name', 'member_id')
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password', 'member_id')}),
        ('Personal Info', {'fields': (
            'first_name', 'middle_name', 'last_name', 'short_name', 'phone_number', 'balance', 'total_invest_balance',
            'birth_year', 'birth_month', 'birth_date',
            'personal_image', 'photo_id',
        )}),
        ('Group & Deductions', {
            'fields': ('user_group',),
            'description': 'Select a group to apply profit deductions for this user. Users without a group have 0% deduction.'
        }),
        ('Address', {'fields': (
            'home_address_line_1', 'home_address_line_2', 'city', 'state', 'zip_code',
        )}),
        ('Additional Information', {'fields': (
            'emergency_contact', 'emergency_contact_number', 'beneficiaries', 'how_did_you_know', 'sign_by_name',
        )}),
        ('Permissions', {'fields': (
            'is_active', 'staff', 'investor', 'owner', 'semi_superuser', 'is_superuser', 'is_finnancial', 'is_expense', 'is_property', 'office_management'
        )}),
        ('Status', {'fields': (
            'is_agree', 'is_continue', 'freeze_date',
        )}),
        ('Important dates', {'fields': ('last_login', 'member_since')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2')}
        ),
        ('Personal Info', {
            'fields': ('first_name', 'middle_name', 'last_name', 'phone_number',
                      'birth_year', 'birth_month', 'birth_date')
        }),
        ('Group Assignment', {
            'fields': ('user_group',),
            'description': 'Assign user to a group for profit deductions'
        }),
        ('Address', {
            'fields': ('home_address_line_1', 'home_address_line_2', 'city', 'state', 'zip_code')
        }),
        ('Additional Information', {
            'fields': ('emergency_contact', 'emergency_contact_number', 'how_did_you_know', 'sign_by_name',
                     'personal_image', 'photo_id')
        }),
        ('Permissions', {
            'fields': ('is_active', 'staff', 'investor', 'owner', 'semi_superuser', 'is_superuser', 'office_management')
        }),
        ('Status', {
            'fields': ('is_agree', 'is_continue')
        }),
    )
    
    readonly_fields = ('member_id', 'member_since', 'freeze_date')
    
    def get_queryset(self, request):
        """Optimize queries by selecting related group"""
        qs = super().get_queryset(request)
        return qs.select_related('user_group')
@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    search_fields = ('name',)
    list_filter = ('is_active',)

# @admin.register(Payment)
# class PaymentAdmin(admin.ModelAdmin):
#     list_display = ('user', 'bank', 'amount', 'status', 'created_at', 'approved_by', 'approved_at')
#     list_filter = ('user', 'bank', 'status') 
#     search_fields = ('user__username', 'user__email', 'bank__name')
#     ordering = ('-created_at',)
from django.db.models.functions import Lower
class UserShortNameFilter(admin.SimpleListFilter):
    title = 'User'
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        qs = (
            model_admin.get_queryset(request)
            .select_related('user')
            .exclude(user__short_name__isnull=True)
            .exclude(user__short_name='')
            .annotate(sn=Lower('user__short_name'))
            .order_by('sn')
            .values_list('user__id', 'user__short_name')
            .distinct()
        )
        return [(user_id, short_name) for user_id, short_name in qs]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(user__id=self.value())
        return queryset
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'bank', 'amount', 'status',
        'created_at', 'approved_by', 'approved_at',
        'copy_button'
    )
    list_filter = (UserShortNameFilter, 'bank', 'status')
    search_fields = ('user__username', 'user__email', 'bank__name')
    ordering = ('-created_at',)

    # 🔘 Copy Button
    def copy_button(self, obj):
        return format_html(
            '<a class="button" href="{}">Copy</a>',
            f'copy/{obj.id}/'
        )

    copy_button.short_description = 'Copy'

    # 🔗 Custom admin URL
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'copy/<int:payment_id>/',
                self.admin_site.admin_view(self.copy_payment),
                name='payment-copy',
            ),
        ]
        return custom_urls + urls

    # 🧠 Copy logic
    def copy_payment(self, request, payment_id):
        payment = get_object_or_404(Payment, pk=payment_id)

        Payment.objects.create(
            user=payment.user,
            bank=payment.bank,
            amount=payment.amount,
            paid_amount=payment.paid_amount,
            receipt=payment.receipt,
            notes=payment.notes,

            # 🔴 Important rules
            status='pending',
            approved_by=None,
            approved_at=None,
            is_office_management=False,
        )

        self.message_user(
            request,
            "Payment copied successfully with status set to Pending.",
            messages.SUCCESS
        )

        return redirect(request.META.get('HTTP_REFERER'))

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'address', 'city', 'state', 'auction_price', 'selling_price', 'profit', 'status', 'is_contribution_locked', 'listed_by', 'created_at')
    list_filter = ('status', 'is_contribution_locked', 'state', 'city')
    search_fields = ('title', 'address', 'city', 'state', 'zip_code')
    readonly_fields = ('created_at', 'updated_at', 'listed_by', 'listed_date', 'profit')
    
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'status', 'is_contribution_locked')
        }),
        ('Price Info', {
            'fields': ('auction_price', 'buying_price', 'service_cost', 'acquisition_cost', 'asking_price', 'selling_price', 'profit'),
            'description': 'Profit is automatically calculated: Selling Price - Acquisition Cost'
        }),
        ('Property Info', {
            'fields': ('bedrooms', 'bathrooms', 'dining_rooms', 'square_feet')
        }),
        ('Location', {
            'fields': ('address', 'city', 'state', 'zip_code')
        }),
        ('Dates', {
            'fields': ('buying_date', 'selling_date', 'listed_date', 'created_at', 'updated_at')
        }),
        ('Listed By', {
            'fields': ('listed_by',)
        }),
    )
    
    actions = ['recalculate_profit_distribution']
    
    def recalculate_profit_distribution(self, request, queryset):
        """Admin action to recalculate profit distribution for selected properties"""
        count = 0
        for property_obj in queryset:
            if property_obj.status == 'sold' and property_obj.selling_price:
                if property_obj.distribute_sale_proceeds():
                    count += 1
        
        self.message_user(
            request,
            f'Successfully recalculated profit distribution for {count} propert{"y" if count == 1 else "ies"}.'
        )
    recalculate_profit_distribution.short_description = "Recalculate profit distribution for sold properties"

class PropertyNameFilter(admin.SimpleListFilter):
    title = 'Property'
    parameter_name = 'property'

    def lookups(self, request, model_admin):
        properties = Property.objects.all().order_by('title')
        return [(p.id, p.title) for p in properties]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(property_id=self.value())
        return queryset


@admin.register(PropertyContribution)
class PropertyContributionAdmin(admin.ModelAdmin):
    list_display = [
        'user_display',
        'user_group_display',
        'property', 
        'investment_sequence',
        'contribution', 
        'invest_amount',
        'remaining',
        'investment_date',
        'total_days',
        'days_proportion',
        'shares',
        'profit_weight',
        'profit_display',
        'deduction_display',
        'final_profit_display',
        'ratio',

        'is_fixed_amount'
    ]
    
    list_filter = [
        PropertyNameFilter,
        'is_fixed_amount',
        'investment_date',
        'created_at',
        'user__user_group'
    ]
    
    search_fields = [
        'user__first_name',
        'user__last_name',
        'user__email',
        'property__title'
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'shares'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'user',
                'property',
                'investment_sequence',
                'is_fixed_amount'
            )
        }),
        ('Investment Details', {
            'fields': (
                'invest_amount',
                'contribution',
                'remaining',
                'ratio'
            )
        }),
        ('Profit Breakdown', {
            'fields': (
                'profit',
                'deduction',
                'final_profit'
            ),
            'description': 'Profit breakdown for this contribution based on user group deduction percentage'
        }),
        ('Date & Time Tracking', {
            'fields': (
                'investment_date',
                'total_days',
            )
        }),
        ('Shares & Weight Calculation', {
            'fields': (
                'shares',
                'days_proportion',
                'investment_ratio',
                'profit_weight'
            ),
            'description': 'Share-based profit calculation: Profit Weight = Days Proportion × Shares'
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    def user_display(self, obj):
        """Display user full name"""
        return obj.user.get_full_name()
    user_display.short_description = 'User'
    user_display.admin_order_field = 'user__first_name'
    
    def user_group_display(self, obj):
        """Display user's group"""
        if obj.user.user_group:
            return f"{obj.user.user_group.name} ({obj.user.user_group.percentage}%)"
        return "No Group (0%)"
    user_group_display.short_description = 'User Group'
    
    def profit_display(self, obj):
        """Display profit with color coding"""
        if obj.profit > 0:
            return f"${obj.profit:,.2f}"
        return f"${obj.profit:,.2f}"
    profit_display.short_description = 'Profit'
    profit_display.admin_order_field = 'profit'
    
    def deduction_display(self, obj):
        """Display deduction with percentage"""
        if obj.deduction > 0 and obj.user.user_group:
            return f"${obj.deduction:,.2f} ({obj.user.user_group.percentage}%)"
        return f"${obj.deduction:,.2f}"
    deduction_display.short_description = 'Deduction'
    deduction_display.admin_order_field = 'deduction'
    
    def final_profit_display(self, obj):
        """Display final profit"""
        return f"${obj.final_profit:,.2f}"
    final_profit_display.short_description = 'Final Profit'
    final_profit_display.admin_order_field = 'final_profit'
    
    def save_model(self, request, obj, form, change):
        """
        Admin থেকে save করার সময় automatic calculations করে
        """
        super().save_model(request, obj, form, change)
        
        
        if obj.property.selling_date and obj.investment_date:
            
            delta = obj.property.selling_date - obj.investment_date
            obj.total_days = max(1, delta.days)
            
            
            contributions = PropertyContribution.objects.filter(property=obj.property)
            
            
            max_days = max([c.total_days for c in contributions if c.total_days > 0], default=1)
            
            
            if max_days > 0 and obj.total_days > 0:
                obj.days_proportion = Decimal(str(obj.total_days)) / Decimal(str(max_days))
            else:
                obj.days_proportion = Decimal('0')
            
            
            total_contribution = sum([c.contribution for c in contributions]) or Decimal('1')
            
            
            obj.investment_ratio = obj.contribution / total_contribution
            
            
            obj.profit_weight = obj.investment_ratio * obj.days_proportion
            
            obj.save()
    
    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'user__user_group', 'property')
    
    list_per_page = 50
    ordering = ['-created_at']




@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'percentage', 'user_count', 'created_at')
    search_fields = ('name',)
    list_filter = ('created_at',)
    ordering = ('name',)
    
    fieldsets = (
        ('Group Information', {
            'fields': ('name', 'percentage')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def user_count(self, obj):
        return obj.users.count()
    user_count.short_description = 'Number of Users'

class BuyerLevelHistoryInline(admin.TabularInline):
    """Inline display for Buyer Level History under PropertyProfitDistribution"""
    model = BuyerLevelHistory
    extra = 0
    readonly_fields = [
        'user', 'previous_level', 'current_level',
        'changed_at', 'changed_by'
    ]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PropertyProfitDistribution)
class PropertyProfitDistributionAdmin(admin.ModelAdmin):
    """
    Admin interface for Property Profit Distribution

    Features:
    - Show property name with clickable link
    - Display all first & second level buyers
    - Editable share values
    - Buyer level history inline
    """

    list_display = [
        'property_name_with_icon',
        'first_level_count_display',
        'first_level_share_display',
        'second_level_count_display',
        'second_level_share_display',
        'total_buyers_display',
        'created_date',
        'actions_display',
    ]

    list_filter = ['created_at', 'updated_at']

    search_fields = [
        'property__title',
        'property__address',
        'first_level_buyers__email',
        'second_level_buyers__email',
    ]

    fieldsets = (
        ('Property Information', {
            'fields': ('property', 'property_details_display'),
        }),

        ('First Level Buyers', {
            'fields': (
                'first_level_buyers',
                'first_level_buyer_count',
                'first_level_share',
                'first_level_buyers_display',
            ),
            'classes': ('wide',),
        }),

        ('Second Level Buyers', {
            'fields': (
                'second_level_buyers',
                'second_level_buyer_count',
                'second_level_share',
                'second_level_buyers_display',
            ),
            'classes': ('wide',),
        }),

        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = [
        'property_details_display',
        'first_level_buyer_count',
        'second_level_buyer_count',
        'first_level_buyers_display',
        'second_level_buyers_display',
        'created_at',
        'updated_at',
    ]

    filter_horizontal = ['first_level_buyers', 'second_level_buyers']

    inlines = [BuyerLevelHistoryInline]
    ordering = ['-created_at']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.update_buyer_counts()

 

    def property_name_with_icon(self, obj):
        """
        Property name with icon and clickable link
        Clicking opens the PropertyProfitDistribution detail page
        """
        try:
            
            url = reverse('admin:accounts_propertyprofitdistribution_change', args=[obj.id])
            return format_html(
                '''
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 20px;">🏠</span>
                    <a href="{}" style="font-weight: bold; color: #0066cc; font-size: 15px; text-decoration: none;">
                        {}
                    </a>
                </div>
                ''',
                url,
                obj.property.title
            )
        except Exception as e:
            return format_html(
                '<div style="display: flex; align-items: center; gap: 8px;"><span style="font-size: 20px;">🏠</span><span>{}</span></div>',
                obj.property.title
            )
    property_name_with_icon.short_description = 'Property Name'

    def property_details_display(self, obj):
        """Display property details with link to Property admin page"""
        if not obj.property:
            return "—"

        p = obj.property
        
        
        try:
            property_url = reverse('admin:accounts_property_change', args=[p.id])
            property_link = f'<a href="{property_url}" style="color: #0066cc; font-weight: bold;">{p.title}</a>'
        except:
            property_link = p.title

        html = f"""
        <div style="background:#f5f5f5;padding:15px;border-radius:5px;border-left:4px solid #0066cc;">
            <h3 style="margin-top:0;color:#0066cc;">📋 Property Details</h3>
            <table style="width:100%;border-collapse:collapse;">
                <tr><td style="padding:5px;"><b>Title:</b></td><td style="padding:5px;">{property_link}</td></tr>
                <tr><td style="padding:5px;"><b>Address:</b></td><td style="padding:5px;">{p.address}, {p.city}</td></tr>
                <tr><td style="padding:5px;"><b>Status:</b></td>
                    <td style="padding:5px;"><span style="background:#4CAF50;color:#fff;padding:3px 8px;border-radius:3px;">{p.get_status_display()}</span></td>
                </tr>
                <tr><td style="padding:5px;"><b>Buying Price:</b></td><td style="padding:5px;">${p.buying_price or 0:,.2f}</td></tr>
                <tr><td style="padding:5px;"><b>Selling Price:</b></td><td style="padding:5px;">${p.selling_price or 0:,.2f}</td></tr>
            </table>
        </div>
        """
        return mark_safe(html)
    property_details_display.short_description = 'Property Details'

    def first_level_count_display(self, obj):
        color = '#4CAF50' if obj.first_level_buyer_count > 0 else '#999'
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;border-radius:12px;font-weight:bold;">👤 {}</span>',
            color, obj.first_level_buyer_count
        )
    first_level_count_display.short_description = '1st Level Buyers'

    def first_level_share_display(self, obj):
        return format_html(
            '<span style="background:#2196F3;color:white;padding:3px 10px;border-radius:5px;font-weight:bold;">× {}</span>',
            obj.first_level_share
        )
    first_level_share_display.short_description = '1st Level Share'

    def second_level_count_display(self, obj):
        color = '#FF9800' if obj.second_level_buyer_count > 0 else '#999'
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;border-radius:12px;font-weight:bold;">👥 {}</span>',
            color, obj.second_level_buyer_count
        )
    second_level_count_display.short_description = '2nd Level Buyers'

    def second_level_share_display(self, obj):
        return format_html(
            '<span style="background:#9C27B0;color:white;padding:3px 10px;border-radius:5px;font-weight:bold;">× {}</span>',
            obj.second_level_share
        )
    second_level_share_display.short_description = '2nd Level Share'

    def total_buyers_display(self, obj):
        total = obj.first_level_buyer_count + obj.second_level_buyer_count
        return format_html(
            '<span style="background:#607D8B;color:white;padding:3px 10px;border-radius:5px;font-weight:bold;">Σ {}</span>',
            total
        )
    total_buyers_display.short_description = 'Total Buyers'

    def created_date(self, obj):
        return obj.created_at.strftime('%d %b %Y, %I:%M %p')
    created_date.short_description = 'Created'

    def first_level_buyers_display(self, obj):
        buyers = obj.first_level_buyers.all()
        if not buyers:
            return mark_safe('<p style="color:#999;">No first-level buyers available.</p>')

        html = """
        <div style="background:#e8f5e9;padding:10px;border-radius:5px;border-left:4px solid #4CAF50;">
        <h4 style="margin-top:0;color:#4CAF50;">👥 First Level Buyer List</h4>
        <table style="width:100%;border-collapse:collapse;">
        <tr style="background:#c8e6c9;">
            <th style="padding:8px;text-align:left;">Name</th>
            <th style="padding:8px;text-align:left;">Email</th>
            <th style="padding:8px;text-align:left;">Share</th>
        </tr>
        """
        for b in buyers:
            html += f"""
                <tr style="border-bottom:1px solid #ddd;">
                    <td style="padding:8px;">{b.get_full_name()}</td>
                    <td style="padding:8px;">{b.email}</td>
                    <td style="padding:8px;"><b>× {obj.first_level_share}</b></td>
                </tr>
            """

        html += "</table></div>"
        return mark_safe(html)
    first_level_buyers_display.short_description = '👥 First Level Buyers'

    def second_level_buyers_display(self, obj):
        buyers = obj.second_level_buyers.all()
        if not buyers:
            return mark_safe('<p style="color:#999;">No second-level buyers available.</p>')

        html = """
        <div style="background:#fff3e0;padding:10px;border-radius:5px;border-left:4px solid #FF9800;">
        <h4 style="margin-top:0;color:#FF9800;">👥 Second Level Buyer List</h4>
        <table style="width:100%;border-collapse:collapse;">
        <tr style="background:#ffe0b2;">
            <th style="padding:8px;text-align:left;">Name</th>
            <th style="padding:8px;text-align:left;">Email</th>
            <th style="padding:8px;text-align:left;">Share</th>
        </tr>
        """

        for b in buyers:
            html += f"""
                <tr style="border-bottom:1px solid #ddd;">
                    <td style="padding:8px;">{b.get_full_name()}</td>
                    <td style="padding:8px;">{b.email}</td>
                    <td style="padding:8px;"><b>× {obj.second_level_share}</b></td>
                </tr>
            """

        html += "</table></div>"
        return mark_safe(html)
    second_level_buyers_display.short_description = '👥 Second Level Buyers'

    def actions_display(self, obj):
        """Quick action buttons"""
        try:
            contributions_url = reverse('admin:accounts_propertycontribution_changelist') + f'?property__id__exact={obj.property.id}'
            property_url = reverse('admin:accounts_property_change', args=[obj.property.id])
            
            html = f'''
            <div style="white-space:nowrap;">
                <a href="{contributions_url}"
                   style="background:#2196F3;color:white;padding:5px 10px;border-radius:3px;text-decoration:none;display:inline-block;margin:2px;">
                    📊 Contributions
                </a>
                <a href="{property_url}"
                   style="background:#4CAF50;color:white;padding:5px 10px;border-radius:3px;text-decoration:none;display:inline-block;margin:2px;">
                    🏠 Property
                </a>
            </div>
            '''
        except:
            html = '<span style="color:#999;">—</span>'
        
        return mark_safe(html)
    actions_display.short_description = 'Quick Actions'


    actions = ['update_profit_weights_action', 'reset_shares_action']

    def update_profit_weights_action(self, request, queryset):
        """Bulk update profit weights for selected properties"""
        updated_count = 0
        for dist in queryset:
            result = dist.update_all_profit_weights()
            if result['success']:
                updated_count += result['updated_count']

        self.message_user(
            request,
            f"✅ Successfully updated profit weights for {updated_count} contributions!"
        )
    update_profit_weights_action.short_description = "🔄 Update Profit Weights"

    def reset_shares_action(self, request, queryset):
        """Reset all shares to default (1.0)"""
        queryset.update(first_level_share=1.0, second_level_share=1.0)
        self.message_user(
            request,
            f"✅ Reset share values to 1.0 for {queryset.count()} properties."
        )
    reset_shares_action.short_description = "↺ Reset Share Values (1.0)"



@admin.register(BuyerLevelHistory)
class BuyerLevelHistoryAdmin(admin.ModelAdmin):
    """Admin interface for Buyer Level History"""

    list_display = [
        'user_name',
        'property_name',
        'level_change_display',
        'changed_date',
        'changed_by_name',
    ]

    list_filter = ['current_level', 'previous_level', 'changed_at']
    search_fields = [
        'user__email',
        'user__first_name',
        'user__last_name',
        'profit_distribution__property__title',
    ]

    readonly_fields = [
        'profit_distribution',
        'user',
        'previous_level',
        'current_level',
        'changed_at',
        'changed_by',
    ]

    ordering = ['-changed_at']

    def user_name(self, obj):
        return obj.user.get_full_name()
    user_name.short_description = 'User'

    def property_name(self, obj):
        return obj.profit_distribution.property.title
    property_name.short_description = 'Property'

    def level_change_display(self, obj):
        prev = obj.previous_level or 'New'
        curr = obj.current_level

        color_map = {
            'first': '#4CAF50',
            'second': '#FF9800',
            'New': '#2196F3',
        }

        return format_html(
            '<span style="background:{};color:white;padding:3px 8px;border-radius:3px;">{}</span>'
            ' → '
            '<span style="background:{};color:white;padding:3px 8px;border-radius:3px;">{}</span>',
            color_map.get(prev, '#999'),
            prev,
            color_map.get(curr, '#999'),
            curr,
        )
    level_change_display.short_description = 'Level Change'

    def changed_date(self, obj):
        return obj.changed_at.strftime('%d %b %Y, %I:%M %p')
    changed_date.short_description = 'Changed At'

    def changed_by_name(self, obj):
        return obj.changed_by.get_full_name() if obj.changed_by else '—'
    changed_by_name.short_description = 'Changed By'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
   
admin.site.register(OfficeCost)
admin.site.register(SharePrice)
admin.site.register(User, UserAdmin)
admin.site.register(Agreement)
admin.site.register(Expense)
admin.site.register(UserAgreement)

admin.site.register(Help)
admin.site.register(ExpenseBalance)
admin.site.register(ExpensePayment)