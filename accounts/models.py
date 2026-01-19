import datetime
import uuid
from decimal import Decimal,getcontext,ROUND_HALF_UP
from datetime import date, datetime
from django.contrib.auth.models import (AbstractBaseUser, BaseUserManager,
                                        PermissionsMixin)
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.db.models import Sum,F
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

getcontext().prec = 28

# User Manager Class
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(
            email=self.normalize_email(email),
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_staffuser(self, email, password):
        """
        Creates and saves a staff user with the given email and password.
        """
        user = self.create_user(
            email,
            password=password,
        )
        user.staff = True
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        """
        Creates and saves a superuser with the given email and password.
        """
        user = self.create_user(
            email,
            password=password,
        )
        user.staff = True
        user.admin = True
        user.is_active = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


def generate_member_id():
    last_user = User.objects.filter(
        member_id__startswith='MEM'
    ).exclude(
        member_id__isnull=True
    ).exclude(
        member_id__exact=''
    ).order_by('member_id').last()
    
    if last_user and last_user.member_id:
        try:
            last_number = int(last_user.member_id[3:])  
            new_number = last_number + 1
        except (ValueError, IndexError):
            new_number = 1
    else:
        new_number = 1
    
    return f"MEM{new_number:04d}"

# User Model
class User(AbstractBaseUser, PermissionsMixin):
    STATE_CHOICES = (
        ('AL', 'Alabama'), ('AK', 'Alaska'), ('AS', 'American Samoa'), 
        ('AZ', 'Arizona'), ('AR', 'Arkansas'), ('AA', 'Armed Forces Americas'), 
        ('AE', 'Armed Forces Europe'), ('AP', 'Armed Forces Pacific'), 
        ('CA', 'California'), ('CO', 'Colorado'), ('CT', 'Connecticut'), 
        ('DE', 'Delaware'), ('DC', 'District of Columbia'), 
        ('FM', 'Federated States of Micronesia'), ('FL', 'Florida'), 
        ('GA', 'Georgia'), ('GU', 'Guam'), ('HI', 'Hawaii'), ('ID', 'Idaho'), 
        ('IL', 'Illinois'), ('IN', 'Indiana'), ('IA', 'Iowa'), ('KS', 'Kansas'), 
        ('KY', 'Kentucky'), ('LA', 'Louisiana'), ('ME', 'Maine'), 
        ('MH', 'Marshall Islands'), ('MD', 'Maryland'), ('MA', 'Massachusetts'), 
        ('MI', 'Michigan'), ('MN', 'Minnesota'), ('MS', 'Mississippi'), 
        ('MO', 'Missouri'), ('MT', 'Montana'), ('NE', 'Nebraska'), ('NV', 'Nevada'), 
        ('NH', 'New Hampshire'), ('NJ', 'New Jersey'), ('NM', 'New Mexico'), 
        ('NY', 'New York'), ('NC', 'North Carolina'), ('ND', 'North Dakota'), 
        ('MP', 'Northern Mariana Islands'), ('OH', 'Ohio'), ('OK', 'Oklahoma'), 
        ('OR', 'Oregon'), ('PW', 'Palau'), ('PA', 'Pennsylvania'), 
        ('PR', 'Puerto Rico'), ('RI', 'Rhode Island'), ('SC', 'South Carolina'), 
        ('SD', 'South Dakota'), ('TN', 'Tennessee'), ('TX', 'Texas'), 
        ('UT', 'Utah'), ('VT', 'Vermont'), ('VI', 'Virgin Islands'), 
        ('VA', 'Virginia'), ('WA', 'Washington'), ('WV', 'West Virginia'), 
        ('WI', 'Wisconsin'), ('WY', 'Wyoming')
    )
    BIRTH_YEAR_CHOICES = [(r, r) for r in range(1959, 2026)]
    BIRTH_MONTH_CHOICES = [
        (1, "January"), (2, "February"), (3, "March"), (4, "April"), 
        (5, "May"), (6, "June"), (7, "July"), (8, "August"), 
        (9, "September"), (10, "October"), (11, "November"), (12, "December")
    ]
    BIRTH_DATE_CHOICES = [(d, d) for d in range(1, 32)]
    # Personal information
    first_name = models.CharField(max_length=150, verbose_name='First Name')
    middle_name = models.CharField(max_length=150, verbose_name='Middle Name', blank=True, null=True)
    last_name = models.CharField(max_length=150, verbose_name='Last Name')
    short_name = models.CharField(max_length=255, verbose_name='Short Name', blank=True, null=True)

    # Contact information
    phone_number = models.CharField(max_length=20, verbose_name='Phone Number')
    email = models.EmailField(verbose_name='Email Address', max_length=255, unique=True)
    # Birth date information
    birth_year = models.IntegerField(choices=BIRTH_YEAR_CHOICES, verbose_name='Birth Year', blank=False, null=True)
    birth_month = models.IntegerField(choices=BIRTH_MONTH_CHOICES, verbose_name='Birth Month', blank=False, null=True)
    birth_date = models.IntegerField(choices=BIRTH_DATE_CHOICES, verbose_name='Birth Date', blank=False, null=True)
    
    # Address information
    home_address_line_1 = models.CharField(max_length=255, verbose_name='Home Address Line 1')
    home_address_line_2 = models.CharField(max_length=255, verbose_name='Home Address Line 2', blank=True, null=True)
    city = models.CharField(max_length=100, verbose_name='City')
    state = models.CharField(max_length=100, verbose_name='State', choices=STATE_CHOICES, blank=False, null=True)
    zip_code = models.CharField(max_length=10, verbose_name='ZIP Code')
    
    # Profile images and ID
    personal_image = models.ImageField(upload_to='users/profile/', verbose_name='Personal Image', null=True, blank=True)
    photo_id = models.ImageField(upload_to='users/id/', verbose_name='Photo ID', null=True, blank=True)
    
    # Other information
    emergency_contact = models.CharField(max_length=150, verbose_name='Emergency Contact', blank=True, null=True)
    emergency_contact_number = models.CharField(max_length=150, verbose_name='Emergency Contact Name', blank=True, null=True)
    how_did_you_know = models.CharField(max_length=500, verbose_name='How Did You Know About Us', blank=True, null=True)
    sign_by_name = models.CharField(max_length=150, verbose_name='Sign By Name', blank=True, null=True)
    beneficiaries = models.JSONField(default=list,null=True, blank=True, verbose_name='Beneficiaries')
    # User roles
    investor = models.BooleanField(default=True, verbose_name='Investor')
    owner = models.BooleanField(default=False, verbose_name='Owner')
    staff = models.BooleanField(default=False, verbose_name='Staff')
    semi_superuser = models.BooleanField(default=False, verbose_name='Semi-Superuser')
    
    # Automatic information
    member_id = models.CharField(max_length=20, verbose_name='Member ID', unique=True, blank=True, null=True)
    member_since = models.DateTimeField(verbose_name='Member Since', auto_now_add=True)
    balance = models.DecimalField(max_digits=100, decimal_places=6, default=0.00, verbose_name='Balance')
    total_invest_balance = models.DecimalField(max_digits=100, decimal_places=6, default=0.00, verbose_name='Invest Balance')
    
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    is_agree = models.BooleanField(default=False, verbose_name='Is Agree')
    is_expense = models.BooleanField(default=False, verbose_name='Is Expense')
    is_finnancial = models.BooleanField(default=False, verbose_name='Is Finnancial')
    is_property = models.BooleanField(default=False, verbose_name='Is Property')
    is_continue = models.BooleanField(default=True, verbose_name='Is Continue')
    office_management = models.BooleanField(
        default=False, 
        verbose_name='Office Management',
        help_text='Only one user can be office manager. Office costs will be added to this user\'s balance.'
    )
    user_group = models.ForeignKey(
        'Group',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='User Group',
        help_text='Select a group for this user to apply profit deductions'
    )
    freeze_date = models.DateTimeField(null=True, blank=True, verbose_name='Freeze Date')
    
    # Set the User Manager
    objects = UserManager()
    
    # Field to use for login
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    @property
    def is_staff(self):
        return self.staff
    def get_full_name(self):
        
        name_parts = []
        
        if self.first_name and self.first_name.strip():
            name_parts.append(self.first_name.strip())
            
        if self.middle_name and self.middle_name.strip():
            name_parts.append(self.middle_name.strip())
            
        if self.last_name and self.last_name.strip():
            name_parts.append(self.last_name.strip())
        
        return " ".join(name_parts)

    def __str__(self):
       
        if self.short_name:
            return self.short_name
        full_name = self.get_full_name()
        return full_name if full_name else self.email or str(self.pk)
    
    def clean(self):
        """
        Validation to ensure only one user has office_management=True
        """
        super().clean()
        
        if self.office_management:
           
            existing_manager = User.objects.filter(
                office_management=True
            ).exclude(pk=self.pk).first()
            
            if existing_manager:
                raise ValidationError(
                    f'Only one user can be the office manager. '
                    f'{existing_manager.get_full_name()} is currently the office manager.'
                )
    def save(self, *args, **kwargs):
        # Generate member ID for new users
        if not self.member_id:
            self.member_id = generate_member_id()
            
        # Set investor as default during registration
        if not self.pk:  # If this is a new user
            self.investor = True
        if not self.short_name or self.short_name.strip() == "":
            full_name = self.get_full_name()
            if full_name:
                self.short_name = full_name
            
        # Handle freeze date tracking
        if not self.is_continue and self.freeze_date is None:
            self.freeze_date = timezone.now()
        elif self.is_continue:
            self.freeze_date = None
            
        super().save(*args, **kwargs)

    def _transfer_office_cost_to_user(self):
        """
        Transfer office cost balance to user's balance when office_management is enabled
        """
        with transaction.atomic():
            office_cost, created = OfficeCost.objects.get_or_create(id=1)
            
            if office_cost.balance > 0:
                print(f"\n{'='*60}")
                print(f"💼 TRANSFERRING OFFICE COST TO USER")
                print(f"{'='*60}")
                print(f"User: {self.get_full_name()}")
                print(f"User Balance Before: ${float(self.balance):,.2f}")
                print(f"Office Cost Balance: ${float(office_cost.balance):,.2f}")
                
                
                self.balance += office_cost.balance
                
                
                office_cost.balance = Decimal('0.00')
                office_cost.save(update_fields=['balance'])
                
                print(f"User Balance After: ${float(self.balance):,.2f}")
                print(f"Office Cost Balance After: ${float(office_cost.balance):,.2f}")
                print(f"{'='*60}\n")
    
    def _transfer_user_balance_to_office(self):
        """
        Optional: Transfer balance back to office cost when office_management is disabled
        This is optional - you can remove this if you want the user to keep the balance
        """
        with transaction.atomic():
            office_cost, created = OfficeCost.objects.get_or_create(id=1)
            
            if self.balance > 0:
                print(f"\n{'='*60}")
                print(f"💼 TRANSFERRING USER BALANCE BACK TO OFFICE COST")
                print(f"{'='*60}")
                print(f"User: {self.get_full_name()}")
                print(f"User Balance Before: ${float(self.balance):,.2f}")
                print(f"Office Cost Balance Before: ${float(office_cost.balance):,.2f}")
                
                
                office_cost.balance += self.balance
                
                
                self.balance = Decimal('0.00')
                
                office_cost.save(update_fields=['balance'])
                
                print(f"User Balance After: ${float(self.balance):,.2f}")
                print(f"Office Cost Balance After: ${float(office_cost.balance):,.2f}")
                print(f"{'='*60}\n")
    
    @classmethod
    def get_office_manager(cls):
        """
        Get the current office manager user
        """
        return cls.objects.filter(office_management=True).first()
    
    @classmethod
    def set_office_manager(cls, user_id):
        """
        Set a specific user as office manager (removes from previous manager)
        """
        with transaction.atomic():
            # Remove office_management from all users
            cls.objects.filter(office_management=True).update(office_management=False)
            
            # Set for specific user
            user = cls.objects.get(id=user_id)
            user.office_management = True
            user.save()
            
            return user


class Agreement(models.Model):
    title = models.CharField(max_length=200, verbose_name='Title')
    content = models.TextField(verbose_name='Agreement Content')
    version = models.CharField(max_length=10, verbose_name='Version')
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    def __str__(self):
        return f"{self.title} (v{self.version})"
    
    class Meta:
        verbose_name = 'Agreement'
        verbose_name_plural = 'Agreements'


class UserAgreement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='User')
    agreement = models.ForeignKey(Agreement,null=True, blank=True, on_delete=models.CASCADE, verbose_name='Agreement')
    agreed_at = models.DateTimeField(auto_now_add=True, verbose_name='Agreed At')
    uploaded_file = models.FileField(upload_to='user_agreements/', null=True, blank=True, verbose_name='Uploaded File')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    def __str__(self):
        return f"{self.user} - {self.agreement or 'Uploaded File'}"

    class Meta:
        unique_together = ('user', 'agreement')  # optional
    
    class Meta:
        verbose_name = 'User Agreement'
        verbose_name_plural = 'User Agreements'
        unique_together = ('user', 'agreement')


