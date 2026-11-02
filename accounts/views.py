import json
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib import messages
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import LoginForm
from .models import RoleChoices, UserProfile

def get_role_redirect_url(user):
    """
    Computes the appropriate operational landing page based on role (FR-04).
    """
    if not user.is_authenticated:
        return reverse('landing')

    profile = getattr(user, 'profile', None)
    role = profile.role if profile else None

    if user.is_superuser or role == RoleChoices.SUPER_ADMIN:
        return reverse('superadmin_dashboard')
    elif role == RoleChoices.VILLAGE_MANAGER:
        return reverse('manager_dashboard')
    elif role == RoleChoices.WASTE_COLLECTOR:
        return reverse('collector_doorstep')
    elif role == RoleChoices.HOUSEHOLD:
        return reverse('household_dashboard')

    return reverse('landing')


def role_redirect_view(request):
    """
    Central dispatcher redirecting authenticated users to their authorized workspace (FR-04).
    """
    if not request.user.is_authenticated:
        return redirect('login')
    return redirect(get_role_redirect_url(request.user))


def login_view(request):
    """
    Browser-facing login view with clean validation and role-based routing (FR-01, FR-03, FR-04).
    """
    if request.user.is_authenticated:
        return redirect('role_redirect')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")

            # Respect safe 'next' redirect if provided
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)

            return redirect('role_redirect')
        else:
            messages.error(request, "Invalid username or password. Please verify and try again.")
    else:
        form = LoginForm(request)

    return render(request, 'accounts/login.html', {
        'form': form,
        'next': request.GET.get('next', ''),
    })


def logout_view(request):
    """
    Terminates the user's active session and redirects to landing page (FR-07).
    """
    if request.user.is_authenticated:
        auth_logout(request)
        messages.info(request, "You have been signed out successfully.")
    return redirect('landing')


# ==============================================================================
# REST-Style JSON API Endpoints (FR-51 to FR-55)
# ==============================================================================

@csrf_protect
@require_POST
def api_login(request):
    """
    POST /api/v1/auth/login/
    Authenticates user via JSON payload and creates session cookie.
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'success': False, 'error': 'Malformed JSON payload.'}, status=400)

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return JsonResponse({'success': False, 'error': 'Both username and password are required.'}, status=400)

    user = authenticate(request, username=username, password=password)
    if user is not None:
        if not user.is_active:
            return JsonResponse({'success': False, 'error': 'Account is inactive.'}, status=403)

        auth_login(request, user)
        profile = getattr(user, 'profile', None)

        return JsonResponse({
            'success': True,
            'message': 'Authentication successful.',
            'user': {
                'id': user.id,
                'username': user.username,
                'name': user.get_full_name() or user.username,
                'role': profile.role if profile else None,
                'village': {
                    'id': profile.village.id,
                    'code': profile.village.code,
                    'name': profile.village.name,
                } if (profile and profile.village) else None,
            },
            'redirect_url': get_role_redirect_url(user),
        }, status=200)

    return JsonResponse({'success': False, 'error': 'Invalid username or password.'}, status=401)


@csrf_protect
@require_POST
def api_logout(request):
    """
    POST /api/v1/auth/logout/
    Terminates the authenticated session cookie.
    """
    if request.user.is_authenticated:
        auth_logout(request)
    return JsonResponse({'success': True, 'message': 'Session invalidated successfully.'}, status=200)


def api_me(request):
    """
    GET /api/v1/auth/me/
    Returns currently authenticated user profile and permissions.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required.'}, status=401)

    profile = getattr(request.user, 'profile', None)
    return JsonResponse({
        'success': True,
        'user': {
            'id': request.user.id,
            'username': request.user.username,
            'name': request.user.get_full_name() or request.user.username,
            'role': profile.role if profile else None,
            'phone': profile.phone_number if profile else '',
            'village': {
                'id': profile.village.id,
                'code': profile.village.code,
                'name': profile.village.name,
            } if (profile and profile.village) else None,
            'is_superuser': request.user.is_superuser,
        }
    }, status=200)
