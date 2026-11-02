from functools import wraps
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from .models import RoleChoices

def is_json_request(request):
    """Detect if the incoming request expects a JSON response."""
    return (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or
        request.content_type == 'application/json' or
        'application/json' in request.headers.get('Accept', '') or
        request.path.startswith('/api/')
    )

def role_required(allowed_roles):
    """
    Decorator to enforce authentication and role-based permissions (FR-05).
    allowed_roles: list or tuple of RoleChoices values e.g. [RoleChoices.SUPER_ADMIN]
    """
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 1. Verify Authentication (FR-01, FR-03)
            if not request.user.is_authenticated:
                if is_json_request(request):
                    return JsonResponse({
                        'success': False,
                        'error': 'Authentication credentials are required.'
                    }, status=401)
                return redirect(f"/accounts/login/?next={request.path}")

            # 2. Check Profile Existence & Role
            user_profile = getattr(request.user, 'profile', None)
            user_role = user_profile.role if user_profile else None

            # Superusers always have SUPER_ADMIN clearance
            is_authorized = (
                (request.user.is_superuser and RoleChoices.SUPER_ADMIN in allowed_roles) or
                (user_role in allowed_roles)
            )

            if not is_authorized:
                if is_json_request(request):
                    return JsonResponse({
                        'success': False,
                        'error': f"Access denied. Required role(s): {', '.join(allowed_roles)}. Your role is '{user_role}'."
                    }, status=403)
                return render(request, 'errors/403.html', {
                    'message': 'You do not have authorization to view this operational portal.'
                }, status=403)

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def village_access_required(view_func):
    """
    Ensures that Village Managers and Waste Collectors are assigned to an active Village,
    and prevents them from accessing/mutating records from other villages (FR-06).
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            if is_json_request(request):
                return JsonResponse({'success': False, 'error': 'Authentication required.'}, status=401)
            return redirect('login')

        profile = getattr(request.user, 'profile', None)

        # Super Admin has system-wide clearance across all villages
        if request.user.is_superuser or (profile and profile.role == RoleChoices.SUPER_ADMIN):
            return view_func(request, *args, **kwargs)

        # For Village Managers & Collectors, village assignment is strictly required
        if not profile or not profile.village:
            error_msg = "Account is not assigned to any Gram Panchayat / Village."
            if is_json_request(request):
                return JsonResponse({'success': False, 'error': error_msg}, status=403)
            return render(request, 'errors/403.html', {'message': error_msg}, status=403)

        if not profile.village.is_active:
            error_msg = "The assigned Gram Panchayat / Village is currently inactive."
            if is_json_request(request):
                return JsonResponse({'success': False, 'error': error_msg}, status=403)
            return render(request, 'errors/403.html', {'message': error_msg}, status=403)

        # If a specific village identifier is passed in kwargs, assert match
        target_village_id = kwargs.get('village_id')
        if target_village_id is not None and int(target_village_id) != profile.village.id:
            error_msg = "Cross-village access denied. You may only access your assigned Gram Panchayat."
            if is_json_request(request):
                return JsonResponse({'success': False, 'error': error_msg}, status=403)
            return render(request, 'errors/403.html', {'message': error_msg}, status=403)

        return view_func(request, *args, **kwargs)
    return _wrapped_view