class SharePrice(models.Model):
    """
    Singleton model to store per-share price
    One share = fixed amount (e.g., 5000 Tk)
    """
    price_per_share = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=Decimal('5000.00'),
        verbose_name='Price Per Share'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Share Price"
        verbose_name_plural = "Share Price"

    def __str__(self):
        return f"Per Share Price: {self.price_per_share} Tk"

    @classmethod
    def get_current_price(cls):
        """Get current share price, create if doesn't exist"""
        obj, created = cls.objects.get_or_create(id=1)
        return obj.price_per_share

class PropertyContribution(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='property_contributions')
    property = models.ForeignKey('Property', on_delete=models.CASCADE, related_name='property_contributions')
    contribution = models.DecimalField(max_digits=50, decimal_places=6, validators=[MinValueValidator(Decimal('0.00'))], verbose_name='Contribution Amount')
    is_fixed_amount = models.BooleanField(default=False, verbose_name='Fixed Investment Amount')
    ratio = models.DecimalField(max_digits=20, decimal_places=6, validators=[MinValueValidator(Decimal('0.00'))], verbose_name='Contribution Ratio')
    investment_date = models.DateField(null=True, blank=True, verbose_name='Date of Investment')
    total_days = models.PositiveIntegerField(default=0, verbose_name='Total Days Invested')
    days_proportion = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal('0.00'), verbose_name='Days Proportion')
    shares = models.DecimalField(
        max_digits=20, 
        decimal_places=6, null=True, blank=True,
        default=Decimal('0.00'), 
        verbose_name='Number of Shares'
    )
    investment_ratio = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal('0.00'), verbose_name='Investment Ratio')
    profit_weight = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal('0.00'), verbose_name='Profit Weight')
    invest_amount = models.DecimalField(max_digits=50, null=True, blank=True, decimal_places=2, default=0)
    remaining = models.DecimalField(max_digits=50, null=True, blank=True, decimal_places=2, default=0)
    investment_sequence = models.PositiveIntegerField(default=1, verbose_name='Investment Sequence')
    profit = models.DecimalField(
        max_digits=50,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Profit Amount',
        help_text='Profit earned on this contribution'
    )
    
    deduction = models.DecimalField(
        max_digits=50,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Deduction Amount',
        help_text='Amount deducted based on user group percentage'
    )
    
    final_profit = models.DecimalField(
        max_digits=50,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Final Profit',
        help_text='Final profit after deduction (profit - deduction)'
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name='Updated At')
    
    class Meta:
        verbose_name = 'Property Contribution'
        verbose_name_plural = 'Property Contributions'
        ordering = ['property', 'user', 'investment_sequence']
        indexes = [
            models.Index(fields=['user', 'property', 'investment_sequence']),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name()} → {self.property.title} (#{self.investment_sequence}: {self.shares} shares)"
    
    def calculate_shares(self):
        """Calculate number of shares based on contribution amount"""
        share_price = SharePrice.get_current_price()
        if share_price > 0 and self.contribution > 0:
            self.shares = (self.contribution / share_price).quantize(
                Decimal('0.000001'), rounding=ROUND_HALF_UP
            )
        else:
            self.shares = Decimal('0')
        return self.shares
    
    def calculate_total_days(self):
        """Calculate total days invested until selling date"""
        if not self.investment_date or not self.property.selling_date:
            return 0
        delta = self.property.selling_date - self.investment_date
        return max(0, delta.days)
    
    def get_contribution_percentage(self):
        total_contribution = PropertyContribution.objects.filter(
            property=self.property
        ).aggregate(total=models.Sum('contribution'))['total'] or Decimal('0')
        if total_contribution == 0:
            return Decimal('0')
        return (self.contribution / total_contribution * 100).quantize(Decimal('0.01'))

      
class Property(models.Model):
    STATUS_CHOICES = [
        ('wishlist', 'Wish List'),
        ('failed_to_bought', 'Failed to bought'),
        ('move_to_next_option', 'Move to next Auction'),
        ('bought', 'Bought'),
        ('ready_to_sell', 'Ready to sell'),
        ('sold', 'Sold'),
    ]
    title = models.CharField(max_length=200)
    description = models.TextField()
    estimated_price= models.DecimalField(max_digits=50, decimal_places=2,null=True, blank=True, verbose_name="Estimated Price")
    booking_fee = models.DecimalField(max_digits=50, decimal_places=2,null=True, blank=True, verbose_name="Booking fee")
    auction_price = models.DecimalField(max_digits=50, decimal_places=2,null=True, blank=True, verbose_name="Auction Price")
    buying_price = models.DecimalField(max_digits=50, decimal_places=6,null=True, blank=True, verbose_name="Buying Price")
    service_cost = models.DecimalField(max_digits=50, decimal_places=6,null=True, blank=True, verbose_name="Service Cost")
    asking_price = models.DecimalField(max_digits=50, decimal_places=2, null=True, blank=True, verbose_name="Asking Price")
    selling_price = models.DecimalField(max_digits=50, decimal_places=2, null=True, blank=True, verbose_name="Selling Price")
    acquisition_cost = models.DecimalField(max_digits=50, decimal_places=6, null=True, blank=True, verbose_name="Acquisition Cost")
    profit = models.DecimalField(max_digits=50, decimal_places=2,null=True, blank=True, verbose_name="Profit")
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=10)
    
    # Add status field
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='wishlist')

    bedrooms = models.IntegerField(verbose_name="Bedrooms")
    bathrooms = models.FloatField(verbose_name="Bathrooms")
    dining_rooms = models.IntegerField(null=True, blank=True,verbose_name="Dining Rooms")
    square_feet = models.IntegerField(verbose_name="Total Square Feet")
    auction_date = models.DateField(null=True, blank=True)
    buying_date = models.DateField(null=True, blank=True)
    selling_date = models.DateField(null=True, blank=True)
    listed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    listed_date = models.DateTimeField(auto_now_add=True)
    url = models.URLField(null=True, blank=True)
    contributors = models.ManyToManyField(
        User, 
        related_name='contributed_properties',
        blank=True, null=True,
        verbose_name='Property Contributors'
    )
    is_contribution_locked = models.BooleanField(default=False, verbose_name='Contribution Locked')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name='Updated At')

    
    def __str__(self):
        return self.title

    def get_contributors(self):
        return self.contributors.filter(is_active=True)

    def deduct_property_costs_proportionally(self, investment_data, investment_dates=None):
        """
        investment_data: {user_id: invest_amount}
        investment_dates: {user_id: date_string or date object} (optional)
        """
        if self.buying_price is None:
            return False

        total_cost = (self.buying_price or Decimal('0')) + (self.service_cost or Decimal('0'))
        if total_cost <= 0:
            return False

        contributors = list(self.get_contributors())
        if not contributors:
            return False

        total_invest = sum(investment_data.values()) or Decimal('0')
        if total_invest <= 0:
            return False

        self.refund_all_contributions()

        with transaction.atomic():
            distributed_total = Decimal('0')
            
            # Default investment date = buying_date or today
            default_date = self.buying_date or date.today()
            
            for i, user in enumerate(contributors):
                invest_amount = Decimal(investment_data.get(user.id, 0))
                
                if i == len(contributors) - 1:
                    used_amount = total_cost - distributed_total
                else:
                    used_amount = (total_cost * invest_amount / total_invest).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                
                distributed_total += used_amount
                remaining_amount = invest_amount - used_amount
                
                # Investment date নির্ধারণ
                inv_date = default_date
                if investment_dates and user.id in investment_dates:
                    date_val = investment_dates[user.id]
                    if isinstance(date_val, str):
                        try:
                            inv_date = datetime.strptime(date_val, '%Y-%m-%d').date()
                        except:
                            inv_date = default_date
                    else:
                        inv_date = date_val
                
                user.balance -= used_amount
                user.save(update_fields=['balance'])

                PropertyContribution.objects.create(
                    user=user,
                    property=self,
                    contribution=used_amount,
                    invest_amount=invest_amount,
                    remaining=remaining_amount,
                    ratio=(used_amount / total_cost * 100) if total_cost > 0 else 0,
                    investment_date=inv_date,
                    total_days=0,
                    days_proportion=Decimal('0'),
                    investment_ratio=Decimal('0'),
                    profit_weight=Decimal('0')
                )

        return True

    def deduct_property_costs_with_fixed_users(self, investment_data, fixed_users, investment_dates=None):
        """
        investment_dates: {user_id: date}
        """
        if self.buying_price is None:
            return False

        buying_price = self.buying_price or Decimal('0')
        service_cost = self.service_cost or Decimal('0')
        total_cost = buying_price + service_cost

        if total_cost <= 0 or not investment_data:
            return False

        self.refund_all_contributions()
        default_date = self.buying_date or date.today()

        with transaction.atomic():
            fixed_total = Decimal('0')
            fixed_contributions = []

            for user_id in fixed_users:
                if user_id in investment_data:
                    invest_amount = Decimal(str(investment_data[user_id]))
                    try:
                        user = User.objects.get(id=user_id)
                        if user.balance < invest_amount:
                            return False
                        
                        inv_date = default_date
                        if investment_dates and user_id in investment_dates:
                            date_val = investment_dates[user_id]
                            if isinstance(date_val, str):
                                try:
                                    inv_date = datetime.strptime(date_val, '%Y-%m-%d').date()
                                except:
                                    pass
                            else:
                                inv_date = date_val
                        
                        fixed_contributions.append({
                            'user': user,
                            'invest_amount': invest_amount,
                            'contribution': invest_amount,
                            'investment_date': inv_date
                        })
                        fixed_total += invest_amount
                    except User.DoesNotExist:
                        continue

            if fixed_total > total_cost:
                return False

            remaining_cost = total_cost - fixed_total
            non_fixed_data = {}
            total_non_fixed_invest = Decimal('0')

            for user_id, amount in investment_data.items():
                if user_id not in fixed_users:
                    invest_amt = Decimal(str(amount))
                    non_fixed_data[user_id] = invest_amt
                    total_non_fixed_invest += invest_amt

            proportional_contributions = []

            if remaining_cost > 0:
                if total_non_fixed_invest <= 0:
                    return False

                distributed_total = Decimal('0')
                non_fixed_items = list(non_fixed_data.items())

                for i, (user_id, invest_amount) in enumerate(non_fixed_items):
                    try:
                        user = User.objects.get(id=user_id)
                    except User.DoesNotExist:
                        continue

                    ratio = invest_amount / total_non_fixed_invest

                    if i == len(non_fixed_items) - 1:
                        actual_contribution = remaining_cost - distributed_total
                    else:
                        actual_contribution = (remaining_cost * ratio).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)

                    distributed_total += actual_contribution

                    if user.balance < actual_contribution:
                        return False
                    
                    inv_date = default_date
                    if investment_dates and user_id in investment_dates:
                        date_val = investment_dates[user_id]
                        if isinstance(date_val, str):
                            try:
                                inv_date = datetime.strptime(date_val, '%Y-%m-%d').date()
                            except:
                                pass
                        else:
                            inv_date = date_val

                    proportional_contributions.append({
                        'user': user,
                        'invest_amount': invest_amount,
                        'contribution': actual_contribution,
                        'investment_date': inv_date
                    })

            elif remaining_cost == 0 and non_fixed_data:
                for user_id, invest_amount in non_fixed_data.items():
                    try:
                        user = User.objects.get(id=user_id)
                        inv_date = default_date
                        if investment_dates and user_id in investment_dates:
                            date_val = investment_dates[user_id]
                            if isinstance(date_val, str):
                                try:
                                    inv_date = datetime.strptime(date_val, '%Y-%m-%d').date()
                                except:
                                    pass
                            else:
                                inv_date = date_val
                        
                        proportional_contributions.append({
                            'user': user,
                            'invest_amount': invest_amount,
                            'contribution': Decimal('0'),
                            'investment_date': inv_date
                        })
                    except User.DoesNotExist:
                        continue

            # Save fixed contributions
            for contrib_data in fixed_contributions:
                user = contrib_data['user']
                invest_amount = contrib_data['invest_amount']
                contribution = contrib_data['contribution']
                inv_date = contrib_data['investment_date']

                user.balance -= contribution
                user.save(update_fields=['balance'])

                PropertyContribution.objects.create(
                    user=user,
                    property=self,
                    invest_amount=invest_amount,
                    contribution=contribution,
                    remaining=Decimal('0'),
                    ratio=(contribution / total_cost) if total_cost > 0 else Decimal('0'),
                    is_fixed_amount=True,
                    investment_date=inv_date,
                    total_days=0,
                    days_proportion=Decimal('0'),
                    investment_ratio=Decimal('0'),
                    profit_weight=Decimal('0')
                )

            # Save proportional contributions
            for contrib_data in proportional_contributions:
                user = contrib_data['user']
                invest_amount = contrib_data['invest_amount']
                contribution = contrib_data['contribution']
                inv_date = contrib_data['investment_date']

                user.balance -= contribution
                user.save(update_fields=['balance'])

                remaining = invest_amount - contribution

                PropertyContribution.objects.create(
                    user=user,
                    property=self,
                    invest_amount=invest_amount,
                    contribution=contribution,
                    remaining=remaining,
                    ratio=(contribution / total_cost) if total_cost > 0 else Decimal('0'),
                    is_fixed_amount=False,
                    investment_date=inv_date,
                    total_days=0,
                    days_proportion=Decimal('0'),
                    investment_ratio=Decimal('0'),
                    profit_weight=Decimal('0')
                )

        return True

    def deduct_property_costs_three_box_system(self, fixed_investments, active_investments, investment_dates_list=None):
        """
        Three-box investment system:
        1. Fixed Box (Top): First level buyers - fixed amounts, cannot change
        2. Active Box (Middle): Current contributors - proportional distribution
        3. Inactive Box (Bottom): Available investors with remaining balance
        """
        if self.buying_price is None:
            return False
        
        buying_price = self.buying_price or Decimal('0')
        service_cost = self.service_cost or Decimal('0')
        total_cost = buying_price + service_cost
        
        if total_cost <= 0:
            return False
        
        self.refund_all_contributions()
        default_date = self.buying_date or date.today()
        
        with transaction.atomic():
            
            fixed_total = Decimal('0')
            print(f"\n📦 BOX 1 (FIXED/FIRST LEVEL BUYERS):")
            print("-" * 80)
            
            for inv in fixed_investments:
                user_id = inv['user_id']
                invest_amount = Decimal(str(inv['invest_amount']))
                sequence = inv.get('sequence', 1)
                
                try:
                    user = User.objects.get(id=user_id)
                    
                    if user.balance < invest_amount:
                        print(f"❌ User {user.get_full_name()} has insufficient balance")
                        return False
                    
                   
                    inv_date = default_date
                    if investment_dates_list:
                        date_info = next((d for d in investment_dates_list 
                                        if d['user_id'] == user_id and d['sequence'] == sequence), None)
                        if date_info:
                            date_val = date_info['date']
                            if isinstance(date_val, str):
                                try:
                                    inv_date = datetime.strptime(date_val, '%Y-%m-%d').date()
                                except:
                                    pass
                            else:
                                inv_date = date_val
                    
                    
                    user.balance -= invest_amount
                    user.save(update_fields=['balance'])
                    
                    
                    PropertyContribution.objects.create(
                        user=user,
                        property=self,
                        invest_amount=invest_amount,
                        contribution=invest_amount,  # Same as invest_amount for fixed
                        remaining=Decimal('0'),
                        ratio=(invest_amount / total_cost) if total_cost > 0 else Decimal('0'),
                        is_fixed_amount=True,
                        investment_date=inv_date,
                        investment_sequence=1,  # Always first contribution
                        total_days=0,
                        days_proportion=Decimal('0'),
                        investment_ratio=Decimal('0'),
                        profit_weight=Decimal('0')
                    )
                    
                    fixed_total += invest_amount
                    print(f"  ✅ {user.get_full_name():20} | Fixed: ${invest_amount} (1st contribution)")
                    
                except User.DoesNotExist:
                    print(f"❌ User with id {user_id} not found")
                    return False
            
            print(f"\n  {'FIXED BOX TOTAL':20} | ${fixed_total}")
            
            if fixed_total > total_cost:
                print(f"❌ Fixed investments ({fixed_total}) exceed total cost ({total_cost})")
                return False
            
            
            remaining_cost = total_cost - fixed_total
            print(f"\n📦 BOX 2 (ACTIVE CONTRIBUTORS):")
            print("-" * 80)
            print(f"  Remaining Cost to Distribute: ${remaining_cost}")
            
            if remaining_cost > 0 and active_investments:
                total_active_invest = sum(Decimal(str(inv['invest_amount'])) 
                                        for inv in active_investments)
                
                if total_active_invest <= 0:
                    print(f"❌ No active investment amount available")
                    return False
                
                distributed_total = Decimal('0')
                
                for i, inv in enumerate(active_investments):
                    user_id = inv['user_id']
                    invest_amount = Decimal(str(inv['invest_amount']))
                    sequence = inv.get('sequence', 1)
                    
                    try:
                        user = User.objects.get(id=user_id)
                    except User.DoesNotExist:
                        continue
                    
                    ratio = invest_amount / total_active_invest
                    
                    # Last user gets exact remaining to avoid rounding issues
                    if i == len(active_investments) - 1:
                        actual_contribution = remaining_cost - distributed_total
                    else:
                        actual_contribution = (remaining_cost * ratio).quantize(
                            Decimal('0.000001'), rounding=ROUND_HALF_UP
                        )
                        distributed_total += actual_contribution
                    
                    if user.balance < actual_contribution:
                        print(f"❌ User {user.get_full_name()} has insufficient balance")
                        return False
                    
                    # Get investment date
                    inv_date = default_date
                    if investment_dates_list:
                        date_info = next((d for d in investment_dates_list 
                                        if d['user_id'] == user_id and d['sequence'] == sequence), None)
                        if date_info:
                            date_val = date_info['date']
                            if isinstance(date_val, str):
                                try:
                                    inv_date = datetime.strptime(date_val, '%Y-%m-%d').date()
                                except:
                                    pass
                            else:
                                inv_date = date_val
                    
                    # Deduct from user balance
                    user.balance -= actual_contribution
                    user.save(update_fields=['balance'])
                    
                    remaining_amount = invest_amount - actual_contribution
                    
                    # Create proportional contribution
                    PropertyContribution.objects.create(
                        user=user,
                        property=self,
                        invest_amount=invest_amount,
                        contribution=actual_contribution,
                        remaining=remaining_amount,
                        ratio=(actual_contribution / total_cost) if total_cost > 0 else Decimal('0'),
                        is_fixed_amount=False,
                        investment_date=inv_date,
                        investment_sequence=sequence,
                        total_days=0,
                        days_proportion=Decimal('0'),
                        investment_ratio=Decimal('0'),
                        profit_weight=Decimal('0')
                    )
                    
                    print(f"  ✅ {user.get_full_name():20} | Invest: ${invest_amount} | Used: ${actual_contribution} | Remaining: ${remaining_amount}")
            
            elif remaining_cost == 0:
                print(f"  ℹ️  No remaining cost - fixed investments covered total cost")
            
            print("\n" + "="*80)
            print("✅ THREE-BOX SYSTEM PROCESSING COMPLETED")
            print("="*80)
        
        return True
    def deduct_property_costs_with_multiple_investments(self, investments_list, investment_dates_list=None):
        """
        NEW METHOD: Handle multiple investments from same users
        
        investments_list: [
            {'user_id': 1, 'invest_amount': 5000, 'is_fixed': False, 'sequence': 1},
            {'user_id': 1, 'invest_amount': 2000, 'is_fixed': False, 'sequence': 2},
            {'user_id': 2, 'invest_amount': 3000, 'is_fixed': True, 'sequence': 1},
        ]
        
        investment_dates_list: [
            {'user_id': 1, 'sequence': 1, 'date': '2024-01-01'},
            {'user_id': 1, 'sequence': 2, 'date': '2024-02-01'},
            {'user_id': 2, 'sequence': 1, 'date': '2024-01-15'},
        ]
        """
        if self.buying_price is None:
            return False
        
        buying_price = self.buying_price or Decimal('0')
        service_cost = self.service_cost or Decimal('0')
        total_cost = buying_price + service_cost
        
        if total_cost <= 0 or not investments_list:
            return False
        
        
        self.refund_all_contributions()
        
        default_date = self.buying_date or date.today()
        
        with transaction.atomic():
            
            fixed_investments = [inv for inv in investments_list if inv.get('is_fixed', False)]
            non_fixed_investments = [inv for inv in investments_list if not inv.get('is_fixed', False)]
            
            
            fixed_total = sum(Decimal(str(inv['invest_amount'])) for inv in fixed_investments)
            
            if fixed_total > total_cost:
                print(f"❌ Fixed investments ({fixed_total}) exceed total cost ({total_cost})")
                return False
            
            remaining_cost = total_cost - fixed_total
            
            # Process fixed investments
            for inv in fixed_investments:
                user_id = inv['user_id']
                invest_amount = Decimal(str(inv['invest_amount']))
                sequence = inv.get('sequence', 1)
                
                try:
                    user = User.objects.get(id=user_id)
                    if user.balance < invest_amount:
                        print(f"❌ User {user.get_full_name()} has insufficient balance")
                        return False
                    
                    # Get investment date
                    inv_date = default_date
                    if investment_dates_list:
                        date_info = next((d for d in investment_dates_list 
                                        if d['user_id'] == user_id and d['sequence'] == sequence), None)
                        if date_info:
                            date_val = date_info['date']
                            if isinstance(date_val, str):
                                try:
                                    inv_date = datetime.strptime(date_val, '%Y-%m-%d').date()
                                except:
                                    pass
                            else:
                                inv_date = date_val
                    
                    
                    user.balance -= invest_amount
                    user.save(update_fields=['balance'])
                    
                    
                    PropertyContribution.objects.create(
                        user=user,
                        property=self,
                        invest_amount=invest_amount,
                        contribution=invest_amount,
                        remaining=Decimal('0'),
                        ratio=(invest_amount / total_cost) if total_cost > 0 else Decimal('0'),
                        is_fixed_amount=True,
                        investment_date=inv_date,
                        investment_sequence=sequence,
                        total_days=0,
                        days_proportion=Decimal('0'),
                        investment_ratio=Decimal('0'),
                        profit_weight=Decimal('0')
                    )
                    
                except User.DoesNotExist:
                    print(f"❌ User with id {user_id} not found")
                    return False
            
            
            if remaining_cost > 0 and non_fixed_investments:
                total_non_fixed_invest = sum(Decimal(str(inv['invest_amount'])) 
                                            for inv in non_fixed_investments)
                
                if total_non_fixed_invest <= 0:
                    print(f"❌ No non-fixed investment amount available")
                    return False
                
                distributed_total = Decimal('0')
                
                for i, inv in enumerate(non_fixed_investments):
                    user_id = inv['user_id']
                    invest_amount = Decimal(str(inv['invest_amount']))
                    sequence = inv.get('sequence', 1)
                    
                    try:
                        user = User.objects.get(id=user_id)
                    except User.DoesNotExist:
                        continue
                    
                    ratio = invest_amount / total_non_fixed_invest
                    
                    
                    if i == len(non_fixed_investments) - 1:
                        actual_contribution = remaining_cost - distributed_total
                    else:
                        actual_contribution = (remaining_cost * ratio).quantize(
                            Decimal('0.000001'), rounding=ROUND_HALF_UP
                        )
                    
                    distributed_total += actual_contribution
                    
                    if user.balance < actual_contribution:
                        print(f"❌ User {user.get_full_name()} has insufficient balance")
                        return False
                    
                    # Get investment date
                    inv_date = default_date
                    if investment_dates_list:
                        date_info = next((d for d in investment_dates_list 
                                        if d['user_id'] == user_id and d['sequence'] == sequence), None)
                        if date_info:
                            date_val = date_info['date']
                            if isinstance(date_val, str):
                                try:
                                    inv_date = datetime.strptime(date_val, '%Y-%m-%d').date()
                                except:
                                    pass
                            else:
                                inv_date = date_val
                    
                   
                    user.balance -= actual_contribution
                    user.save(update_fields=['balance'])
                    
                    remaining_amount = invest_amount - actual_contribution
                    
                    
                    PropertyContribution.objects.create(
                        user=user,
                        property=self,
                        invest_amount=invest_amount,
                        contribution=actual_contribution,
                        remaining=remaining_amount,
                        ratio=(actual_contribution / total_cost) if total_cost > 0 else Decimal('0'),
                        is_fixed_amount=False,
                        investment_date=inv_date,
                        investment_sequence=sequence,
                        total_days=0,
                        days_proportion=Decimal('0'),
                        investment_ratio=Decimal('0'),
                        profit_weight=Decimal('0')
                    )
            
            elif remaining_cost == 0 and non_fixed_investments:
                
                for inv in non_fixed_investments:
                    user_id = inv['user_id']
                    invest_amount = Decimal(str(inv['invest_amount']))
                    sequence = inv.get('sequence', 1)
                    
                    try:
                        user = User.objects.get(id=user_id)
                        
                        inv_date = default_date
                        if investment_dates_list:
                            date_info = next((d for d in investment_dates_list 
                                            if d['user_id'] == user_id and d['sequence'] == sequence), None)
                            if date_info:
                                date_val = date_info['date']
                                if isinstance(date_val, str):
                                    try:
                                        inv_date = datetime.strptime(date_val, '%Y-%m-%d').date()
                                    except:
                                        pass
                                else:
                                    inv_date = date_val
                        
                        PropertyContribution.objects.create(
                            user=user,
                            property=self,
                            invest_amount=invest_amount,
                            contribution=Decimal('0'),
                            remaining=invest_amount,
                            ratio=Decimal('0'),
                            is_fixed_amount=False,
                            investment_date=inv_date,
                            investment_sequence=sequence,
                            total_days=0,
                            days_proportion=Decimal('0'),
                            investment_ratio=Decimal('0'),
                            profit_weight=Decimal('0')
                        )
                    except User.DoesNotExist:
                        continue
        
        return True
    
    def get_user_investment_sequences(self, user):
        """Get all investment sequences for a user in this property"""
        return PropertyContribution.objects.filter(
            property=self,
            user=user
        ).values_list('investment_sequence', flat=True).distinct().order_by('investment_sequence')
    
    def get_next_sequence_number(self, user):
        """Get the next sequence number for a user's investment"""
        max_seq = PropertyContribution.objects.filter(
            property=self,
            user=user
        ).aggregate(models.Max('investment_sequence'))['investment_sequence__max']
        
        return (max_seq or 0) + 1
    def calculate_profit_weights(self):
        """
        Share-based profit weight calculation:
        Weight = Days Proportion × Number of Shares
        
        More shares + More days = Higher weight
        """
        if not self.selling_date:
            print("❌ No selling date found!")
            return False

        contributions = PropertyContribution.objects.filter(property=self)
        if not contributions.exists():
            print("❌ No contributions found!")
            return False

        print("\n" + "="*80)
        print(f"🏠 CALCULATING SHARE-BASED PROFIT WEIGHTS FOR: {self.title}")
        print("="*80)
        
        share_price = SharePrice.get_current_price()
        print(f"\n💰 Current Share Price: ${share_price}")

        with transaction.atomic():
            
            print("\n📊 STEP 1: Calculating Shares")
            print("-" * 80)
            for contrib in contributions:
                contrib.calculate_shares()
                print(f"  {contrib.user.get_full_name():20} | Contribution: ${contrib.contribution:8.2f} | Shares: {float(contrib.shares):.6f}")
                contrib.save(update_fields=['shares'])
            
           
            print("\n📅 STEP 2: Calculating Total Days")
            print("-" * 80)
            for contrib in contributions:
                if contrib.investment_date:
                    delta = self.selling_date - contrib.investment_date
                    contrib.total_days = max(1, delta.days)
                    print(f"  {contrib.user.get_full_name():20} | Investment: {contrib.investment_date} | Selling: {self.selling_date} | Days: {contrib.total_days}")
                else:
                    contrib.total_days = 0
                    print(f"  {contrib.user.get_full_name():20} | No investment date | Days: 0")
                contrib.save(update_fields=['total_days'])

           
            max_days = contributions.aggregate(models.Max('total_days'))['total_days__max'] or 1
            print(f"\n📊 STEP 3: Calculating Days Proportion (Max Days: {max_days})")
            print("-" * 80)

            for contrib in contributions:
                if max_days > 0 and contrib.total_days > 0:
                    contrib.days_proportion = (Decimal(str(contrib.total_days)) / Decimal(str(max_days))).quantize(
                        Decimal('0.000001'), rounding=ROUND_HALF_UP
                    )
                    print(f"  {contrib.user.get_full_name():20} | Days: {contrib.total_days:3} / {max_days:3} = {float(contrib.days_proportion):.4f}")
                else:
                    contrib.days_proportion = Decimal('0')
                    print(f"  {contrib.user.get_full_name():20} | Days: 0 | Proportion: 0.0000")
                contrib.save(update_fields=['days_proportion'])

            
            print(f"\n⚖️  STEP 4: Calculating Profit Weight (Days Proportion × Shares)")
            print("-" * 80)
            total_weight = Decimal('0')
            
            for contrib in contributions:
                contrib.profit_weight = (contrib.days_proportion * contrib.shares).quantize(
                    Decimal('0.000001'), rounding=ROUND_HALF_UP
                )
                total_weight += contrib.profit_weight
                print(f"  {contrib.user.get_full_name():20} | {float(contrib.days_proportion):.4f} × {float(contrib.shares):.6f} shares = {float(contrib.profit_weight):.6f}")
                contrib.save(update_fields=['profit_weight'])
            
            print(f"\n  {'TOTAL WEIGHT':20} | {float(total_weight):.6f}")
            print("="*80)

        return True

    def distribute_sale_proceeds(self):
        """
        Modified distribution system:
        - NO 15% office deduction from total profit
        - Individual deductions based on user groups per contribution
        - Deducted amounts go to office manager's balance
        - Track deduction history
        """
        if self.is_contribution_locked:
            print("🔒 Contribution already locked!")
            return True

        if not self.selling_price or self.selling_price <= 0:
            print("❌ Invalid selling price!")
            return False

        contributions = PropertyContribution.objects.filter(property=self)
        if not contributions.exists():
            print("❌ No contributions found!")
            return False

        total_contribution = sum(c.contribution for c in contributions)
        if total_contribution <= 0:
            print("❌ Total contribution is zero!")
            return False

        selling_price = Decimal(str(self.selling_price))
        total_profit = selling_price - total_contribution

        print("\n" + "="*100)
        print(f"💵 GROUP-BASED PROFIT DISTRIBUTION FOR: {self.title}")
        print("="*100)
        print(f"\n📊 FINANCIAL SUMMARY:")
        print(f"  Total Investment:            ${float(total_contribution):,.2f}")
        print(f"  Selling Price:               ${float(selling_price):,.2f}")
        print(f"  Total Profit:                ${float(total_profit):,.2f}")

        if total_profit <= 0:
            print("\n⚠️  NO PROFIT - Returning investments only")
            with transaction.atomic():
                for contrib in contributions:
                    user = contrib.user
                    user.balance += contrib.contribution
                    user.save(update_fields=['balance'])
                    
                    
                    contrib.profit = Decimal('0.00')
                    contrib.deduction = Decimal('0.00')
                    contrib.final_profit = Decimal('0.00')
                    contrib.save(update_fields=['profit', 'deduction', 'final_profit'])
                    
                    print(f"  {user.get_full_name():20} | Refund: ${float(contrib.contribution):,.2f}")
                
                self.is_contribution_locked = True
                self.save(update_fields=['is_contribution_locked'])
            return True

        
        print(f"\n🔢 Calculating profit weights...")
        self.calculate_profit_weights()

        total_weight = sum(c.profit_weight for c in contributions)
        if total_weight <= 0:
            print("❌ Total weight is zero!")
            return False

        print(f"  Total Weight: {float(total_weight):.6f}")

        with transaction.atomic():
            user_totals = {}
            total_deductions = Decimal('0.00')
            distributed_profit = Decimal('0')
            
            print(f"\n💰 DISTRIBUTION DETAILS (PER CONTRIBUTION):")
            print("-" * 120)
            print(f"{'Name':20} | {'Group':15} | {'Seq':3} | {'Investment':>12} | {'Weight':>10} | "
                f"{'Profit':>12} | {'Deduct%':>8} | {'Deduction':>12} | {'Final':>12}")
            print("-" * 120)

            contributions_list = list(contributions)
            
            for i, contrib in enumerate(contributions_list):
                user = contrib.user
                user_id = user.id
                investment_return = contrib.contribution
                
                
                if i == len(contributions_list) - 1:
                    profit_share = total_profit - distributed_profit
                else:
                    profit_share = (
                        total_profit * contrib.profit_weight / total_weight
                    ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    distributed_profit += profit_share

                
                deduction_percentage = Decimal('0.00')
                group_name = "No Group"
                
                if user.user_group:
                    deduction_percentage = user.user_group.percentage
                    group_name = user.user_group.name
                
                
                deduction_amount = (
                    profit_share * deduction_percentage / Decimal('100')
                ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                
                
                final_profit = profit_share - deduction_amount
                
                
                contrib.profit = profit_share
                contrib.deduction = deduction_amount
                contrib.final_profit = final_profit
                contrib.save(update_fields=['profit', 'deduction', 'final_profit'])
                
                
                office_manager = User.get_office_manager()
                DeductionHistory.objects.create(
                    property=self,
                    user=user,
                    property_contribution=contrib,
                    profit_share=profit_share,
                    deduction_percentage=deduction_percentage,
                    deduction_amount=deduction_amount,
                    sequence_number=contrib.investment_sequence,
                    office_manager=office_manager
                )
                
                total_deductions += deduction_amount
                total_amount = investment_return + final_profit

                print(f"{user.get_full_name():20} | {group_name:15} | #{contrib.investment_sequence:2} | "
                    f"${float(investment_return):>11,.2f} | {float(contrib.profit_weight):>10.6f} | "
                    f"${float(profit_share):>11,.2f} | {float(deduction_percentage):>7.2f}% | "
                    f"${float(deduction_amount):>11,.2f} | ${float(final_profit):>11,.2f}")

                
                if user_id not in user_totals:
                    user_totals[user_id] = {
                        'user': user,
                        'investment': Decimal('0'),
                        'profit': Decimal('0'),
                        'deduction': Decimal('0'),
                        'final_profit': Decimal('0'),
                        'total': Decimal('0')
                    }
                
                user_totals[user_id]['investment'] += investment_return
                user_totals[user_id]['profit'] += profit_share
                user_totals[user_id]['deduction'] += deduction_amount
                user_totals[user_id]['final_profit'] += final_profit
                user_totals[user_id]['total'] += total_amount

            print("-" * 120)
            print(f"{'TOTALS':20} | {'':15} | {'':3} | ${float(total_contribution):>11,.2f} | "
                f"{float(total_weight):>10.6f} | ${float(total_profit):>11,.2f} | {'':>8} | "
                f"${float(total_deductions):>11,.2f} | ${float(total_profit - total_deductions):>11,.2f}")

            
            print(f"\n💰 UPDATING USER BALANCES:")
            print("-" * 100)
            for user_id, amounts in user_totals.items():
                user = User.objects.get(id=user_id)
                print(f"  {user.get_full_name():20} | Before: ${float(user.balance):>11,.2f}")
                print(f"  {'':20} | Return: ${float(amounts['investment']):>11,.2f}")
                print(f"  {'':20} | Profit: ${float(amounts['profit']):>11,.2f}")
                print(f"  {'':20} | Deduct: ${float(amounts['deduction']):>11,.2f}")
                print(f"  {'':20} | Final:  ${float(amounts['final_profit']):>11,.2f}")
                
             
                user.balance += amounts['total']
                user.save(update_fields=['balance'])
                
                print(f"  {'':20} | After:  ${float(user.balance):>11,.2f}\n")

            print(f"🏢 OFFICE MANAGEMENT:")
            print("-" * 100)
            print(f"  Total Deductions Collected: ${float(total_deductions):,.2f}")
            
            office_manager = User.get_office_manager()
            if office_manager:
                print(f"  ✅ Office Manager: {office_manager.get_full_name()}")
                office_manager = User.objects.get(id=office_manager.id)
                office_manager.balance += total_deductions
                office_manager.save(update_fields=['balance'])
                print(f"  ✅ Added ${float(total_deductions):,.2f} to office manager's balance")
            else:
                print(f"  ⚠️  No Office Manager - Adding to OfficeCost model")
                office_cost_record, _ = OfficeCost.objects.get_or_create(id=1)
                office_cost_record.balance += total_deductions
                office_cost_record.save(update_fields=['balance'])

            self.is_contribution_locked = True
            self.save(update_fields=['is_contribution_locked'])

        print("\n✅ Group-based distribution completed!")
        print("="*100 + "\n")
        return True

    def refund_all_contributions(self):
        contributions = PropertyContribution.objects.filter(property=self)
        
        if not contributions.exists():
            print(f"ℹ️  No contributions to refund for property {self.id}")
            return True
        
        print(f"\n{'='*50}")
        print(f" REFUNDING CONTRIBUTIONS")
        print(f"{'='*50}")
        
        with transaction.atomic():
            total_refunded = Decimal('0')
            for contrib in contributions:
                print(f"User: {contrib.user.email}")
                print(f"  Balance before: {contrib.user.balance}")
                print(f"  Refunding: {contrib.contribution}")
                
              
                contrib.user.balance += contrib.contribution
                contrib.user.save(update_fields=['balance'])
                
                print(f"  Balance after: {contrib.user.balance}")
                total_refunded += contrib.contribution
            
            
            contributions.delete()
            
            print(f"{'='*50}\n")
        
        return True

    def redistribute_contributions(self):
        contributions = PropertyContribution.objects.filter(property=self)
        if not contributions.exists():
            return False
        investment_data = {c.user.id: c.invest_amount for c in contributions}
        investment_dates = {c.user.id: c.investment_date for c in contributions if c.investment_date}
        return self.deduct_property_costs_proportionally(investment_data, investment_dates)

    def add_or_update_contributor(self, user, invest_amount, investment_date=None):
        """
        Add or update a contributor for this property.
        
        CRITICAL: When adding a new contributor, we MUST refund all existing 
        contributions first to ensure fair redistribution based on everyone's 
        full available balance.
        """
        if self.is_contribution_locked:
            print("🔒 Contribution is locked. Cannot add/update contributor.")
            return False
        

        is_new_contributor = user not in self.get_contributors()
        
        if is_new_contributor:
            print(f"\n{'='*60}")
            print(f"🆕 Adding NEW contributor: {user.get_full_name()}")
            print(f"{'='*60}")
            

            existing_contributions = PropertyContribution.objects.filter(property=self).exists()
            
            if existing_contributions:
                print(f"⚠️  Existing contributors found. Refunding all contributions first...")
                self.refund_all_contributions()
                print(f"✅ All contributions refunded successfully.")
        
       
        if not investment_date:
            investment_date = self.buying_date or date.today()
        
        
        self.contributors.add(user)
        
       
        PropertyContribution.objects.update_or_create(
            property=self,
            user=user,
            defaults={
                'invest_amount': invest_amount,
                'contribution': 0,  
                'remaining': invest_amount,
                'ratio': 0,  
                'investment_date': investment_date,
                'total_days': 0,
                'days_proportion': Decimal('0'),
                'investment_ratio': Decimal('0'),
                'profit_weight': Decimal('0'),
                'is_fixed_amount': False
            }
        )
        
        print(f"✅ Contributor record created/updated for {user.get_full_name()}")
        print(f"   Investment Amount: ${invest_amount}")
        print(f"   Investment Date: {investment_date}")
        
        
        print(f"\n🔄 Redistributing contributions...")
        success = self.redistribute_contributions()
        
        if success:
            print(f"✅ Redistribution completed successfully!")
        else:
            print(f"❌ Redistribution failed!")
        
        print(f"{'='*60}\n")
        
        return success

    def remove_contributor(self, user):
        if self.is_contribution_locked:
            return False

        if user not in self.get_contributors():
            return False

        with transaction.atomic():
            self.contributors.remove(user)
            remaining_contributors = list(self.get_contributors())
            if remaining_contributors:
                self.redistribute_contributions()

        return True

    def get_all_investors_contributions(self):
        active_investors = User.objects.filter(is_active=True, investor=True)
        default_date = self.buying_date or date.today()
        
        for user in active_investors:
            PropertyContribution.objects.get_or_create(
                user=user,
                property=self,
                defaults={
                    'invest_amount': Decimal('0'),
                    'contribution': Decimal('0'),
                    'remaining': Decimal('0'),
                    'ratio': Decimal('0'),
                    'investment_date': default_date,
                    'total_days': 0,
                    'days_proportion': Decimal('0'),
                    'investment_ratio': Decimal('0'),
                    'profit_weight': Decimal('0')
                }
            )
        return PropertyContribution.objects.filter(property=self)

    def recalculate_contributions(self):
        
        contributions = PropertyContribution.objects.filter(property=self)
        
        if not contributions.exists():
            print("❌ No contributions found")
            return False
        
       
        buying_price = self.buying_price or Decimal('0')
        service_cost = self.service_cost or Decimal('0')
        total_cost = buying_price + service_cost
        
        if total_cost <= 0:
            print("❌ Total cost is zero or negative")
            return False
        
        
        total_investment = sum(c.invest_amount for c in contributions)
        
        if total_investment <= 0:
            print("❌ Total investment is zero")
            return False
        
        
        previous_total_contribution = sum(c.contribution for c in contributions)
        
        print(f"\n{'='*60}")
        print(f"🔄 RECALCULATING CONTRIBUTIONS")
        print(f"{'='*60}")
        print(f"Total Investment: {total_investment}")
        print(f"Previous Total Contribution: {previous_total_contribution}")
        print(f"New Total Cost (buying + service): {total_cost}")
        print(f"Adjustment needed: {total_cost - previous_total_contribution}")
        print(f"{'='*60}\n")
        
        with transaction.atomic():
            distributed_total = Decimal('0')
            contribution_list = list(contributions)
            
            for i, contrib in enumerate(contribution_list):
                user = contrib.user
                investment = contrib.invest_amount
                previous_contribution = contrib.contribution
                
                
                ratio = investment / total_investment
                
                
                if i == len(contribution_list) - 1:
                    new_contribution = total_cost - distributed_total
                else:
                    new_contribution = (total_cost * ratio).quantize(
                        Decimal('0.000001'), rounding=ROUND_HALF_UP
                    )
                    distributed_total += new_contribution
                
               
                adjustment = new_contribution - previous_contribution
                
                print(f"👤 {user.email}")
                print(f"   Investment: {investment} ({ratio*100:.2f}%)")
                print(f"   Previous Contribution: {previous_contribution}")
                print(f"   New Contribution: {new_contribution}")
                print(f"   Adjustment: {adjustment:+.6f}")
                print(f"   Balance before adjustment: {user.balance}")
                
               
                if adjustment != 0:
                    
                    if adjustment > 0 and user.balance < adjustment:
                        print(f"   ❌ ERROR: Insufficient balance for adjustment!")
                        return False
                    
                    user.balance -= adjustment
                    user.save(update_fields=['balance'])
                
                contrib.contribution = new_contribution
                contrib.ratio = ratio
                contrib.save(update_fields=['contribution', 'ratio'])
                
                print(f"   Balance after adjustment: {user.balance}")
                print()
            
            print(f"{'='*60}")
            print(f"RECALCULATION COMPLETED")
            print(f"{'='*60}\n")
        
        return True
    
    def adjust_contributions_for_service_cost_change(self, service_cost_increase):
        """
        Adjust contributions when service cost increases (e.g., expense approval)
        WITHOUT refunding - just deduct the additional amount proportionally
        
        ✅ FIXED: Only deduct from ACTIVE (non-fixed) contributors
        """
        if service_cost_increase <= 0:
            return True
        
        # ✅ Get ONLY ACTIVE (non-fixed) contributors who have contributed
        contributions = PropertyContribution.objects.filter(
            property=self,
            contribution__gt=0,
            is_fixed_amount=False  # ✅ CRITICAL: Only non-fixed (Active Layer)
        ).select_related('user')
        
        if not contributions.exists():
            print("❌ No active (non-fixed) contributions found")
            return False
        
        # Calculate total contribution from ACTIVE contributors only
        total_contribution = sum(c.contribution for c in contributions)
        
        if total_contribution <= 0:
            print("❌ Total active contribution is zero")
            return False
        
        print(f"\n{'='*80}")
        print(f"💰 ADJUSTING ACTIVE LAYER CONTRIBUTIONS FOR SERVICE COST INCREASE")
        print(f"{'='*80}")
        print(f"Property: {self.title}")
        print(f"Service Cost Increase: ${service_cost_increase:.2f}")
        print(f"Total Active Contribution: ${total_contribution:.2f}")
        print(f"Active Contributors (non-fixed): {contributions.count()}")
        print(f"{'='*80}\n")
        
        with transaction.atomic():
            distributed_total = Decimal('0')
            contribution_list = list(contributions)
            
            for i, contrib in enumerate(contribution_list):
                user = contrib.user
                
                # Calculate this user's share of the increase (proportional to their active contribution)
                ratio = contrib.contribution / total_contribution
                
                # Last user gets exact remaining to avoid rounding issues
                if i == len(contribution_list) - 1:
                    user_share = service_cost_increase - distributed_total
                else:
                    user_share = (service_cost_increase * ratio).quantize(
                        Decimal('0.000001'), rounding=ROUND_HALF_UP
                    )
                    distributed_total += user_share
                
                # Check if user has sufficient balance
                if user.balance < user_share:
                    print(f"❌ {user.get_full_name()} has insufficient balance!")
                    print(f"   Required: ${user_share:.2f}, Available: ${user.balance:.2f}")
                    return False
                
                # Deduct from user balance
                old_balance = user.balance
                user.balance -= user_share
                user.save(update_fields=['balance'])
                
                # Update contribution amounts
                old_contribution = contrib.contribution
                contrib.contribution += user_share
                
                # Recalculate acquisition cost for ratio
                acquisition_cost = (self.buying_price or Decimal('0')) + (self.service_cost or Decimal('0')) + service_cost_increase
                contrib.ratio = (contrib.contribution / acquisition_cost * 100) if acquisition_cost > 0 else 0
                contrib.save(update_fields=['contribution', 'ratio'])
                
                print(f"👤 {user.get_full_name():20}")
                print(f"   Share of increase: ${user_share:.2f} ({ratio*100:.2f}%)")
                print(f"   Balance: ${old_balance:.2f} → ${user.balance:.2f}")
                print(f"   Contribution: ${old_contribution:.2f} → ${contrib.contribution:.2f}")
                print(f"   Layer: ACTIVE (non-fixed)")
                print()
            
            print(f"{'='*80}")
            print(f"✅ ACTIVE LAYER ADJUSTMENT COMPLETED")
            print(f"   Fixed Layer contributors were NOT affected")
            print(f"{'='*80}\n")
        
        return True
    # def adjust_contributions_for_service_cost_change(self, service_cost_increase):
    #     """
    #     Adjust contributions when service cost increases (e.g., expense approval)
    #     WITHOUT refunding - just deduct the additional amount proportionally
        
    #     This avoids double deduction by only charging the incremental cost.
    #     """
    #     if service_cost_increase <= 0:
    #         return True
        
    #     # Get active contributors (those who have contributed)
    #     contributions = PropertyContribution.objects.filter(
    #         property=self,
    #         contribution__gt=0
    #     ).select_related('user')
        
    #     if not contributions.exists():
    #         print("❌ No active contributions found")
    #         return False
        
    #     # Calculate total contribution to determine ratios
    #     total_contribution = sum(c.contribution for c in contributions)
        
    #     if total_contribution <= 0:
    #         print("❌ Total contribution is zero")
    #         return False
        
    #     print(f"\n{'='*80}")
    #     print(f"💰 ADJUSTING CONTRIBUTIONS FOR SERVICE COST INCREASE")
    #     print(f"{'='*80}")
    #     print(f"Property: {self.title}")
    #     print(f"Service Cost Increase: ${service_cost_increase:.2f}")
    #     print(f"Total Current Contribution: ${total_contribution:.2f}")
    #     print(f"Active Contributors: {contributions.count()}")
    #     print(f"{'='*80}\n")
        
    #     with transaction.atomic():
    #         distributed_total = Decimal('0')
    #         contribution_list = list(contributions)
            
    #         for i, contrib in enumerate(contribution_list):
    #             user = contrib.user
                
    #             # Calculate this user's share of the increase
    #             ratio = contrib.contribution / total_contribution
                
    #             # Last user gets exact remaining to avoid rounding issues
    #             if i == len(contribution_list) - 1:
    #                 user_share = service_cost_increase - distributed_total
    #             else:
    #                 user_share = (service_cost_increase * ratio).quantize(
    #                     Decimal('0.000001'), rounding=ROUND_HALF_UP
    #                 )
    #                 distributed_total += user_share
                
    #             # Check if user has sufficient balance
    #             if user.balance < user_share:
    #                 print(f"❌ {user.get_full_name()} has insufficient balance!")
    #                 print(f"   Required: ${user_share:.2f}, Available: ${user.balance:.2f}")
    #                 return False
                
    #             # Deduct from user balance
    #             old_balance = user.balance
    #             user.balance -= user_share
    #             user.save(update_fields=['balance'])
                
    #             # Update contribution amounts
    #             old_contribution = contrib.contribution
    #             contrib.contribution += user_share
    #             contrib.ratio = (contrib.contribution / (total_contribution + service_cost_increase) * 100) if (total_contribution + service_cost_increase) > 0 else 0
    #             contrib.save(update_fields=['contribution', 'ratio'])
                
    #             print(f"👤 {user.get_full_name():20}")
    #             print(f"   Share of increase: ${user_share:.2f} ({ratio*100:.2f}%)")
    #             print(f"   Balance: ${old_balance:.2f} → ${user.balance:.2f}")
    #             print(f"   Contribution: ${old_contribution:.2f} → ${contrib.contribution:.2f}")
    #             print(f"   Remaining: ${contrib.remaining:.2f}")
    #             print()
            
    #         print(f"{'='*80}")
    #         print(f"✅ SERVICE COST ADJUSTMENT COMPLETED")
    #         print(f"{'='*80}\n")
        
    #     return True    
    def save(self, *args, **kwargs):
        """
        Enhanced save method with automatic selling_date handling
        """
       
        if self.selling_price is not None and self.acquisition_cost is not None:
            try:
                self.profit = Decimal(self.selling_price) - Decimal(self.acquisition_cost)
            except Exception:
                self.profit = None
        else:
            self.profit = None
        
        
        is_new = self._state.adding
        
        if not is_new:
            try:
                old_property = Property.objects.get(pk=self.pk)
                
                
                if old_property.status != 'sold' and self.status == 'sold':
                    if not self.selling_date:
                        self.selling_date = date.today()
                        print(f"✅ Auto-set selling_date to: {self.selling_date}")
                    
                    
                    super().save(*args, **kwargs)
                    
                   
                    if self.selling_price and not self.is_contribution_locked:
                        print(f"\n🔄 Status changed to 'sold' - Starting profit distribution...")
                        self.distribute_sale_proceeds()
                    return
                    
            except Property.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)

class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='properties/')
    is_primary = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Image for {self.property.title}"
    
    class Meta:
        ordering = ['-is_primary', 'id']

