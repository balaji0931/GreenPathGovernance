import re
from django import forms
from django.contrib.auth.models import User
from django.db import transaction
from .models import Household
from governance.models import Ward
from accounts.models import UserProfile, RoleChoices

def generate_next_collector_username(village):
    """
    Auto-generates sequential collector usernames for a village:
    V001-C1, V001-C2, V002-C1, V002-C2...
    """
    v_code = village.code.upper()
    prefix = f"{v_code}-C"
    existing = User.objects.filter(username__istartswith=prefix).values_list('username', flat=True)
    numbers = []
    for u in existing:
        m = re.match(rf'^{re.escape(prefix)}(\d+)$', u, re.IGNORECASE)
        if m:
            numbers.append(int(m.group(1)))
    next_num = max(numbers, default=0) + 1
    candidate = f"{prefix}{next_num}"
    while User.objects.filter(username__iexact=candidate).exists():
        next_num += 1
        candidate = f"{prefix}{next_num}"
    return candidate


class HouseholdRegistrationForm(forms.ModelForm):
    """
    Form for Village Manager to register a household.
    Household UID is auto-assigned (e.g. V001-H1).
    Resident portal login account matches the Household UID.
    """
    create_resident_account = forms.BooleanField(
        required=False,
        initial=True,
        label="Provision Resident Login Account",
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-emerald-600 border-slate-300 rounded focus:ring-emerald-500',
            'id': 'create_account_toggle',
        })
    )
    resident_username = forms.CharField(
        required=False,
        label="Resident Username",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm bg-slate-50',
            'placeholder': 'Auto-assigned to match Household ID (e.g. V001-H1)',
        }),
        help_text="Resident Username matches the Household ID automatically."
    )
    resident_password = forms.CharField(
        required=False,
        label="Initial Resident Password",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm',
            'placeholder': '•••••••• (Leave blank for default: Resident123@)',
        }),
        help_text="Leave blank to automatically assign default password (Resident123@)."
    )

    class Meta:
        model = Household
        fields = ['head_name', 'house_number', 'ward', 'street_address', 'phone_number']
        widgets = {
            'head_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm',
                'placeholder': 'e.g. Balaji Patil',
            }),
            'house_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm',
                'placeholder': 'e.g. 42-B / Plot 7',
            }),
            'street_address': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm',
                'placeholder': 'Near Gram Panchayat Hall',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm',
                'placeholder': '+91 9876543210',
            }),
            'ward': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.village = kwargs.pop('village', None)
        super().__init__(*args, **kwargs)
        if self.village:
            self.instance.village = self.village
            self.fields['ward'].queryset = Ward.objects.filter(village=self.village, is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        ward = cleaned_data.get('ward')
        if self.village and ward and ward.village_id != self.village.id:
            self.add_error('ward', "Selected ward does not belong to your assigned Gram Panchayat.")

        create_acc = cleaned_data.get('create_resident_account')
        username = cleaned_data.get('resident_username', '').strip()
        password = cleaned_data.get('resident_password', '')

        if create_acc:
            if username and User.objects.filter(username__iexact=username).exists():
                self.add_error('resident_username', f"Username '{username}' is already taken.")
            if password and len(password) < 6:
                self.add_error('resident_password', "Password must be at least 6 characters.")

        return cleaned_data

    def save(self, commit=True):
        household = super().save(commit=False)
        if self.village:
            household.village = self.village

        # Ensure UID is generated before creating linked resident user
        if not household.uid:
            household.uid = household.generate_unique_uid()

        with transaction.atomic():
            cd = self.cleaned_data
            if cd.get('create_resident_account'):
                # Resident username matches household.uid (or fallback to explicitly provided)
                target_username = cd.get('resident_username', '').strip() or household.uid
                candidate = target_username
                c = 1
                while User.objects.filter(username__iexact=candidate).exists():
                    candidate = f"{target_username}_{c}"
                    c += 1

                password = cd.get('resident_password') or 'Resident123@'

                user = User.objects.create_user(
                    username=candidate,
                    password=password,
                    first_name=cd.get('head_name', '')
                )
                profile, _ = UserProfile.objects.get_or_create(user=user)
                profile.role = RoleChoices.HOUSEHOLD
                profile.village = self.village
                profile.phone_number = cd.get('phone_number', '')
                profile.save()
                household.resident_user = user
                household._resident_password = password

            if commit:
                household.save()

        return household


class HouseholdEditForm(forms.ModelForm):
    """
    Form for updating household details and active/inactive status (FR-19).
    """
    class Meta:
        model = Household
        fields = ['head_name', 'house_number', 'ward', 'street_address', 'phone_number', 'is_active']
        widgets = {
            'head_name': forms.TextInput(attrs={'class': 'w-full px-4 py-2 rounded-xl border border-slate-300 text-sm'}),
            'house_number': forms.TextInput(attrs={'class': 'w-full px-4 py-2 rounded-xl border border-slate-300 text-sm'}),
            'street_address': forms.TextInput(attrs={'class': 'w-full px-4 py-2 rounded-xl border border-slate-300 text-sm'}),
            'phone_number': forms.TextInput(attrs={'class': 'w-full px-4 py-2 rounded-xl border border-slate-300 text-sm'}),
            'ward': forms.Select(attrs={'class': 'w-full px-4 py-2 rounded-xl border border-slate-300 text-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-emerald-600 rounded'}),
        }

    def __init__(self, *args, **kwargs):
        self.village = kwargs.pop('village', None)
        super().__init__(*args, **kwargs)
        if self.village:
            self.fields['ward'].queryset = Ward.objects.filter(village=self.village)


class WasteCollectorCreateForm(forms.Form):
    """
    Form for Village Manager to create a Waste Collector account.
    Collector ID is auto-assigned (e.g. V001-C1).
    """
    username = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm bg-slate-50',
            'placeholder': 'Auto-assigned (e.g. V001-C1)',
        }),
        help_text="Leave blank to automatically assign Collector ID (e.g. V001-C1)."
    )
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm',
            'placeholder': 'Kishore',
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm',
            'placeholder': 'Shinde',
        })
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm',
            'placeholder': '+91 9876543210',
        })
    )
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm',
            'placeholder': '•••••••• (Leave blank for default: Collector123@)',
        }),
        help_text="Leave blank to automatically set default password (Collector123@)."
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if username and User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(f"Username '{username}' is already taken.")
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password and len(password) < 6:
            raise forms.ValidationError("Password must be at least 6 characters.")
        return password

    def save(self, village):
        cd = self.cleaned_data
        username = cd.get('username')
        if not username:
            username = generate_next_collector_username(village)
        password = cd.get('password') or 'Collector123@'

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                first_name=cd.get('first_name', ''),
                last_name=cd.get('last_name', ''),
                password=password
            )
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = RoleChoices.WASTE_COLLECTOR
            profile.village = village
            profile.phone_number = cd.get('phone_number', '')
            profile.save()
            user.profile = profile
            user._raw_password = password
        return user
