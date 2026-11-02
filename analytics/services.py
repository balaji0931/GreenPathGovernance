from django.utils import timezone
from households.models import Household
from waste_collections.models import CollectionRecord, OutcomeChoices
from governance.models import Ward

def get_village_daily_report(village, target_date=None):
    """
    Computes date-filtered totals and ward-wise analytics for a Village Manager (FR-39 to FR-45).
    Applies exact SRS Section 2.5 deduplication rule:
    If multiple entries exist for the same household on target_date, the latest saved record
    determines the displayed status.
    """
    if target_date is None:
        target_date = timezone.localdate()

    # 1. Total Active Households in this village (FR-40)
    active_households = list(
        Household.objects.filter(village=village, is_active=True).select_related('ward')
    )
    total_active_households = len(active_households)

    # 2. Retrieve all collection records for the target date, ordered by time/created_at
    records = CollectionRecord.objects.filter(
        village=village,
        collection_date=target_date
    ).select_related('household', 'collector__user', 'ward').order_by('collection_time', 'created_at')

    # Deduplicate: latest saved entry per household on target_date
    latest_record_by_hh = {}
    for r in records:
        latest_record_by_hh[r.household_id] = r

    # 3. Aggregates computation
    collected_count = 0
    rating_sum = 0
    rating_count = 0

    # Categorized households for detail views if needed
    collected_hh_ids = set()
    explicit_missed_hh_ids = set()

    for hh in active_households:
        latest = latest_record_by_hh.get(hh.id)
        if latest and latest.outcome == OutcomeChoices.COLLECTED:
            collected_count += 1
            collected_hh_ids.add(hh.id)
            if latest.segregation_rating is not None and 1 <= latest.segregation_rating <= 5:
                rating_sum += latest.segregation_rating
                rating_count += 1
        elif latest and latest.outcome == OutcomeChoices.MISSED:
            explicit_missed_hh_ids.add(hh.id)

    # FR-42: Missed / Uncollected = Active households minus households counted as collected
    missed_count = total_active_households - collected_count

    # FR-43: Collection percentage = (Collected / Total Active) * 100
    if total_active_households > 0:
        collection_percentage = round((collected_count / total_active_households) * 100, 1)
    else:
        collection_percentage = 0.0

    # FR-44: Average segregation rating for collected entries with valid rating
    if rating_count > 0:
        average_segregation_rating = round(rating_sum / rating_count, 2)
    else:
        average_segregation_rating = None

    # 4. Ward-wise Breakdown (FR-45)
    wards = village.wards.filter(is_active=True).order_by('ward_number')
    ward_breakdown = []

    for ward in wards:
        ward_hhs = [hh for hh in active_households if hh.ward_id == ward.id]
        w_total = len(ward_hhs)
        w_collected = 0
        w_rating_sum = 0
        w_rating_count = 0

        for hh in ward_hhs:
            latest = latest_record_by_hh.get(hh.id)
            if latest and latest.outcome == OutcomeChoices.COLLECTED:
                w_collected += 1
                if latest.segregation_rating is not None and 1 <= latest.segregation_rating <= 5:
                    w_rating_sum += latest.segregation_rating
                    w_rating_count += 1

        w_missed = w_total - w_collected
        w_pct = round((w_collected / w_total) * 100, 1) if w_total > 0 else 0.0
        w_avg_rating = round(w_rating_sum / w_rating_count, 2) if w_rating_count > 0 else None

        ward_breakdown.append({
            'ward_id': ward.id,
            'ward_number': ward.ward_number,
            'ward_name': ward.ward_name,
            'total_households': w_total,
            'collected': w_collected,
            'missed_uncollected': w_missed,
            'collection_percentage': w_pct,
            'average_rating': w_avg_rating,
        })

    return {
        'village': village,
        'target_date': target_date,
        'total_active_households': total_active_households,
        'collected_count': collected_count,
        'missed_count': missed_count,
        'collection_percentage': collection_percentage,
        'average_segregation_rating': average_segregation_rating,
        'rating_count': rating_count,
        'ward_breakdown': ward_breakdown,
        'raw_submissions_count': records.count(),
    }