class OfficeCost(models.Model):
    """
    Singleton-like model storing office's accumulated balance (official cost).
    We will use get_or_create to access the single record.
    """
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return f"Office Cost Balance: {self.balance}"

    class Meta:
        verbose_name = "Office Cost"
        verbose_name_plural = "Office Costs"

class Bank(models.Model):
    name = models.CharField(max_length=100, verbose_name='Bank Name')
    logo = models.ImageField(upload_to='banks/logos/', verbose_name='Bank Logo', null=True, blank=True)
    icon = models.ImageField(upload_to='banks/icons/', verbose_name='Bank Icon', null=True, blank=True)
    qr_code = models.ImageField(upload_to='banks/qr_codes/', verbose_name='QR Code', null=True, blank=True)
    account_details = models.TextField(verbose_name='Account Details',null=True, blank=True)
    url = models.URLField(max_length=2048,null=True, blank=True)
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    is_card = models.BooleanField(default=False)
    is_square = models.BooleanField(default=False)
    is_paypal = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Payment Option'
        verbose_name_plural = 'Payment Options'

class Payment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='User')
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name='Bank')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Amount')
    paid_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Total Amount (with fee)',
        null=True,
        blank=True
    )
    receipt = models.FileField(upload_to='payments/receipts/', verbose_name='Receipt',  blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name='Status')
    notes = models.TextField(verbose_name='Notes', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_payments',
        verbose_name='Approved By'
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='Approved At')

    is_office_management = models.BooleanField(
        default=False,
        verbose_name='Office Management Approval',
        help_text='True if this payment was approved for office management'
    )
    
    def __str__(self):
        return f"{self.user} - ${self.amount} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_status = None
        is_office_approval = kwargs.pop('office_management', False)
        
        if not self.paid_amount:
            self.paid_amount = self.amount
            
        if not is_new:
            old_payment = Payment.objects.get(pk=self.pk)
            old_status = old_payment.status
            
            old_is_office = old_payment.is_office_management
        else:
            old_status = None
            old_is_office = False
        
        status_changing_to_approved = (
            (is_new and self.status == "approved") or
            (not is_new and old_status != "approved" and self.status == "approved")
        )
        
        status_changing_from_approved = (
            not is_new and old_status == "approved" and self.status in ["pending", "rejected"]
        )
        
        super().save(*args, **kwargs)
        
       
        if self.is_office_management:
            office_manager = User.get_office_manager()
            
            if office_manager:
                if status_changing_to_approved:
                    
                    office_manager.balance += self.amount
                    office_manager.save(update_fields=['balance'])
                    
                    if not self.approved_at:
                        self.approved_at = timezone.now()
                        super().save(update_fields=["approved_at"])
                        
                    print(f"✅ Office Payment Approved: ${self.amount} added to {office_manager.get_full_name()}'s balance")
                    
                elif status_changing_from_approved:
                   
                    office_manager.balance -= self.amount
                    office_manager.save(update_fields=['balance'])
                    
                    self.approved_at = None
                    self.approved_by = None
                    super().save(update_fields=["approved_at", "approved_by"])
                    
                    print(f"↩️ Office Payment Reversed: ${self.amount} deducted from {office_manager.get_full_name()}'s balance")
        
         
        elif not self.is_office_management:
            if status_changing_to_approved:
                self.user.balance += self.amount
                self.user.total_invest_balance += self.amount
                self.user.save()
                
                if not self.approved_at:
                    self.approved_at = timezone.now()
                    super().save(update_fields=["approved_at"])
                    
            elif status_changing_from_approved:
                self.user.balance -= self.amount
                self.user.total_invest_balance -= self.amount
                self.user.save()
                
                self.approved_at = None
                self.approved_by = None
                super().save(update_fields=["approved_at", "approved_by"])
