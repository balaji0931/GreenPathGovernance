from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

class LoginForm(AuthenticationForm):
    """
    Standardized Django Authentication Form with modern Tailwind styling
    and case-insensitive username lookup (e.g. ADMIN vs admin).
    """
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm placeholder-slate-400 transition-colors',
            'placeholder': 'Enter your username (e.g. ADMIN, V001-M1)',
            'autocomplete': 'username',
            'autofocus': True,
        }),
        label="Username"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm placeholder-slate-400 transition-colors',
            'placeholder': '••••••••',
            'autocomplete': 'current-password',
        }),
        label="Password"
    )

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            # Case-insensitive user lookup to support ADMIN / V001-M1 / v001-m1
            user_obj = User.objects.filter(username__iexact=username.strip()).first()
            actual_username = user_obj.username if user_obj else username.strip()

            self.user_cache = authenticate(
                self.request,
                username=actual_username,
                password=password
            )
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data
