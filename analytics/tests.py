import json
import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone

from governance.models import Village, Ward
from households.models import Household
from waste_collections.models import CollectionRecord, OutcomeChoices, MissedReasonChoices
from accounts.models import UserProfile, RoleChoices
from analytics.services import get_village_daily_report

class AnalyticsPhase5Tests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Village Setup
        self.village = Village.objects.create(code="VIL-SHIVAJI-01", name="Shivaji Gram Panchayat")
        self.ward_1 = Ward.objects.create(village=self.village, ward_number="Ward 01", ward_name="East")
        self.ward_2 = Ward.objects.create(village=self.village, ward_number="Ward 02", ward_name="West")

        # 2. Manager User
        self.manager_user = User.objects.create_user(username="mgr_shivaji", password="password123")
        self.manager_user.profile.role = RoleChoices.VILLAGE_MANAGER
        self.manager_user.profile.village = self.village
        self.manager_user.profile.save()

        # 3. Collector User
        self.collector_user = User.objects.create_user(username="col_shivaji", password="password123")
        self.collector_user.profile.role = RoleChoices.WASTE_COLLECTOR
        self.collector_user.profile.village = self.village
        self.collector_user.profile.save()

        # 4. Household Users & Records
        # HH1 in Ward 1 (Linked to resident1)
        self.resident1_user = User.objects.create_user(username="res_user1", password="password123")
        self.resident1_user.profile.role = RoleChoices.HOUSEHOLD
        self.resident1_user.profile.save()

        self.hh1 = Household.objects.create(
            village=self.village,
            ward=self.ward_1,
            head_name="Ashok Kumar",
            house_number="101",
            resident_user=self.resident1_user
        )

        # HH2 in Ward 1 (Active, no resident account)
        self.hh2 = Household.objects.create(
            village=self.village,
            ward=self.ward_1,
            head_name="Bina Devi",
            house_number="102"
        )

        # HH3 in Ward 2 (Active)
        self.hh3 = Household.objects.create(
            village=self.village,
            ward=self.ward_2,
            head_name="Chetan Sharma",
            house_number="201"
        )

        # HH4 in Ward 2 (Inactive - should be excluded from active report counts)
        self.hh4 = Household.objects.create(
            village=self.village,
            ward=self.ward_2,
            head_name="Inactive Resident",
            house_number="202",
            is_active=False
        )

        self.today = timezone.localdate()

    def test_daily_report_calculation_and_deduplication(self):
        """FR-40 to FR-44, Section 2.5: Aggregation math and latest saved record deduplication."""
        # Scenario:
        # HH1: Initially missed at 08:00 AM (House Locked)
        CollectionRecord.objects.create(
            household=self.hh1,
            collector=self.collector_user.profile,
            village=self.village,
            ward=self.ward_1,
            collection_date=self.today,
            collection_time=datetime.time(8, 0),
            outcome=OutcomeChoices.MISSED,
            missed_reason=MissedReasonChoices.LOCKED
        )

        # HH1: Revisiting at 11:30 AM -> Successfully Collected with 4-star rating
        CollectionRecord.objects.create(
            household=self.hh1,
            collector=self.collector_user.profile,
            village=self.village,
            ward=self.ward_1,
            collection_date=self.today,
            collection_time=datetime.time(11, 30),
            outcome=OutcomeChoices.COLLECTED,
            is_segregated=True,
            waste_wet=True,
            waste_dry=True,
            segregation_rating=4
        )

        # HH2: Collected with 5-star rating
        CollectionRecord.objects.create(
            household=self.hh2,
            collector=self.collector_user.profile,
            village=self.village,
            ward=self.ward_1,
            collection_date=self.today,
            collection_time=datetime.time(9, 15),
            outcome=OutcomeChoices.COLLECTED,
            is_segregated=True,
            waste_wet=True,
            segregation_rating=5
        )

        # HH3: No submission today (Pending / Uncollected)
        # HH4: Inactive

        # Compute report
        report = get_village_daily_report(self.village, self.today)

        # Assertions
        # Total active = HH1 + HH2 + HH3 = 3 (HH4 excluded)
        self.assertEqual(report['total_active_households'], 3)

        # Collected = 2 (HH1 latest status is COLLECTED, HH2 is COLLECTED)
        self.assertEqual(report['collected_count'], 2)

        # Missed / Uncollected = 3 - 2 = 1 (HH3)
        self.assertEqual(report['missed_count'], 1)

        # Coverage % = (2 / 3) * 100 = 66.7%
        self.assertEqual(report['collection_percentage'], 66.7)

        # Avg Segregation Rating = (4 + 5) / 2 = 4.5
        self.assertEqual(report['average_segregation_rating'], 4.5)

        # Ward 1 Breakdown: Total 2, Collected 2, Missed 0, Coverage 100.0%
        w1_data = next(w for w in report['ward_breakdown'] if w['ward_id'] == self.ward_1.id)
        self.assertEqual(w1_data['total_households'], 2)
        self.assertEqual(w1_data['collected'], 2)
        self.assertEqual(w1_data['missed_uncollected'], 0)
        self.assertEqual(w1_data['collection_percentage'], 100.0)

        # Ward 2 Breakdown: Total 1, Collected 0, Missed 1, Coverage 0.0%
        w2_data = next(w for w in report['ward_breakdown'] if w['ward_id'] == self.ward_2.id)
        self.assertEqual(w2_data['total_households'], 1)
        self.assertEqual(w2_data['collected'], 0)
        self.assertEqual(w2_data['missed_uncollected'], 1)
        self.assertEqual(w2_data['collection_percentage'], 0.0)

    def test_manager_reports_browser_view(self):
        """FR-39: Manager views date-filtered reports in HTML browser."""
        self.client.login(username="mgr_shivaji", password="password123")
        res = self.client.get(reverse('manager_reports'))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'analytics/manager_report.html')
        self.assertContains(res, "Daily Collection")
        self.assertContains(res, "Segregation Audit")
        self.assertContains(res, "Ward 01")
        self.assertContains(res, "Ward 02")

    def test_household_resident_dashboard_and_history(self):
        """FR-46 to FR-50: Resident portal views today status, QR code, and history."""
        # Record collection for HH1
        CollectionRecord.objects.create(
            household=self.hh1,
            collector=self.collector_user.profile,
            village=self.village,
            ward=self.ward_1,
            collection_date=self.today,
            collection_time=datetime.time(10, 0),
            outcome=OutcomeChoices.COLLECTED,
            is_segregated=True,
            waste_wet=True,
            waste_dry=True,
            segregation_rating=5,
            remarks="Pristine bins"
        )

        self.client.login(username="res_user1", password="password123")
        res = self.client.get(reverse('household_dashboard'))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'analytics/household_dashboard.html')
        self.assertContains(res, "Ashok Kumar")
        self.assertContains(res, "Waste Collected")
        self.assertContains(res, self.hh1.uid)
        self.assertContains(res, "Pristine bins")

    def test_api_reports_summary_endpoint(self):
        """FR-51, FR-52: REST API report summary."""
        self.client.login(username="mgr_shivaji", password="password123")
        res = self.client.get(reverse('api_reports_summary'))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['summary']['total_active_households'], 3)
        self.assertEqual(len(data['ward_breakdown']), 2)

    def test_api_household_my_status_endpoint(self):
        """FR-51, FR-52: REST API resident status endpoint."""
        # Create record
        CollectionRecord.objects.create(
            household=self.hh1,
            collector=self.collector_user.profile,
            village=self.village,
            ward=self.ward_1,
            collection_date=self.today,
            collection_time=datetime.time(9, 30),
            outcome=OutcomeChoices.COLLECTED,
            is_segregated=True,
            segregation_rating=4
        )

        self.client.login(username="res_user1", password="password123")
        res = self.client.get(reverse('api_household_my_status'))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['household']['uid'], self.hh1.uid)
        self.assertEqual(data['today_status']['outcome'], 'COLLECTED')
        self.assertEqual(data['today_status']['segregation_rating'], 4)