# #nearest previous code
#     def save(self, *args, **kwargs):
#         is_new = self.pk is None
#         old_status = None
#         is_office_approval = kwargs.pop('office_management', False)
#         if not self.paid_amount:
#             self.paid_amount = self.amount
            
#         if not is_new:
#             old_payment = Payment.objects.get(pk=self.pk)
#             old_status = old_payment.status
#         else:
#             old_status = None
        
#         status_changing_to_approved = (
#             (is_new and self.status == "approved") or
#             (not is_new and old_status != "approved" and self.status == "approved")
#         )
        
#         status_changing_from_approved = (
#             not is_new and old_status == "approved" and self.status in ["pending", "rejected"]
#         )
        
#         super().save(*args, **kwargs)
        
#         if status_changing_to_approved and not is_office_approval:
#             self.user.balance += self.amount
#             self.user.total_invest_balance += self.amount
#             self.user.save()
            
#             if not self.approved_at:
#                 self.approved_at = timezone.now()
#                 super().save(update_fields=["approved_at"])
                
#         elif status_changing_from_approved and not is_office_approval:
#             self.user.balance -= self.amount
#             self.user.total_invest_balance -= self.amount
#             self.user.save()
            
#             self.approved_at = None
#             self.approved_by = None
#             super().save(update_fields=["approved_at", "approved_by"])    

    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-created_at']
        
