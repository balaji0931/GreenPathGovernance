import re
from django import forms
from django.contrib.auth.models import User
from .models import Village, Ward
from accounts.models import UserProfile, RoleChoices

class VillageForm(forms.ModelForm):
    """
    Form for Super Admin to register or edit a Village / Gram Panchayat (FR-09).
    """
    class Meta:
        model = Village
        fields = ['code', 'name', 'district', 'state', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm font-mono uppercase',
                'placeholder': 'VIL-PANCHAYAT-01',
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm',
                'placeholder': 'Shivaji Gram Panchayat',
            }),
            'district': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm',
                'placeholder': 'Pune',
            }),
            'state': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm',
                'placeholder': 'Maharashtra',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-emerald-600 border-slate-300 rounded focus:ring-emerald-500',
            }),
        }

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip().upper()
        if not re.match(r'^[A-Z0-9\-_]+$', code):
            raise forms.ValidationError("Village code must be alphanumeric and can contain hyphens or underscores.")
        
        # Check uniqueness on creation or modification
        qs = Village.objects.filter(code=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"Village code '{code}' is already registered.")
        return code


class WardForm(forms.ModelForm):
    """
    Form to configure Wards under a selected Village (FR-10).
    """
    class Meta:
        model = Ward
        fields = ['ward_number', 'ward_name', 'is_active']
        widgets = {
            'ward_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm font-semibold',
                'placeholder': 'Ward 01',
            }),
            'ward_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm',
                'placeholder': 'e.g. North Bazaar / High School Road',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-emerald-600 border-slate-300 rounded focus:ring-emerald-500',
            }),
        }


class VillageManagerCreateForm(forms.Form):
    """
    Form for Super Admin to create a Village Manager account and assign to a Village (FR-11).
    """
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm',
            'placeholder': 'mgr_shivaji',
        })
    )
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm',
            'placeholder': 'Ramesh',
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm',
            'placeholder': 'Patil',
        })
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm',
            'placeholder': 'manager@panchayat.in',
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
        help_text="Provide an initial password for the manager."
    )
    village = forms.ModelChoiceField(
        queryset=Village.objects.filter(is_active=True),
        empty_label="Select Gram Panchayat / Village",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm',
        })
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(f"Username '{username}' is already taken.")
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 6:
            raise forms.ValidationError("Password must be at least 6 characters long.")
        return password

    def save(self):
        cd = self.cleaned_data
        user = User.objects.create_user(
            username=cd['username'],
            email=cd.get('email', ''),
            first_name=cd.get('first_name', ''),
            last_name=cd.get('last_name', ''),
            password=cd['password']
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = RoleChoices.VILLAGE_MANAGER
        profile.village = cd['village']
        profile.phone_number = cd.get('phone_number', '')
        profile.save()
        user.profile = profile
        return user
