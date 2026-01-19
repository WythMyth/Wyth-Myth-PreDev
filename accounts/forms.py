from captcha.fields import CaptchaField, CaptchaTextInput
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django import forms
from .models import Announcement, ExpensePayment, User, Property, Payment, Expense, Property, PropertyImage, Help, Beneficiary
from django.contrib.auth.forms import AuthenticationForm
from django.forms import DateInput
from calendar import monthrange
from datetime import datetime

from django import forms
from .models import ExpensePayment, User
class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(label='Password', widget=forms.PasswordInput)
    is_agree = forms.BooleanField(label='I agree to the terms', required=True)
    captcha = CaptchaField(
        label='Enter the digits shown',
        widget=CaptchaTextInput(attrs={
            'class': 'mt-1 w-36 px-3 py-2 border border-gray-300 rounded-md shadow-sm '
                     'focus:outline-none focus:ring-2 focus:ring-orange-200 focus:border-orange-400 '
                     'transition duration-150 ease-in-out',
            'placeholder': 'Enter Code'
        })
    )
    birth_year = forms.ChoiceField(
        choices=[("", "Select Birth Year")] + User.BIRTH_YEAR_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    birth_month = forms.ChoiceField(
        choices=[("", "Select Birth Month")] + User.BIRTH_MONTH_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    birth_date = forms.ChoiceField(
        choices=[("", "Select Birth Date")], 
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = [
            'first_name', 'middle_name', 'last_name', 'phone_number', 'email',
            'birth_year', 'birth_month', 'birth_date', 'personal_image', 'photo_id',
            'home_address_line_1', 'home_address_line_2', 'city', 'state', 'zip_code',
            'emergency_contact','emergency_contact_number', 'how_did_you_know', 'sign_by_name',
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize birth_date choices
        self.fields['birth_date'].choices = [("", "Select Birth Date")]
        
        # Dynamically update the days in birth_date based on year and month
        if 'birth_year' in self.data and 'birth_month' in self.data:
            try:
                year = int(self.data.get('birth_year'))
                month = int(self.data.get('birth_month'))
                days = monthrange(year, month)[1]
                self.fields['birth_date'].choices += [
                    (str(day), str(day)) for day in range(1, days + 1)
                ]
            except (ValueError, TypeError):
                pass
    
    def clean(self):
        cleaned_data = super().clean()
        birth_year = cleaned_data.get("birth_year")
        birth_month = cleaned_data.get("birth_month")
        birth_date = cleaned_data.get("birth_date")
        
        # Validate required fields
        if not birth_year:
            self.add_error('birth_year', "This field is required.")
        if not birth_month:
            self.add_error('birth_month', "This field is required.")
        if not birth_date:
            self.add_error('birth_date', "This field is required.")
        else:
            # Validate date combination
            try:
                year = int(birth_year)
                month = int(birth_month)
                day = int(birth_date)
                
                # Check if the day is valid for the selected month and year
                if day > monthrange(year, month)[1]:
                    self.add_error('birth_date', "Invalid date for the selected month and year.")
                
                # Try to create a valid date
                datetime(year, month, day).date()
                
            except (ValueError, TypeError):
                self.add_error('birth_date', "Invalid date.")
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.is_agree = self.cleaned_data["is_agree"]
        
        # Convert string values to integers for the model
        if self.cleaned_data.get("birth_year"):
            user.birth_year = int(self.cleaned_data["birth_year"])
        if self.cleaned_data.get("birth_month"):
            user.birth_month = int(self.cleaned_data["birth_month"])
        if self.cleaned_data.get("birth_date"):
            user.birth_date = int(self.cleaned_data["birth_date"])
        
        if commit:
            user.save()
        return user

class UserUpdateForm(forms.ModelForm):
    birth_year = forms.ChoiceField(
        choices=[("", "Select Birth Year")] + User.BIRTH_YEAR_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    birth_month = forms.ChoiceField(
        choices=[("", "Select Birth Month")] + User.BIRTH_MONTH_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    birth_date = forms.ChoiceField(
        choices=[("", "Select Birth Date")],
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    beneficiary_names = forms.CharField(required=False, widget=forms.HiddenInput())
    beneficiary_percentages = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = User
        fields = [
            'first_name', 'middle_name', 'last_name', 'phone_number',
            'birth_year', 'birth_month', 'birth_date',
            'home_address_line_1', 'home_address_line_2', 'city', 'state', 'zip_code',
            'personal_image', 'photo_id', 'emergency_contact'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Handle dynamic birth_date
        self.fields['birth_date'].choices = [("", "Select Birth Date")]
        if self.data.get('birth_year') and self.data.get('birth_month'):
            try:
                year = int(self.data.get('birth_year'))
                month = int(self.data.get('birth_month'))
                day_count = monthrange(year, month)[1]
                self.fields['birth_date'].choices += [(str(d), str(d)) for d in range(1, day_count + 1)]
            except:
                pass
        elif self.instance.birth_year and self.instance.birth_month:
            day_count = monthrange(self.instance.birth_year, self.instance.birth_month)[1]
            self.fields['birth_date'].choices += [(str(d), str(d)) for d in range(1, day_count + 1)]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['birth_date'].choices = [("", "Select Birth Date")]
        if self.data.get('birth_year') and self.data.get('birth_month'):
            try:
                year = int(self.data.get('birth_year'))
                month = int(self.data.get('birth_month'))
                day_count = monthrange(year, month)[1]
                self.fields['birth_date'].choices += [(str(d), str(d)) for d in range(1, day_count + 1)]
            except:
                pass
        elif self.instance.birth_year and self.instance.birth_month:
            day_count = monthrange(self.instance.birth_year, self.instance.birth_month)[1]
            self.fields['birth_date'].choices += [(str(d), str(d)) for d in range(1, day_count + 1)]
    
    def clean(self):
        cleaned_data = super().clean()
        year = cleaned_data.get("birth_year")
        month = cleaned_data.get("birth_month")
        day = cleaned_data.get("birth_date")
        
        if not (year and month and day):
            self.add_error('birth_date', "Please select a valid date.")
        else:
            try:
                datetime(int(year), int(month), int(day))
            except:
                self.add_error('birth_date', "Invalid date combination.")
        
       
        names = self.data.getlist('beneficiary_name[]')
        percentages = self.data.getlist('beneficiary_percentage[]')
        
        beneficiaries = []
        if names and percentages:
            for name, percentage in zip(names, percentages):
               
                if name.strip() and percentage.strip():
                    try:
                        pct = float(percentage)
                        if pct < 0:
                            self.add_error(None, f"Percentage cannot be negative: {percentage}")
                        else:
                            beneficiaries.append({
                                'name': name.strip(),
                                'percentage': pct
                            })
                    except ValueError:
                        self.add_error(None, f"Invalid percentage value: {percentage}")
        
        
        cleaned_data['beneficiaries'] = beneficiaries
        
        return cleaned_data

class UserLoginForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.EmailInput(attrs={'autocomplete': 'email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}))

class PropertyForm(forms.ModelForm):
    contributors = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True, investor=True),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'w-full border border-black rounded-md px-3 py-2',
            'size': '8',  
        }),
        label="Select Contributors",
        
    )
    
    class Meta:
        model = Property
        exclude = ['listed_by', 'listed_date', 'is_contribution_locked']
        widgets = {
            'buying_date': DateInput(attrs={'type': 'date'}),
            'selling_date': DateInput(attrs={'type': 'date'}),
            'auction_date': DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'acquisition_cost': forms.NumberInput(attrs={
                'readonly': 'readonly',
                'class': 'bg-gray-100'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set labels
        self.fields['title'].label = "Title"
        self.fields['description'].label = "Description"
        self.fields['auction_price'].label = "Auction Price"
        self.fields['service_cost'].label = "Service Cost"
        self.fields['profit'].label = "Profit"
        self.fields['asking_price'].label = "Asking Price"
        self.fields['selling_price'].label = "Selling Price"
        self.fields['buying_date'].label = "Buying Date"
        self.fields['buying_price'].label = "Buying Price"
        self.fields['acquisition_cost'].label = "Acquisition Cost"
        self.fields['selling_date'].label = "Selling Date"
        self.fields['address'].label = "Address"
        self.fields['url'].label = "URL"
        self.fields['city'].label = "City"
        self.fields['state'].label = "State"
        self.fields['zip_code'].label = "Zip Code"
        self.fields['bedrooms'].label = "Bedrooms"
        self.fields['bathrooms'].label = "Bathrooms"
        self.fields['dining_rooms'].label = "Dining Rooms"
        self.fields['square_feet'].label = "Square Feet"
        self.fields['status'].label = "Status"

        self.fields['buying_date'].required = False
        self.fields['selling_date'].required = False
        self.fields['profit'].required = False
        self.fields['url'].required = False
        self.fields['auction_date'].required = False
        self.fields['booking_fee'].required = False
        self.fields['estimated_price'].required = False
        self.fields['auction_price'].required = False
        self.fields['service_cost'].required = False
        self.fields['buying_price'].required = False
        self.fields['acquisition_cost'].required = False 
        self.fields['dining_rooms'].required = False
        self.fields['contributors'].label_from_instance = lambda obj: f"{obj.get_full_name()} (Balance: ${obj.balance:,.2f})"

    def clean(self):
        cleaned_data = super().clean()
        buying_price = cleaned_data.get('buying_price') or 0
        service_cost = cleaned_data.get('service_cost') or 0
        
        # Calculate acquisition cost
        if buying_price or service_cost:
            cleaned_data['acquisition_cost'] = buying_price + service_cost
        else:
            cleaned_data['acquisition_cost'] = None
            
        return cleaned_data
class PropertyImageForm(forms.ModelForm):
    class Meta:
        model = PropertyImage
        fields = ['image', 'is_primary']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['is_primary'].label = "Primary Image"

PropertyImageFormSet = forms.inlineformset_factory(
    Property, 
    PropertyImage,
    form=PropertyImageForm,
    extra=50,
    max_num=50,
    can_delete=True
)

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'receipt', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'receipt': forms.FileInput(attrs={'class': 'form-control'}),
        }

class PaymentApprovalForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['notes']
        widgets = {
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        
class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'class': 'form-input'})
    )

    def get_users(self, email):
        return User.objects.filter(email=email, is_active=True)

class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label="New password",
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    new_password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )



# class ExpenseForm(forms.ModelForm):
#     class Meta:
#         model = Expense
#         fields = ['expense_date', 'purpose', 'description', 'image', 'property', 'amount']
#         widgets = {
#             'description': forms.Textarea(attrs={'rows': 4}),
#             'expense_date': DateInput(attrs={'type': 'date'}),
#         }
class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['expense_date', 'purpose', 'description', 'image', 'property', 'amount', 'paid_by_user']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'expense_date': DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make paid_by_user optional
        self.fields['paid_by_user'].required = False
        self.fields['paid_by_user'].queryset = User.objects.filter(is_active=True).order_by("short_name")
        
class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'description']

        widgets = {
            'title': forms.TextInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4})
        }
        
        
class HelpForm(forms.ModelForm):
    class Meta:
        model = Help
        fields = ['title', 'description', 'image']

class ExpensePaymentForm(forms.ModelForm):
    class Meta:
        model = ExpensePayment
        fields = [ "user", "amount", "receipt", "receive_type"]
        widgets = {
            "amount": forms.NumberInput(attrs={"readonly": "readonly"}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make paid_by_user optional
        self.fields['user'].required = False
        self.fields['user'].queryset = User.objects.filter(is_active=True).order_by("short_name")
        


class BeneficiaryForm(forms.ModelForm):
    class Meta:
        model = Beneficiary
        fields = ['name', 'percentage']


class OfficeExpensePaymentForm(forms.ModelForm):

    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True, investor=True).order_by('first_name'),
        required=True,
        label='User',
        widget=forms.Select(attrs={
            'class': 'w-full border rounded-md px-3 py-2 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-400'
        })
    )
    
    class Meta:
        model = ExpensePayment
        fields = ['user', 'receive_type', 'receipt']
        widgets = {
            'receive_type': forms.Select(attrs={
                'class': 'w-full border rounded-md px-3 py-2 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-400'
            }),
            'receipt': forms.FileInput(attrs={
                'class': 'block w-full text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200 cursor-pointer'
            })
        }
        labels = {
            'user': 'User',
            'receive_type': 'Receive Type',
            'receipt': 'Receipt'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['receipt'].required = False
        self.fields['user'].required = True
        self.fields['receive_type'].required = True