class Expense(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
    )
    expense_date = models.DateField(null=True, blank=True)
    purpose = models.CharField(max_length=200, verbose_name="Purpose", null=True, blank=True) 
    description = models.TextField(verbose_name="Description")
    image = models.ImageField(upload_to='expenses/', verbose_name="Receipt/Invoice", null=True, blank=True)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Related Property")
    amount = models.DecimalField(max_digits=12, decimal_places=6, verbose_name="Amount")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_expenses")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_expenses")
    paid_by_user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="paid_expenses",
        verbose_name="Paid By User",
        help_text="Select the user who paid for this expense with their own money"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='unpaid')

    def __str__(self):
        return f"{self.purpose} - ${self.amount}"


    def should_add_to_expense_balance(self):
        """
        Determine if this expense should be added to ExpenseBalance.
        Returns True if:
        1. It's NOT a property expense (property is None), OR
        2. It IS a property expense AND paid_by_user is set
        
        Returns False if:
        - It's a property expense AND paid_by_user is NOT set
        """
        if self.property is None:
            # Non-property expense: always add to expense balance
            return True
        else:
            # Property expense: only add if a user paid for it
            return self.paid_by_user is not None

    def approve_expense(self, approved_by):
        """
        Approve expense and distribute cost:
        - For property expenses: Use adjust_contributions_for_service_cost_change()
        - For non-property expenses: Deduct from all active investors
        """
        if self.status != 'pending':
            return False
        
        if not (approved_by.is_superuser or (approved_by.is_finnancial and self.created_by != approved_by)):
            return False
        
        amount_value = self.amount or Decimal('0')
        
        with transaction.atomic():
            if self.property:
                # Property expense: Adjust service cost and contributions incrementally
                old_service_cost = self.property.service_cost or Decimal('0')
                new_service_cost = old_service_cost + amount_value
                
                print(f"\n{'='*80}")
                print(f"💰 PROPERTY EXPENSE APPROVAL: {self.purpose}")
                print(f"{'='*80}")
                print(f"Property: {self.property.title}")
                print(f"Expense Amount: ${amount_value:.2f}")
                print(f"Old Service Cost: ${old_service_cost:.2f}")
                print(f"New Service Cost: ${new_service_cost:.2f}")
                print(f"{'='*80}\n")
                
                # Update service cost
                self.property.service_cost = new_service_cost
                self.property.save(update_fields=['service_cost'])
                
                # Adjust contributions for the service cost increase
                adjustment_success = self.property.adjust_contributions_for_service_cost_change(amount_value)
                
                if not adjustment_success:
                    print("❌ Failed to adjust contributions!")
                    # Rollback will happen automatically due to transaction.atomic()
                    return False
                
                print("✅ Contributions adjusted successfully!")
                
            else:
                # Non-property expense: Deduct from all active investors proportionally
                users = list(User.objects.filter(is_active=True, investor=True))
                
                if not users:
                    print("❌ No active investors found")
                    return False
                
                total_balance = sum(user.balance for user in users)
                
                if total_balance <= Decimal('0'):
                    print("❌ Total balance is zero or negative")
                    return False
                
                print(f"\n{'='*80}")
                print(f"💰 NON-PROPERTY EXPENSE APPROVAL: {self.purpose}")
                print(f"{'='*80}")
                print(f"Expense Amount: ${amount_value:.2f}")
                print(f"Distributing among {len(users)} active investors")
                print(f"{'='*80}\n")
                
                distributed_total = Decimal('0')
                
                for i, user in enumerate(users):
                    if i == len(users) - 1:
                        user_share = amount_value - distributed_total
                    else:
                        ratio = (user.balance / total_balance) if total_balance > 0 else Decimal('1.0') / len(users)
                        user_share = (amount_value * ratio).quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)
                        distributed_total += user_share
                    
                    old_balance = user.balance
                    user.balance -= user_share
                    user.save(update_fields=['balance'])
                    
                    print(f"  👤 {user.get_full_name()}: ${user_share:.2f} (${old_balance:.2f} → ${user.balance:.2f})")
            
            # Mark as approved
            self.status = 'approved'
            self.approved_by = approved_by
            self.save(update_fields=['status', 'approved_by'])
            
            # Update expense balance if applicable
            if self.should_add_to_expense_balance():
                from .models import ExpenseBalance
                ExpenseBalance.update_total()
        
        print(f"\n✅ Expense approved successfully!")
        return True

    def reject_expense(self, rejected_by):
        """Reject the expense request"""

        if self.status != 'pending':
            return False

        # Prevent rejecting own expense unless user is admin
        if not (rejected_by.is_superuser or (rejected_by.is_finnancial and self.created_by != rejected_by)):
            return False

        with transaction.atomic():
            self.status = 'rejected'
            self.approved_by = rejected_by
            self.save(update_fields=['status', 'approved_by'])
            
            # No need to update ExpenseBalance for rejected expenses
            # They were never approved, so they were never added to the balance
        
        return True
    def update_status(self, new_status, updated_by):
        """
        Change status and update balances accordingly
        """
        if new_status == self.status:
            return False
        
        amount_value = self.amount or Decimal('0')
        
        # Track if ExpenseBalance needs update
        should_update_expense_balance = self.should_add_to_expense_balance()
        old_status = self.status
        
        with transaction.atomic():
            if self.property:
                old_service_cost = self.property.service_cost or Decimal('0')
                
                # Status change: approved → rejected/pending (reverse the expense)
                if self.status == "approved" and new_status != "approved":
                    print(f"\n↩️  REVERSING EXPENSE: {self.purpose}")
                    
                    # Get active contributors
                    contributions = PropertyContribution.objects.filter(
                        property=self.property,
                        contribution__gt=0
                    ).select_related('user')
                    
                    if not contributions.exists():
                        return False
                    
                    total_contribution = sum(c.contribution for c in contributions)
                    
                    # Refund proportionally and reduce contributions
                    for contrib in contributions:
                        ratio = contrib.contribution / total_contribution
                        user_share = (amount_value * ratio).quantize(
                            Decimal('0.000001'), rounding=ROUND_HALF_UP
                        )
                        
                        # Refund to user balance
                        contrib.user.balance += user_share
                        contrib.user.save(update_fields=['balance'])
                        
                        # Reduce contribution
                        contrib.contribution -= user_share
                        contrib.save(update_fields=['contribution'])
                        
                        print(f"  ✅ Refunded ${user_share:.2f} to {contrib.user.get_full_name()}")
                    
                    # Decrease service cost
                    self.property.service_cost = old_service_cost - amount_value
                    self.property.save(update_fields=['service_cost'])
                
                # Status change: rejected/pending → approved
                elif self.status != "approved" and new_status == "approved":
                    print(f"\n✅ APPLYING EXPENSE: {self.purpose}")
                    
                    # Increase service cost
                    self.property.service_cost = old_service_cost + amount_value
                    self.property.save(update_fields=['service_cost'])
                    
                    # Adjust contributions
                    adjustment_success = self.property.adjust_contributions_for_service_cost_change(amount_value)
                    
                    if not adjustment_success:
                        return False
            
            else:
                # Handle non-property expense status change
                users = list(User.objects.filter(is_active=True, investor=True))
                
                if not users:
                    return False
                
                total_balance = sum(user.balance for user in users)
                
                # Reverse previous approval
                if self.status == "approved":
                    for user in users:
                        ratio = (user.balance / total_balance) if total_balance > 0 else Decimal('1.0') / len(users)
                        user_share = (amount_value * ratio).quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)
                        user.balance += user_share
                        user.save(update_fields=['balance'])
                
                # Apply new approval
                if new_status == "approved":
                    total_balance = sum(user.balance for user in users)
                    
                    if total_balance <= 0:
                        return False
                    
                    distributed_total = Decimal('0')
                    
                    for i, user in enumerate(users):
                        if i == len(users) - 1:
                            user_share = amount_value - distributed_total
                        else:
                            ratio = (user.balance / total_balance) if total_balance > 0 else Decimal('1.0') / len(users)
                            user_share = (amount_value * ratio).quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)
                            distributed_total += user_share
                        
                        user.balance -= user_share
                        user.save(update_fields=['balance'])
            
            # Update expense status
            self.status = new_status
            self.approved_by = updated_by if new_status == "approved" else None
            self.save(update_fields=["status", "approved_by"])
            
            # Update ExpenseBalance based on status change
            if should_update_expense_balance:
                from .models import ExpenseBalance
                
                
                if old_status == "approved" and new_status != "approved":
                    expense_balance, _ = ExpenseBalance.objects.get_or_create(id=1)
                    expense_balance.total_expense -= amount_value
                    expense_balance.save(update_fields=['total_expense'])
                    print(f"↩️ ExpenseBalance decreased by ${amount_value}")
                
               
                elif old_status != "approved" and new_status == "approved":
                    expense_balance, _ = ExpenseBalance.objects.get_or_create(id=1)
                    expense_balance.total_expense += amount_value
                    expense_balance.save(update_fields=['total_expense'])
                    print(f"✅ ExpenseBalance increased by ${amount_value}")
            
            return True
