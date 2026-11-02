import json
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect

from accounts.models import RoleChoices, UserProfile
from accounts.decorators import role_required, village_access_required, is_json_request
from governance.models import Village, Ward
from .models import Household
from .forms import HouseholdRegistrationForm, HouseholdEditForm, WasteCollectorCreateForm
from .qr_service import generate_household_qr_payload


@role_required([RoleChoices.VILLAGE_MANAGER])
@village_access_required
def manager_dashboard_view(request):
    """
    Village Manager Central Workspace (FR-14 to FR-20).
    Displays operational overview of the manager's assigned Gram Panchayat.
    """
    village = request.user.profile.village
    households = Household.objects.filter(village=village)
    collectors = UserProfile.objects.filter(
        village=village,
        role=RoleChoices.WASTE_COLLECTOR
    ).select_related('user')
    wards = village.wards.all()

    total_households = households.count()
    active_households = households.filter(is_active=True).count()
    total_collectors = collectors.count()
    active_collectors = collectors.filter(user__is_active=True).count()

    recent_households = households.select_related('ward').order_by('-registered_at')[:8]

    context = {
        'village': village,
        'wards': wards,
        'total_households': total_households,
        'active_households': active_households,
        'total_collectors': total_collectors,
        'active_collectors': active_collectors,
        'recent_households': recent_households,
    }
    return render(request, 'households/manager_dashboard.html', context)


@role_required([RoleChoices.VILLAGE_MANAGER])
@village_access_required
def household_list_view(request):
    """
    Searchable and filterable register of households in the manager's village (FR-20).
    """
    village = request.user.profile.village
    queryset = Household.objects.filter(village=village).select_related('ward', 'resident_user').order_by('ward__ward_number', 'house_number')

    # Search filter
    q = request.GET.get('q', '').strip()
    if q:
        queryset = queryset.filter(
            Q(head_name__icontains=q) |
            Q(house_number__icontains=q) |
            Q(uid__icontains=q) |
            Q(phone_number__icontains=q)
        )

    # Ward filter
    ward_id = request.GET.get('ward')
    if ward_id:
        queryset = queryset.filter(ward_id=ward_id)

    wards = village.wards.filter(is_active=True)

    context = {
        'village': village,
        'households': queryset,
        'wards': wards,
        'selected_ward': ward_id,
        'search_query': q,
        'total_count': queryset.count(),
    }
    return render(request, 'households/household_list.html', context)


@role_required([RoleChoices.VILLAGE_MANAGER])
@village_access_required
def household_create_view(request):
    """
    Register a new household and generate UID + QR code (FR-16, FR-17, FR-23).
    """
    village = request.user.profile.village
    if request.method == 'POST':
        form = HouseholdRegistrationForm(request.POST, village=village)
        if form.is_valid():
            household = form.save()
            messages.success(
                request,
                f"Household for {household.head_name} (#{household.house_number}) registered successfully with UID '{household.uid}'."
            )
            return redirect('household_qr_card', household_id=household.id)
        else:
            messages.error(request, "Failed to register household. Please correct form errors.")
    else:
        form = HouseholdRegistrationForm(village=village)

    return render(request, 'households/household_form.html', {
        'form': form,
        'village': village,
        'title': 'Register New Household'
    })


@role_required([RoleChoices.VILLAGE_MANAGER])
@village_access_required
def household_edit_view(request, household_id):
    """
    Edit household details or toggle active status (FR-19, FR-22).
    """
    village = request.user.profile.village
    household = get_object_or_404(Household, pk=household_id, village=village)

    if request.method == 'POST':
        form = HouseholdEditForm(request.POST, instance=household, village=village)
        if form.is_valid():
            form.save()
            messages.success(request, f"Household '{household.uid}' updated successfully.")
            return redirect('household_list')
    else:
        form = HouseholdEditForm(instance=household, village=village)

    return render(request, 'households/household_form.html', {
        'form': form,
        'village': village,
        'household': household,
        'title': f"Edit Household ({household.uid})"
    })


