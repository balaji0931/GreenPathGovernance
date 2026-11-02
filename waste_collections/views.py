import json
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect

from accounts.models import RoleChoices
from accounts.decorators import role_required, village_access_required
from households.models import Household
from .models import CollectionRecord, OutcomeChoices, MissedReasonChoices
from .forms import DoorstepCollectionForm


@role_required([RoleChoices.WASTE_COLLECTOR])
@village_access_required
def collector_doorstep_view(request):
    """
    Mobile Doorstep Collection App for Waste Collector (FR-27, FR-61).
    Displays camera QR scanner and collection recording form.
    """
    collector_profile = request.user.profile
    village = collector_profile.village
    today = timezone.localdate()

    # Collector's saved collection count for the current date (FR-61)
    today_count = CollectionRecord.objects.filter(
        collector=collector_profile,
        collection_date=today
    ).count()

    # Last 5 recorded entries by this collector today
    recent_visits = CollectionRecord.objects.filter(
        collector=collector_profile,
        collection_date=today
    ).select_related('household', 'ward').order_by('-collection_time')[:5]

    form = DoorstepCollectionForm()

    context = {
        'village': village,
        'today': today,
        'today_count': today_count,
        'recent_visits': recent_visits,
        'form': form,
    }
    return render(request, 'waste_collections/doorstep_app.html', context)


@role_required([RoleChoices.WASTE_COLLECTOR])
@village_access_required
@require_POST
def doorstep_submit_view(request):
    """
    Handles browser form submission for a verified household (FR-31 to FR-38, FR-58).
    """
    collector_profile = request.user.profile
    village = collector_profile.village
    form = DoorstepCollectionForm(request.POST)

    if form.is_valid():
        household_uid = form.cleaned_data['household_uid'].strip()
        try:
            household = Household.objects.get(uid=household_uid, village=village, is_active=True)
        except Household.DoesNotExist:
            messages.error(request, "Household not found, inactive, or belongs to another Gram Panchayat (FR-29).")
            return redirect('collector_doorstep')

        record = form.save(commit=False)
        record.household = household
        record.collector = collector_profile
        record.village = village
        record.ward = household.ward
        record.collection_date = timezone.localdate()
        record.collection_time = timezone.localtime().time()
        record.save()

        status_label = "Collected" if record.outcome == OutcomeChoices.COLLECTED else f"Missed ({record.get_missed_reason_display()})"
        messages.success(
            request,
            f"Visit for {household.head_name} (#{household.house_number}) recorded: {status_label}."
        )
        return redirect('collector_doorstep')
    else:
        # Re-render with form errors
        today = timezone.localdate()
        today_count = CollectionRecord.objects.filter(collector=collector_profile, collection_date=today).count()
        recent_visits = CollectionRecord.objects.filter(collector=collector_profile, collection_date=today).order_by('-collection_time')[:5]
        messages.error(request, "Please correct the errors in the collection form.")
        return render(request, 'waste_collections/doorstep_app.html', {
            'village': village,
            'today': today,
            'today_count': today_count,
            'recent_visits': recent_visits,
            'form': form,
            'open_form': True,
        })


# ==============================================================================
# REST-Style JSON API Endpoints (FR-51, FR-52, FR-53, FR-54)
# ==============================================================================