# #nearest previous code
#     def update_status(self, new_status, updated_by):
#         """
#         Change status and update balances accordingly
#         """
#         if new_status == self.status:
#             return False
        
#         amount_value = self.amount or Decimal('0')
        
#         with transaction.atomic():
#             if self.property:
#                 old_service_cost = self.property.service_cost or Decimal('0')
                
#                 # Status change: approved → rejected (reverse the expense)
#                 if self.status == "approved" and new_status != "approved":
#                     print(f"\n↩️  REVERSING EXPENSE: {self.purpose}")
                    
#                     # Get active contributors
#                     contributions = PropertyContribution.objects.filter(
#                         property=self.property,
#                         contribution__gt=0
#                     ).select_related('user')
                    
#                     if not contributions.exists():
#                         return False
                    
#                     total_contribution = sum(c.contribution for c in contributions)
                    
#                     # Refund proportionally and reduce contributions
#                     for contrib in contributions:
#                         ratio = contrib.contribution / total_contribution
#                         user_share = (amount_value * ratio).quantize(
#                             Decimal('0.000001'), rounding=ROUND_HALF_UP
#                         )
                        
#                         # Refund to user balance
#                         contrib.user.balance += user_share
#                         contrib.user.save(update_fields=['balance'])
                        
#                         # Reduce contribution
#                         contrib.contribution -= user_share
#                         contrib.save(update_fields=['contribution'])
                        
