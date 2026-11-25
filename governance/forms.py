import re
from django import forms
from django.contrib.auth.models import User
from .models import Village, Ward, generate_next_village_code
from accounts.models import UserProfile, RoleChoices

def generate_next_manager_username(village):
    """
    Auto-generates sequential manager usernames for a village:
    V001-M1, V001-M2, V002-M1, V002-M2...
    """
    v_code = village.code.upper()
    prefix = f"{v_code}-M"
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


class VillageForm(forms.ModelForm):
    """
    Form for Super Admin to register or edit a Village / Gram Panchayat.
    Village ID is auto-assigned (e.g. V001, V002) if left blank.
    """
    code = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm font-mono uppercase bg-slate-50',
            'placeholder': 'Auto-assigned (e.g. V001)',
        }),
        help_text="Leave blank to automatically assign the next sequential ID (V001, V002...)"
    )

    class Meta:
        model = Village
        fields = ['code', 'name', 'district', 'state', 'is_active']
        widgets = {
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
        if not code:
            code = generate_next_village_code()
        elif not re.match(r'^[A-Z0-9\-_]+$', code):
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
    Form to configure Wards under a selected Village.
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
    Form for Super Admin to create a Village Manager account.
    Manager ID is auto-assigned (e.g. V001-M1) based on the selected Village.
    """
    username = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm bg-slate-50',
            'placeholder': 'Auto-assigned (e.g. V001-M1)',
        }),
        help_text="Leave blank to automatically assign sequential Manager ID (e.g. V001-M1)."
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
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm',
            'placeholder': '•••••••• (Leave blank for default: Manager123@)',
        }),
        help_text="Leave blank to automatically set default password (Manager123@)."
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
        if username and User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(f"Username '{username}' is already taken.")
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password and len(password) < 6:
            raise forms.ValidationError("Password must be at least 6 characters long.")
        return password

    def save(self):
        cd = self.cleaned_data
        village = cd['village']
        username = cd.get('username')
        if not username:
            username = generate_next_manager_username(village)
        password = cd.get('password') or 'Manager123@'

        user = User.objects.create_user(
            username=username,
            email=cd.get('email', ''),
            first_name=cd.get('first_name', ''),
            last_name=cd.get('last_name', ''),
            password=password
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = RoleChoices.VILLAGE_MANAGER
        profile.village = village
        profile.phone_number = cd.get('phone_number', '')
        profile.save()
        user.profile = profile
        user._raw_password = password
        return user