@role_required([RoleChoices.WASTE_COLLECTOR])
@village_access_required
@csrf_protect
@require_POST
def api_validate_qr(request):
    """
    POST /api/v1/collector/validate-qr/
    Validates scanned QR string against database before showing collection form (FR-28, FR-29, FR-30).
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'success': False, 'error': 'Malformed JSON payload.'}, status=400)

    raw_qr = body.get('qr_data', '').strip()
    if not raw_qr:
        return JsonResponse({'success': False, 'error': 'QR data payload is required.'}, status=400)

    # Attempt parsing as JSON payload: {"uid": "...", "vcode": "..."}
    target_uid = raw_qr
    try:
        parsed = json.loads(raw_qr)
        if isinstance(parsed, dict) and 'uid' in parsed:
            target_uid = parsed['uid']
    except Exception:
        # Raw UID fallback
        target_uid = raw_qr.strip()

    collector_village = request.user.profile.village

    try:
        household = Household.objects.select_related('ward', 'village').get(uid=target_uid)
    except Household.DoesNotExist:
        return JsonResponse({'success': False, 'error': f"Household UID '{target_uid}' not recognized."}, status=404)

    # Multi-tenancy check (FR-29): Household must belong to collector's village
    if household.village_id != collector_village.id:
        return JsonResponse({
            'success': False,
            'error': f"Cross-village violation! This household belongs to {household.village.name}, not your assigned Panchayat ({collector_village.name})."
        }, status=403)

    if not household.is_active:
        return JsonResponse({'success': False, 'error': 'This household is currently inactive and cannot accept collections.'}, status=400)

    # Return verified household details for doorstep confirmation (FR-30)
    return JsonResponse({
        'success': True,
        'household': {
            'id': household.id,
            'uid': household.uid,
            'head_name': household.head_name,
            'house_number': household.house_number,
            'ward': household.ward.ward_number,
            'ward_name': household.ward.ward_name,
            'street': household.street_address,
            'village': household.village.name,
        }
    }, status=200)


@role_required([RoleChoices.WASTE_COLLECTOR])
@village_access_required
@csrf_protect
@require_POST
def api_collector_submit(request):
    """
    POST /api/v1/collector/submit/
    Submits doorstep collection outcome via REST API (FR-31 to FR-38).
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'success': False, 'error': 'Malformed JSON payload.'}, status=400)

    uid = body.get('household_uid', '').strip()
    collector_village = request.user.profile.village

    try:
        household = Household.objects.get(uid=uid, village=collector_village, is_active=True)
    except Household.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Household not found, inactive, or belongs to another village.'}, status=400)

    outcome = body.get('outcome', OutcomeChoices.COLLECTED)
    if outcome not in [OutcomeChoices.COLLECTED, OutcomeChoices.MISSED]:
        return JsonResponse({'success': False, 'error': "Invalid outcome. Must be 'COLLECTED' or 'MISSED'."}, status=400)

    record = CollectionRecord(
        household=household,
        collector=request.user.profile,
        village=collector_village,
        ward=household.ward,
        collection_date=timezone.localdate(),
        collection_time=timezone.localtime().time(),
        outcome=outcome,
        remarks=body.get('remarks', '').strip()
    )

    if outcome == OutcomeChoices.COLLECTED:
        record.is_segregated = bool(body.get('is_segregated', True))
        record.waste_wet = bool(body.get('waste_wet', False))
        record.waste_dry = bool(body.get('waste_dry', False))
        record.waste_sanitary = bool(body.get('waste_sanitary', False))
        rating = body.get('segregation_rating')
        if not rating or not (1 <= int(rating) <= 5):
            return JsonResponse({'success': False, 'error': 'A segregation rating between 1 and 5 is required for a collected outcome.'}, status=400)
        record.segregation_rating = int(rating)
        record.missed_reason = ''
    else:
        reason = body.get('missed_reason', '')
        if not reason:
            return JsonResponse({'success': False, 'error': 'A missed reason is mandatory when outcome is Missed.'}, status=400)
        record.missed_reason = reason
        record.segregation_rating = None
        record.is_segregated = None

    try:
        record.save()
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

    # Return updated today collection count (FR-61)
    today_count = CollectionRecord.objects.filter(
        collector=request.user.profile,
        collection_date=timezone.localdate()
    ).count()

    return JsonResponse({
        'success': True,
        'message': f"Collection visit recorded for {household.head_name} (#{household.house_number}).",
        'record_id': record.id,
        'today_total': today_count,
    }, status=201)