#                         print(f"  ✅ Refunded ${user_share:.2f} to {contrib.user.get_full_name()}")
                    
#                     # Decrease service cost
#                     self.property.service_cost = old_service_cost - amount_value
#                     self.property.save(update_fields=['service_cost'])
                
#                 # Status change: rejected/pending → approved
#                 elif self.status != "approved" and new_status == "approved":
#                     print(f"\n✅ APPLYING EXPENSE: {self.purpose}")
                    
#                     # Increase service cost
#                     self.property.service_cost = old_service_cost + amount_value
#                     self.property.save(update_fields=['service_cost'])
                    
#                     # Adjust contributions
#                     adjustment_success = self.property.adjust_contributions_for_service_cost_change(amount_value)
                    
#                     if not adjustment_success:
#                         return False
            
#             else:
#                 # Handle non-property expense status change
#                 users = list(User.objects.filter(is_active=True, investor=True))
                
#                 if not users:
#                     return False
                
#                 total_balance = sum(user.balance for user in users)
                
#                 # Reverse previous approval
#                 if self.status == "approved":
#                     for user in users:
#                         ratio = (user.balance / total_balance) if total_balance > 0 else Decimal('1.0') / len(users)
#                         user_share = (amount_value * ratio).quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)
#                         user.balance += user_share
#                         user.save(update_fields=['balance'])
                
#                 # Apply new approval
#                 if new_status == "approved":
#                     total_balance = sum(user.balance for user in users)
                    
#                     if total_balance <= 0:
#                         return False
                    
#                     distributed_total = Decimal('0')
                    