def household_qr_card_view(request, household_id):
    """
    Print-ready QR Card for doorstep installation (FR-25, FR-26).
    Accessible to Village Manager (within village) or Household resident (own record).
    """
    if not request.user.is_authenticated:
        return redirect('login')

    household = get_object_or_404(Household, pk=household_id)
    profile = getattr(request.user, 'profile', None)

    # Permission check: Super Admin, assigned Village Manager, or linked Resident
    is_super = request.user.is_superuser or (profile and profile.role == RoleChoices.SUPER_ADMIN)
    is_mgr = profile and profile.role == RoleChoices.VILLAGE_MANAGER and profile.village_id == household.village_id
    is_owner = household.resident_user_id == request.user.id

    if not (is_super or is_mgr or is_owner):
        return render(request, 'errors/403.html', {'message': "Unauthorized to view this QR code."}, status=403)

    return render(request, 'households/qr_card.html', {
        'household': household,
        'village': household.village,
    })


@role_required([RoleChoices.VILLAGE_MANAGER])
@village_access_required
def household_qr_batch_view(request):
    """
    Batch printable QR sheets for ward distribution (FR-25).
    """
    village = request.user.profile.village
    ward_id = request.GET.get('ward')
    households = Household.objects.filter(village=village, is_active=True).select_related('ward')
    if ward_id:
        households = households.filter(ward_id=ward_id)

    return render(request, 'households/qr_batch.html', {
        'village': village,
        'households': households,
        'ward_id': ward_id,
    })


@role_required([RoleChoices.VILLAGE_MANAGER])
@village_access_required
def collector_list_create_view(request):
    """
    Manage Waste Collectors in manager's village (FR-14, FR-15).
    """
    village = request.user.profile.village

    if request.method == 'POST':
        form = WasteCollectorCreateForm(request.POST)
        if form.is_valid():
            user = form.save(village=village)
            messages.success(request, f"Waste Collector account '{user.username}' created successfully.")
            return redirect('collector_manage')
        else:
            messages.error(request, "Failed to create collector. Please verify inputs.")
    else:
        form = WasteCollectorCreateForm()

    collectors = UserProfile.objects.filter(
        village=village,
        role=RoleChoices.WASTE_COLLECTOR
    ).select_related('user').order_by('-created_at')

    context = {
        'village': village,
        'collectors': collectors,
        'form': form,
    }
    return render(request, 'households/collector_manage.html', context)


@role_required([RoleChoices.VILLAGE_MANAGER])
@village_access_required
@require_POST
def collector_toggle_status_view(request, collector_user_id):
    """
    Activate/Deactivate collector account while preserving collection history (FR-15, FR-22).
    """
    village = request.user.profile.village
    target_profile = get_object_or_404(
        UserProfile,
        user_id=collector_user_id,
        village=village,
        role=RoleChoices.WASTE_COLLECTOR
    )
    user = target_profile.user
    user.is_active = not user.is_active
    user.save()
    status_str = "activated" if user.is_active else "deactivated"
    messages.info(request, f"Collector '{user.username}' has been {status_str}.")
    return redirect('collector_manage')


# ==============================================================================
# REST-Style JSON API Endpoints (FR-51, FR-52, FR-53, FR-54)
# ==============================================================================

@role_required([RoleChoices.VILLAGE_MANAGER])
@village_access_required
@csrf_protect
def api_households_list_create(request):
    """
    GET /api/v1/households/ -> List households in manager's village
    POST /api/v1/households/ -> Register household via JSON
    """
    village = request.user.profile.village

    if request.method == 'GET':
        ward_id = request.GET.get('ward')
        qs = Household.objects.filter(village=village).select_related('ward')
        if ward_id:
            qs = qs.filter(ward_id=ward_id)

        data = [{
            'id': h.id,
            'uid': h.uid,
            'head_name': h.head_name,
            'house_number': h.house_number,
            'ward': {'id': h.ward.id, 'number': h.ward.ward_number, 'name': h.ward.ward_name},
            'phone': h.phone_number,
            'is_active': h.is_active,
            'qr_image_url': h.qr_code_image.url if h.qr_code_image else None,
        } for h in qs]
        return JsonResponse({'success': True, 'count': len(data), 'households': data}, status=200)

    elif request.method == 'POST':
        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'success': False, 'error': 'Malformed JSON payload.'}, status=400)

        head_name = body.get('head_name', '').strip()
        house_number = body.get('house_number', '').strip()
        ward_id = body.get('ward_id')
        phone_number = body.get('phone_number', '').strip()
        street_address = body.get('street_address', '').strip()

        if not head_name or not house_number or not ward_id:
            return JsonResponse({'success': False, 'error': 'head_name, house_number, and ward_id are required.'}, status=400)

        try:
            ward = Ward.objects.get(pk=ward_id, village=village)
        except Ward.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Ward does not exist or does not belong to your village.'}, status=400)

        household = Household.objects.create(
            village=village,
            ward=ward,
            head_name=head_name,
            house_number=house_number,
            street_address=street_address,
            phone_number=phone_number,
        )

        return JsonResponse({
            'success': True,
            'message': 'Household registered successfully.',
            'household': {
                'id': household.id,
                'uid': household.uid,
                'head_name': household.head_name,
                'house_number': household.house_number,
                'ward': household.ward.ward_number,
                'qr_image_url': household.qr_code_image.url if household.qr_code_image else None,
            }
        }, status=201)

    return JsonResponse({'success': False, 'error': 'Method not allowed.'}, status=405)


