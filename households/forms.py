import re
from django import forms
from django.contrib.auth.models import User
from django.db import transaction
from .models import Household
from governance.models import Ward
from accounts.models import UserProfile, RoleChoices

class HouseholdRegistrationForm(forms.ModelForm):
    """
    Form for Village Manager to register a household and optionally
    provision a linked citizen login account (FR-16, FR-17, FR-18).
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
            'class': 'w-full px-4 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm',
            'placeholder': 'e.g. resident_w01_12',
        })
    )
    resident_password = forms.CharField(
        required=False,
        label="Initial Resident Password",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm',
            'placeholder': '••••••••',
        })
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
            # Strictly restrict ward choices to the manager's assigned village (FR-21)
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
            if not username:
                self.add_error('resident_username', "Username is required when creating a resident login account.")
            elif User.objects.filter(username__iexact=username).exists():
                self.add_error('resident_username', f"Username '{username}' is already taken.")

            if not password or len(password) < 6:
                self.add_error('resident_password', "Password must be at least 6 characters.")

        return cleaned_data

    def save(self, commit=True):
        household = super().save(commit=False)
        if self.village:
            household.village = self.village

        with transaction.atomic():
            cd = self.cleaned_data
            if cd.get('create_resident_account'):
                user = User.objects.create_user(
                    username=cd['resident_username'].strip(),
                    password=cd['resident_password'],
                    first_name=cd.get('head_name', '')
                )
                profile, _ = UserProfile.objects.get_or_create(user=user)
                profile.role = RoleChoices.HOUSEHOLD
                profile.village = self.village
                profile.phone_number = cd.get('phone_number', '')
                profile.save()
                household.resident_user = user

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
    Form for Village Manager to create a Waste Collector account (FR-14).
    """
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm',
            'placeholder': 'collector_pune_01',
        })
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
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm',
            'placeholder': '••••••••',
        }),
        help_text="Password for collector mobile login."
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(f"Username '{username}' is already taken.")
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 6:
            raise forms.ValidationError("Password must be at least 6 characters.")
        return password

    def save(self, village):
        cd = self.cleaned_data
        with transaction.atomic():
            user = User.objects.create_user(
                username=cd['username'],
                first_name=cd.get('first_name', ''),
                last_name=cd.get('last_name', ''),
                password=cd['password']
            )
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = RoleChoices.WASTE_COLLECTOR
            profile.village = village
            profile.phone_number = cd.get('phone_number', '')
            profile.save()
            user.profile = profile
        return user