#                     for i, user in enumerate(users):
#                         if i == len(users) - 1:
#                             user_share = amount_value - distributed_total
#                         else:
#                             ratio = (user.balance / total_balance) if total_balance > 0 else Decimal('1.0') / len(users)
#                             user_share = (amount_value * ratio).quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)
#                             distributed_total += user_share
                        
#                         user.balance -= user_share
#                         user.save(update_fields=['balance'])
            
#             # Update expense status
#             self.status = new_status
#             self.approved_by = updated_by if new_status == "approved" else None
#             self.save(update_fields=["status", "approved_by"])
            
#             # Update expense balance if applicable
#             if self.should_add_to_expense_balance():
#                 from .models import ExpenseBalance
#                 ExpenseBalance.update_total()

    
class Story(models.Model):
    message = models.TextField()
    related_property = models.ForeignKey(Property, on_delete=models.CASCADE, null=True, blank=True,related_name='stories')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.created_at} – {self.message[:60]}"
    

class Announcement(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE)

    def __str__(self):
        return self.title
    
class Help(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to='help_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
class ExpenseBalance(models.Model):
    total_expense = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    @classmethod
    def update_total(cls):
        
        total_expenses = Expense.objects.filter(status="approved").aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")

        
        total_paid = ExpensePayment.objects.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")

      
        balance_value = total_expenses - total_paid

        summary, created = cls.objects.get_or_create(id=1)
        summary.total_expense = balance_value
        summary.save()

        return summary.total_expense
    

class ExpensePayment(models.Model):
    RECEIVE_CHOICES = (
        ('cash', 'Cash'),
        ('account', 'Account Transfer'),
    )

    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="payments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="expense_payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    receipt = models.ImageField(upload_to='expense_payments/', null=True, blank=True)
    receive_type = models.CharField(max_length=10, choices=RECEIVE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def process_payment(self):
        """Handle balance update logic for both cash and account transfer."""
        from .models import ExpenseBalance  

        with transaction.atomic():
           
            balance_obj, created = ExpenseBalance.objects.get_or_create(id=1)

            
            balance_obj.total_expense -= self.amount
            balance_obj.total_expense = balance_obj.total_expense.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            balance_obj.save(update_fields=["total_expense"])

            if self.receive_type == "account":
                self.user.balance += self.amount
                self.user.balance = self.user.balance.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                self.user.save(update_fields=["balance"])

            self.expense.payment_status = "paid"
            self.expense.save(update_fields=["payment_status"])
            self.save()

        return True

    def __str__(self):
        return f"Payment for {self.expense.purpose} to {self.user} - {self.amount}"
    
    
class Beneficiary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='old_beneficiaries')
    name = models.CharField(max_length=150, verbose_name='Beneficiary Name')
    percentage = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Percentage')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.percentage}%)"

class PropertyProfitDistribution(models.Model):
    """
    Property-wise Profit Distribution Model

    This model tracks different levels of buyers and their share for each property.

    Features:
    - Select a Property
    - First Level Buyers (those who invested first) - default share: 1
    - Second Level Buyers (those who joined later) - default share: 1
    - First Level share can be increased (example: 1.8)
    - Profit calculation uses: profit_weight × buyer_share
    """

    BUYER_LEVEL_CHOICES = [
        ('first', 'First Level Buyer'),
        ('second', 'Second Level Buyer'),
    ]
    property = models.OneToOneField(
        'Property',
        on_delete=models.CASCADE,
        related_name='profit_distribution',
        verbose_name='Property'
    )
    first_level_buyers = models.ManyToManyField(
        'User',
        related_name='first_level_properties',
        blank=True,
        verbose_name='First Level Buyers'
    )

    first_level_buyer_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Number of First Level Buyers'
    )

    first_level_share = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='First Level Share',
        help_text='Default: 1.00 (Superuser can modify, e.g., 1.8)'
    )
    second_level_buyers = models.ManyToManyField(
        'User',
        related_name='second_level_properties',
        blank=True,
        verbose_name='Second Level Buyers'
    )

    second_level_buyer_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Number of Second Level Buyers'
    )

    second_level_share = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Second Level Share',
        help_text='Default: 1.00'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At'
    )

    class Meta:
        verbose_name = 'Property Profit Distribution'
        verbose_name_plural = 'Property Profit Distribution'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.property.title} - First: {self.first_level_buyer_count}, Second: {self.second_level_buyer_count}"

    def update_buyer_counts(self):
        """Update buyer counts"""
        self.first_level_buyer_count = self.first_level_buyers.count()
        self.second_level_buyer_count = self.second_level_buyers.count()
        self.save(update_fields=['first_level_buyer_count', 'second_level_buyer_count'])

    def get_user_buyer_level(self, user):
        """Check which buyer level the user belongs to"""
        if self.first_level_buyers.filter(id=user.id).exists():
            return 'first'
        elif self.second_level_buyers.filter(id=user.id).exists():
            return 'second'
        return None

    def get_user_share_multiplier(self, user):
        """
        Get the user’s share multiplier

        Returns:
            Decimal: First level = first_level_share, Second level = second_level_share
        """
        buyer_level = self.get_user_buyer_level(user)

        if buyer_level == 'first':
            return self.first_level_share
        elif buyer_level == 'second':
            return self.second_level_share

        return Decimal('1.00')  # Default

    def calculate_adjusted_profit_weight(self, user, base_profit_weight):
        """
        Calculate adjusted profit weight

        Formula: base_profit_weight × buyer_share

        Args:
            user: User object
            base_profit_weight: PropertyContribution.profit_weight

        Returns:
            Decimal: Adjusted profit weight
        """
        share_multiplier = self.get_user_share_multiplier(user)
        adjusted_weight = (base_profit_weight * share_multiplier).quantize(
            Decimal('0.000001'),
            rounding=ROUND_HALF_UP
        )
        return adjusted_weight

    def add_first_level_buyer(self, user):
        """Add a First Level Buyer"""
        if not self.first_level_buyers.filter(id=user.id).exists():
            self.first_level_buyers.add(user)
            self.update_buyer_counts()
            return True
        return False

    def add_second_level_buyer(self, user):
        """Add a Second Level Buyer"""
        if not self.second_level_buyers.filter(id=user.id).exists():
            self.second_level_buyers.add(user)
            self.update_buyer_counts()
            return True
        return False

    def move_to_second_level(self, user):
        """Move buyer from First Level to Second Level"""
        if self.first_level_buyers.filter(id=user.id).exists():
            self.first_level_buyers.remove(user)
            self.second_level_buyers.add(user)
            self.update_buyer_counts()
            return True
        return False

    def get_all_buyers_with_levels(self):
        """
        Get all buyers with their levels

        Returns:
            list: [{'user': User, 'level': 'first'/'second', 'share': Decimal}]
        """
        buyers = []

        # First Level Buyers
        for user in self.first_level_buyers.all():
            buyers.append({
                'user': user,
                'level': 'first',
                'share': self.first_level_share
            })

        
        for user in self.second_level_buyers.all():
            buyers.append({
                'user': user,
                'level': 'second',
                'share': self.second_level_share
            })

        return buyers

    def update_all_profit_weights(self):
        """
        Update all PropertyContribution profit_weight based on buyer level.

        When executed:
        1. Checks buyer level for each contributor
        2. Calculates new weight = base weight × buyer share
        3. Updates PropertyContribution model

        Returns:
            dict: Update summary details
        """

        from django.db import transaction
        from accounts.models import PropertyContribution

        contributions = PropertyContribution.objects.filter(property=self.property)

        if not contributions.exists():
            return {
                'success': False,
                'message': 'No contributions found',
                'updated_count': 0
            }

        updated_count = 0
        update_details = []

        print("\n" + "="*80)
        print("🔄 UPDATING PROFIT WEIGHTS WITH BUYER LEVELS")
        print(f"Property: {self.property.title}")
        print("="*80)

        with transaction.atomic():
            for contrib in contributions:
                user = contrib.user

                base_profit_weight = contrib.profit_weight
                buyer_level = self.get_user_buyer_level(user)
                share_multiplier = self.get_user_share_multiplier(user)

                adjusted_profit_weight = self.calculate_adjusted_profit_weight(
                    user,
                    base_profit_weight
                )

                contrib.profit_weight = adjusted_profit_weight
                contrib.save(update_fields=['profit_weight'])

                updated_count += 1

                detail = {
                    'user': user.get_full_name(),
                    'buyer_level': buyer_level or 'Not Found',
                    'share_multiplier': float(share_multiplier),
                    'base_weight': float(base_profit_weight),
                    'adjusted_weight': float(adjusted_profit_weight)
                }
                update_details.append(detail)

                print(f"\n👤 {user.get_full_name()}")
                print(f"   Buyer Level: {buyer_level or 'Not Found'}")
                print(f"   Share Multiplier: {float(share_multiplier)}")
                print(f"   Base Profit Weight: {float(base_profit_weight):.6f}")
                print(f"   Adjusted Profit Weight: {float(adjusted_profit_weight):.6f}")

        print("\n" + "="*80)
        print(f"✅ {updated_count} contributions updated")
        print("="*80 + "\n")

        return {
            'success': True,
            'message': f'{updated_count} contributions updated successfully',
            'updated_count': updated_count,
            'details': update_details
        }


class BuyerLevelHistory(models.Model):
    """
    Tracks buyer level change history (optional)
    """

    profit_distribution = models.ForeignKey(
        PropertyProfitDistribution,
        on_delete=models.CASCADE,
        related_name='level_history',
        verbose_name='Profit Distribution'
    )

    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        verbose_name='User'
    )

    previous_level = models.CharField(
        max_length=10,
        choices=PropertyProfitDistribution.BUYER_LEVEL_CHOICES,
        null=True,
        blank=True,
        verbose_name='Previous Level'
    )

    current_level = models.CharField(
        max_length=10,
        choices=PropertyProfitDistribution.BUYER_LEVEL_CHOICES,
        verbose_name='Current Level'
    )

    changed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Changed At'
    )

    changed_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='level_changes_made',
        verbose_name='Changed By'
    )

    class Meta:
        verbose_name = 'Buyer Level History'
        verbose_name_plural = 'Buyer Level History'
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.previous_level} → {self.current_level}"
    
    
class Group(models.Model):
    """
    Group model for categorizing users with deduction percentages
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        verbose_name='Group Name'
    )
    percentage = models.DecimalField(
        max_digits=5,
        null=True,
        blank=True,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal('0.00')),
            MaxValueValidator(Decimal('100.00'))
        ],
        verbose_name='Deduction Percentage',
        help_text='Percentage to deduct from profit (0-100)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Group'
        verbose_name_plural = 'Groups'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.percentage}%)"



class DeductionHistory(models.Model):
    """
    Tracks deductions from property profit distributions
    """
    property = models.ForeignKey(
        'Property',
        on_delete=models.CASCADE,
        related_name='deduction_history',
        null=True,
        blank=True,
        verbose_name='Property'
    )
    user = models.ForeignKey(
        'User',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='deduction_history',
        verbose_name='User'
    )
    property_contribution = models.ForeignKey(
        'PropertyContribution',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Property Contribution'
    )
    
    profit_share = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        default=Decimal('0.00'),
        verbose_name='Profit Share'
    )
    
    deduction_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Deduction Percentage'
    )
    
    deduction_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Deduction Amount'
    )
    
    sequence_number = models.PositiveIntegerField(
        default=1,
        verbose_name='Sequence Number'
    )
    
    office_manager = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_deductions',
        verbose_name='Office Manager'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Deduction History'
        verbose_name_plural = 'Deduction Histories'
        ordering = ['-created_at']

    def __str__(self):
        return f"Deduction: {self.user} → {self.property} (Seq #{self.sequence_number})"