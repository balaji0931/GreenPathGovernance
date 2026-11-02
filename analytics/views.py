import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse

from accounts.models import RoleChoices
from accounts.decorators import role_required, village_access_required
from households.models import Household
from households.qr_service import generate_household_qr_payload
from waste_collections.models import CollectionRecord, OutcomeChoices
from .services import get_village_daily_report


@role_required([RoleChoices.VILLAGE_MANAGER])
@village_access_required
def manager_reports_view(request):
    """
    Village Manager Date-Filtered Analytics & Ward Coverage Report (FR-39 to FR-45).
    """
    village = request.user.profile.village
    date_str = request.GET.get('date', '').strip()
    target_date = timezone.localdate()

    if date_str:
        try:
            target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            messages.warning(request, f"Invalid date '{date_str}'. Showing report for today.")
            target_date = timezone.localdate()

    report_data = get_village_daily_report(village, target_date)
    return render(request, 'analytics/manager_report.html', {
        'report': report_data,
        'village': village,
        'selected_date': target_date.strftime('%Y-%m-%d'),
        'today_str': timezone.localdate().strftime('%Y-%m-%d'),
    })


@role_required([RoleChoices.HOUSEHOLD])
def household_dashboard_view(request):
    """
    Household Citizen Portal (FR-46 to FR-50).
    Displays today's collection status, personal QR card, and reverse-chronological history.
    """
    household = getattr(request.user, 'linked_household', None)
    if not household:
        # Fallback query
        household = Household.objects.filter(resident_user=request.user).first()

    if not household:
        return render(request, 'analytics/household_unlinked.html', {
            'username': request.user.username,
        })

    today = timezone.localdate()

    # FR-47: Today's collection status
    today_visit = CollectionRecord.objects.filter(
        household=household,
        collection_date=today
    ).select_related('collector__user').order_by('-collection_time', '-created_at').first()

    # FR-49: Reverse-chronological collection history
    history = CollectionRecord.objects.filter(
        household=household
    ).select_related('collector__user').order_by('-collection_date', '-collection_time')[:30]

    context = {
        'household': household,
        'today': today,
        'today_visit': today_visit,
        'history': history,
        'village': household.village,
    }
    return render(request, 'analytics/household_dashboard.html', context)


# ==============================================================================
# REST-Style JSON API Endpoints (FR-51, FR-52, FR-53, FR-54)
# ==============================================================================

@role_required([RoleChoices.VILLAGE_MANAGER])
@village_access_required
def api_reports_summary(request):
    """
    GET /api/v1/reports/summary/?date=YYYY-MM-DD
    Returns JSON summary totals and ward-wise metrics for manager's village (FR-39 to FR-45).
    """
    village = request.user.profile.village
    date_str = request.GET.get('date', '').strip()
    target_date = timezone.localdate()

    if date_str:
        try:
            target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'success': False, 'error': "Invalid date format. Expected 'YYYY-MM-DD'."}, status=400)

    report_data = get_village_daily_report(village, target_date)

    return JsonResponse({
        'success': True,
        'village': {
            'id': village.id,
            'code': village.code,
            'name': village.name,
        },
        'date': target_date.strftime('%Y-%m-%d'),
        'summary': {
            'total_active_households': report_data['total_active_households'],
            'collected_today': report_data['collected_count'],
            'missed_uncollected': report_data['missed_count'],
            'collection_percentage': report_data['collection_percentage'],
            'average_segregation_rating': report_data['average_segregation_rating'],
        },
        'ward_breakdown': report_data['ward_breakdown'],
    }, status=200)


@role_required([RoleChoices.HOUSEHOLD])
def api_household_my_status(request):
    """
    GET /api/v1/household/my-status/
    Returns today's status, personal QR data, and collection history for linked household (FR-46 to FR-50).
    """
    household = getattr(request.user, 'linked_household', None)
    if not household:
        household = Household.objects.filter(resident_user=request.user).first()

    if not household:
        return JsonResponse({'success': False, 'error': 'No household record is linked to this account.'}, status=404)

    today = timezone.localdate()
    today_visit = CollectionRecord.objects.filter(
        household=household,
        collection_date=today
    ).select_related('collector__user').order_by('-collection_time', '-created_at').first()

    history = CollectionRecord.objects.filter(
        household=household
    ).select_related('collector__user').order_by('-collection_date', '-collection_time')[:15]

    history_data = [{
        'date': v.collection_date.strftime('%Y-%m-%d'),
        'time': v.collection_time.strftime('%H:%M:%S'),
        'outcome': v.outcome,
        'is_segregated': v.is_segregated,
        'segregation_rating': v.segregation_rating,
        'waste_types': {
            'wet': v.waste_wet,
            'dry': v.waste_dry,
            'sanitary': v.waste_sanitary,
        },
        'missed_reason': v.get_missed_reason_display() if v.outcome == OutcomeChoices.MISSED else None,
        'collector_name': v.collector.user.get_full_name() if v.collector else None,
        'remarks': v.remarks,
    } for v in history]

    return JsonResponse({
        'success': True,
        'household': {
            'uid': household.uid,
            'head_name': household.head_name,
            'house_number': household.house_number,
            'ward': household.ward.ward_number,
            'village': household.village.name,
            'qr_image_url': household.qr_code_image.url if household.qr_code_image else None,
        },
        'today_status': {
            'date': today.strftime('%Y-%m-%d'),
            'recorded': today_visit is not None,
            'outcome': today_visit.outcome if today_visit else 'NOT_RECORDED_YET',
            'time': today_visit.collection_time.strftime('%H:%M:%S') if today_visit else None,
            'is_segregated': today_visit.is_segregated if today_visit else None,
            'segregation_rating': today_visit.segregation_rating if today_visit else None,
            'missed_reason': today_visit.get_missed_reason_display() if (today_visit and today_visit.outcome == OutcomeChoices.MISSED) else None,
            'collector_name': today_visit.collector.user.get_full_name() if (today_visit and today_visit.collector) else None,
        },
        'history_count': len(history_data),
        'history': history_data,
    }, status=200)
