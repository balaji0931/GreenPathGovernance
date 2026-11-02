import json
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.models import User
from django.db import transaction

from accounts.models import RoleChoices, UserProfile
from accounts.decorators import role_required, is_json_request
from .models import Village, Ward
from .forms import VillageForm, WardForm, VillageManagerCreateForm


@role_required([RoleChoices.VILLAGE_MANAGER])
def manager_dashboard_view(request):
    """Placeholder view for Village Manager portal until Phase 3/5."""
    return render(request, 'core/landing.html')


@role_required([RoleChoices.SUPER_ADMIN])
def superadmin_dashboard_view(request):
    """
    Super Admin Governance HQ Dashboard (FR-12).
    Shows platform aggregates, village registers, and manager appointments.
    """
    villages = Village.objects.prefetch_related('wards', 'user_profiles__user').order_by('-created_at')
    managers = UserProfile.objects.filter(
        role=RoleChoices.VILLAGE_MANAGER
    ).select_related('user', 'village').order_by('-created_at')

    total_villages = villages.count()
    active_villages = villages.filter(is_active=True).count()
    total_wards = Ward.objects.count()
    total_managers = managers.count()

    context = {
        'villages': villages,
        'managers': managers,
        'total_villages': total_villages,
        'active_villages': active_villages,
        'total_wards': total_wards,
        'total_managers': total_managers,
        'village_form': VillageForm(),
        'manager_form': VillageManagerCreateForm(),
    }
    return render(request, 'governance/superadmin_dashboard.html', context)


@role_required([RoleChoices.SUPER_ADMIN])
def village_create_view(request):
    """
    Create a new Village / Gram Panchayat (FR-09).
    """
    if request.method == 'POST':
        form = VillageForm(request.POST)
        if form.is_valid():
            village = form.save()
            messages.success(request, f"Gram Panchayat '{village.name}' ({village.code}) successfully created.")
            return redirect('village_detail', village_id=village.id)
        else:
            messages.error(request, "Failed to create village. Please correct the errors below.")
    else:
        form = VillageForm()

    return render(request, 'governance/village_form.html', {'form': form, 'title': 'Register New Gram Panchayat'})


@role_required([RoleChoices.SUPER_ADMIN])
def village_detail_view(request, village_id):
    """
    Village details and Ward configuration workspace (FR-10).
    """
    village = get_object_or_404(Village, pk=village_id)
    wards = village.wards.all().order_by('ward_number')
    managers = village.user_profiles.filter(role=RoleChoices.VILLAGE_MANAGER).select_related('user')
    ward_form = WardForm()

    context = {
        'village': village,
        'wards': wards,
        'managers': managers,
        'ward_form': ward_form,
    }
    return render(request, 'governance/village_detail.html', context)


@role_required([RoleChoices.SUPER_ADMIN])
@require_POST
def ward_create_view(request, village_id):
    """
    Add a new Ward to an existing Village (FR-10).
    """
    village = get_object_or_404(Village, pk=village_id)
    form = WardForm(request.POST)
    if form.is_valid():
        ward_number = form.cleaned_data['ward_number'].strip()
        if Ward.objects.filter(village=village, ward_number__iexact=ward_number).exists():
            messages.error(request, f"Ward '{ward_number}' already exists in {village.name}.")
        else:
            ward = form.save(commit=False)
            ward.village = village
            ward.save()
            messages.success(request, f"Ward '{ward.ward_number}' successfully added to {village.name}.")
    else:
        messages.error(request, "Invalid Ward data. Please verify ward number.")

    return redirect('village_detail', village_id=village.id)


@role_required([RoleChoices.SUPER_ADMIN])
def manager_create_view(request):
    """
    Create a Village Manager and assign to a Village (FR-11).
    """
    if request.method == 'POST':
        form = VillageManagerCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            village_name = user.profile.village.name if (user.profile and user.profile.village) else "assigned village"
            messages.success(
                request,
                f"Village Manager account '{user.username}' successfully provisioned for {village_name}."
            )
            return redirect('superadmin_dashboard')
        else:
            messages.error(request, "Failed to create Village Manager. Please check form errors.")
    else:
        form = VillageManagerCreateForm()

    return render(request, 'governance/manager_form.html', {
        'form': form,
        'title': 'Provision Village Manager Account'
    })


@role_required([RoleChoices.SUPER_ADMIN])
@require_POST
def village_toggle_status_view(request, village_id):
    """
    Activate or deactivate a Village.
    """
    village = get_object_or_404(Village, pk=village_id)
    village.is_active = not village.is_active
    village.save()
    status_str = "activated" if village.is_active else "deactivated"
    messages.info(request, f"Village '{village.name}' has been {status_str}.")
    return redirect('superadmin_dashboard')