def api_household_qr(request, uid):
    """
    GET /api/v1/households/<uid>/qr/
    Returns QR image path and encoded payload for authorized user (FR-25, FR-26).
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required.'}, status=401)

    household = get_object_or_404(Household, uid=uid)
    profile = getattr(request.user, 'profile', None)

    # Scoping check
    is_super = request.user.is_superuser or (profile and profile.role == RoleChoices.SUPER_ADMIN)
    is_mgr = profile and profile.role == RoleChoices.VILLAGE_MANAGER and profile.village_id == household.village_id
    is_owner = household.resident_user_id == request.user.id

    if not (is_super or is_mgr or is_owner):
        return JsonResponse({'success': False, 'error': 'Access denied: not authorized for this household QR.'}, status=403)

    return JsonResponse({
        'success': True,
        'household': {
            'uid': household.uid,
            'head_name': household.head_name,
            'house_number': household.house_number,
            'ward': household.ward.ward_number,
            'village': household.village.name,
            'is_active': household.is_active,
            'qr_payload': generate_household_qr_payload(household),
            'qr_image_url': household.qr_code_image.url if household.qr_code_image else None,
        }
    }, status=200)


@role_required([RoleChoices.VILLAGE_MANAGER])
@village_access_required
@csrf_protect
def api_collectors_list_create(request):
    """
    GET /api/v1/collectors/ -> List collectors in manager's village
    POST /api/v1/collectors/ -> Create collector in manager's village
    """
    village = request.user.profile.village

    if request.method == 'GET':
        collectors = UserProfile.objects.filter(
            village=village,
            role=RoleChoices.WASTE_COLLECTOR
        ).select_related('user')
        data = [{
            'id': c.user.id,
            'username': c.user.username,
            'name': c.user.get_full_name() or c.user.username,
            'phone': c.phone_number,
            'is_active': c.user.is_active,
        } for c in collectors]
        return JsonResponse({'success': True, 'count': len(data), 'collectors': data}, status=200)

    elif request.method == 'POST':
        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'success': False, 'error': 'Malformed JSON payload.'}, status=400)

        username = body.get('username', '').strip()
        password = body.get('password', '')
        phone = body.get('phone_number', '').strip()
        first_name = body.get('first_name', '').strip()
        last_name = body.get('last_name', '').strip()

        if not username or not password:
            return JsonResponse({'success': False, 'error': 'Username and password are required.'}, status=400)

        if User.objects.filter(username__iexact=username).exists():
            return JsonResponse({'success': False, 'error': f"Username '{username}' is already taken."}, status=400)

        form = WasteCollectorCreateForm({
            'username': username,
            'password': password,
            'first_name': first_name,
            'last_name': last_name,
            'phone_number': phone,
        })
        if form.is_valid():
            user = form.save(village=village)
            return JsonResponse({
                'success': True,
                'message': 'Waste Collector registered successfully.',
                'collector': {
                    'id': user.id,
                    'username': user.username,
                    'name': user.get_full_name() or user.username,
                }
            }, status=201)
        else:
            return JsonResponse({'success': False, 'error': form.errors}, status=400)

    return JsonResponse({'success': False, 'error': 'Method not allowed.'}, status=405)
