from django import forms
from django.contrib.auth.forms import AuthenticationForm

class LoginForm(AuthenticationForm):
    """
    Standardized Django Authentication Form with modern Tailwind styling.
    """
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm placeholder-slate-400 transition-colors',
            'placeholder': 'Enter your username',
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