# ==============================================================================
# REST-Style JSON API Endpoints (FR-51, FR-52, FR-53, FR-54)
# ==============================================================================

@role_required([RoleChoices.SUPER_ADMIN])
@csrf_protect
def api_villages_list_create(request):
    """
    GET /api/v1/villages/ -> List all villages
    POST /api/v1/villages/ -> Create a new village with optional wards
    """
    if request.method == 'GET':
        villages = Village.objects.prefetch_related('wards', 'user_profiles__user').all()
        data = []
        for v in villages:
            data.append({
                'id': v.id,
                'code': v.code,
                'name': v.name,
                'district': v.district,
                'state': v.state,
                'is_active': v.is_active,
                'wards_count': v.wards.count(),
                'wards': [{'id': w.id, 'number': w.ward_number, 'name': w.ward_name} for w in v.wards.all()],
                'managers': [
                    {'id': up.user.id, 'username': up.user.username, 'name': up.user.get_full_name()}
                    for up in v.user_profiles.filter(role=RoleChoices.VILLAGE_MANAGER)
                ]
            })
        return JsonResponse({'success': True, 'count': len(data), 'villages': data}, status=200)

    elif request.method == 'POST':
        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'success': False, 'error': 'Malformed JSON payload.'}, status=400)

        code = body.get('code', '').strip().upper()
        name = body.get('name', '').strip()
        district = body.get('district', '').strip()
        state = body.get('state', 'Maharashtra').strip()
        wards = body.get('wards', [])

        if not code or not name:
            return JsonResponse({'success': False, 'error': 'Code and Name are required fields.'}, status=400)

        if Village.objects.filter(code=code).exists():
            return JsonResponse({'success': False, 'error': f"Village code '{code}' already exists."}, status=400)

        with transaction.atomic():
            village = Village.objects.create(
                code=code,
                name=name,
                district=district,
                state=state,
                is_active=True
            )
            created_wards = []
            for w in wards:
                w_num = w.get('number', '') if isinstance(w, dict) else str(w)
                w_name = w.get('name', '') if isinstance(w, dict) else ''
                if w_num:
                    ward_obj = Ward.objects.create(village=village, ward_number=w_num, ward_name=w_name)
                    created_wards.append({'id': ward_obj.id, 'number': ward_obj.ward_number})

        return JsonResponse({
            'success': True,
            'message': 'Village created successfully.',
            'village': {
                'id': village.id,
                'code': village.code,
                'name': village.name,
                'district': village.district,
                'wards': created_wards,
            }
        }, status=201)

    return JsonResponse({'success': False, 'error': 'Method not allowed.'}, status=405)


@role_required([RoleChoices.SUPER_ADMIN])
@csrf_protect
def api_managers_list_create(request):
    """
    GET /api/v1/managers/ -> List all village managers
    POST /api/v1/managers/ -> Create manager and assign to village
    """
    if request.method == 'GET':
        managers = UserProfile.objects.filter(
            role=RoleChoices.VILLAGE_MANAGER
        ).select_related('user', 'village')
        data = []
        for m in managers:
            data.append({
                'id': m.user.id,
                'username': m.user.username,
                'name': m.user.get_full_name() or m.user.username,
                'email': m.user.email,
                'phone': m.phone_number,
                'village': {
                    'id': m.village.id,
                    'code': m.village.code,
                    'name': m.village.name,
                } if m.village else None,
                'is_active': m.user.is_active,
            })
        return JsonResponse({'success': True, 'count': len(data), 'managers': data}, status=200)

    elif request.method == 'POST':
        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'success': False, 'error': 'Malformed JSON payload.'}, status=400)

        username = body.get('username', '').strip()
        password = body.get('password', '')
        village_id = body.get('village_id')
        first_name = body.get('first_name', '').strip()
        last_name = body.get('last_name', '').strip()
        email = body.get('email', '').strip()
        phone = body.get('phone_number', '').strip()

        if not username or not password or not village_id:
            return JsonResponse({'success': False, 'error': 'Username, password, and village_id are required.'}, status=400)

        if User.objects.filter(username__iexact=username).exists():
            return JsonResponse({'success': False, 'error': f"Username '{username}' already exists."}, status=400)

        try:
            village = Village.objects.get(pk=village_id, is_active=True)
        except Village.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Assigned village does not exist or is inactive.'}, status=400)

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = RoleChoices.VILLAGE_MANAGER
            profile.village = village
            profile.phone_number = phone
            profile.save()

        return JsonResponse({
            'success': True,
            'message': 'Village Manager provisioned successfully.',
            'manager': {
                'id': user.id,
                'username': user.username,
                'name': user.get_full_name() or user.username,
                'village': {'id': village.id, 'code': village.code, 'name': village.name}
            }
        }, status=201)

    return JsonResponse({'success': False, 'error': 'Method not allowed.'}, status=405)
