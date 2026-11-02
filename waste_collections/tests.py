import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import CollectionRecord, OutcomeChoices, MissedReasonChoices
from governance.models import Village, Ward
from households.models import Household
from accounts.models import UserProfile, RoleChoices

class WasteCollectionsPhase4Tests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Village Alpha
        self.village_a = Village.objects.create(code="VIL-ALPHA-01", name="Alpha Gram Panchayat", district="Pune")
        self.ward_a = Ward.objects.create(village=self.village_a, ward_number="Ward 01")

        # 2. Village Beta (for multi-tenant isolation testing)
        self.village_b = Village.objects.create(code="VIL-BETA-02", name="Beta Gram Panchayat", district="Nashik")
        self.ward_b = Ward.objects.create(village=self.village_b, ward_number="Ward 01")

        # 3. Collector for Village Alpha
        self.collector_user = User.objects.create_user(username="collector_alpha", password="password123")
        self.collector_user.profile.role = RoleChoices.WASTE_COLLECTOR
        self.collector_user.profile.village = self.village_a
        self.collector_user.profile.save()

        # 4. Active Household in Village Alpha
        self.hh_alpha = Household.objects.create(
            village=self.village_a,
            ward=self.ward_a,
            head_name="Sachin Tendulkar",
            house_number="100-Century",
            phone_number="9876500100"
        )

        # 5. Inactive Household in Village Alpha
        self.hh_inactive = Household.objects.create(
            village=self.village_a,
            ward=self.ward_a,
            head_name="Inactive Resident",
            house_number="00-X",
            is_active=False
        )

        # 6. Household in Village Beta (Out-of-village)
        self.hh_beta = Household.objects.create(
            village=self.village_b,
            ward=self.ward_b,
            head_name="Beta Resident",
            house_number="99-B"
        )

    def test_collection_record_model_validations(self):
        """FR-31 to FR-37: Model validation for collected vs missed visit constraints."""
        # 1. Collected without rating must fail
        with self.assertRaises(ValidationError):
            rec_invalid = CollectionRecord(
                household=self.hh_alpha,
                collector=self.collector_user.profile,
                outcome=OutcomeChoices.COLLECTED,
                is_segregated=True,
                segregation_rating=None  # Missing!
            )
            rec_invalid.save()

        # 2. Collected with rating > 5 must fail
        with self.assertRaises(ValidationError):
            rec_invalid2 = CollectionRecord(
                household=self.hh_alpha,
                collector=self.collector_user.profile,
                outcome=OutcomeChoices.COLLECTED,
                is_segregated=True,
                segregation_rating=6  # Out of range!
            )
            rec_invalid2.save()

        # 3. Missed without reason must fail
        with self.assertRaises(ValidationError):
            rec_missed_invalid = CollectionRecord(
                household=self.hh_alpha,
                collector=self.collector_user.profile,
                outcome=OutcomeChoices.MISSED,
                missed_reason=""  # Missing!
            )
            rec_missed_invalid.save()

        # 4. Valid collected record succeeds
        rec_valid = CollectionRecord.objects.create(
            household=self.hh_alpha,
            collector=self.collector_user.profile,
            outcome=OutcomeChoices.COLLECTED,
            is_segregated=True,
            waste_wet=True,
            waste_dry=True,
            segregation_rating=5,
            remarks="Excellent segregation"
        )
        self.assertEqual(rec_valid.village, self.village_a)
        self.assertEqual(rec_valid.ward, self.ward_a)

    def test_api_validate_qr_scenarios(self):
        """FR-28, FR-29, FR-30: Server-side QR verification endpoint."""
        self.client.login(username="collector_alpha", password="password123")

        # 1. Valid QR in collector's village -> 200 OK with household details
        qr_payload = json.dumps({'uid': self.hh_alpha.uid, 'vcode': self.village_a.code})
        res1 = self.client.post(
            reverse('api_collector_validate_qr'),
            data=json.dumps({'qr_data': qr_payload}),
            content_type='application/json'
        )
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertTrue(data1['success'])
        self.assertEqual(data1['household']['head_name'], "Sachin Tendulkar")
        self.assertEqual(data1['household']['house_number'], "100-Century")

        # 2. Inactive household -> 400
        res2 = self.client.post(
            reverse('api_collector_validate_qr'),
            data=json.dumps({'qr_data': self.hh_inactive.uid}),
            content_type='application/json'
        )
        self.assertEqual(res2.status_code, 400)
        self.assertIn("inactive", res2.json()['error'].lower())

        # 3. Cross-village QR (Household from Village Beta) -> 403 Forbidden (FR-29)
        res3 = self.client.post(
            reverse('api_collector_validate_qr'),
            data=json.dumps({'qr_data': self.hh_beta.uid}),
            content_type='application/json'
        )
        self.assertEqual(res3.status_code, 403)
        self.assertIn("cross-village", res3.json()['error'].lower())

        # 4. Unknown UID -> 404
        res4 = self.client.post(
            reverse('api_collector_validate_qr'),
            data=json.dumps({'qr_data': 'HH-NONEXISTENT-9999'}),
            content_type='application/json'
        )
        self.assertEqual(res4.status_code, 404)

    def test_doorstep_browser_form_submission_and_counter(self):
        """FR-31 to FR-38, FR-58, FR-61: Browser form submission and collector daily count."""
        self.client.login(username="collector_alpha", password="password123")

        # Initial doorstep page shows count 0
        get_res = self.client.get(reverse('collector_doorstep'))
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.context['today_count'], 0)

        # Submit Collected Visit via POST
        post_res = self.client.post(reverse('doorstep_submit'), {
            'household_uid': self.hh_alpha.uid,
            'outcome': OutcomeChoices.COLLECTED,
            'is_segregated': 'true',
            'waste_wet': True,
            'waste_dry': True,
            'segregation_rating': 4,
            'remarks': 'Doorstep collection verified'
        })
        self.assertEqual(post_res.status_code, 302)  # PRG redirect

        # Verify record in DB
        self.assertEqual(CollectionRecord.objects.filter(household=self.hh_alpha).count(), 1)
        record = CollectionRecord.objects.first()
        self.assertEqual(record.outcome, OutcomeChoices.COLLECTED)
        self.assertEqual(record.segregation_rating, 4)

        # Verify collector's today count incremented to 1 (FR-61)
        get_res_after = self.client.get(reverse('collector_doorstep'))
        self.assertEqual(get_res_after.context['today_count'], 1)

    def test_api_collector_submission_endpoint(self):
        """FR-51, FR-52, FR-54: REST API endpoint for doorstep collection submission."""
        self.client.login(username="collector_alpha", password="password123")

        # 1. Successful Collected Submission via JSON
        payload = json.dumps({
            'household_uid': self.hh_alpha.uid,
            'outcome': 'COLLECTED',
            'is_segregated': True,
            'waste_wet': True,
            'waste_dry': True,
            'waste_sanitary': False,
            'segregation_rating': 5,
            'remarks': 'API submission test'
        })
        res1 = self.client.post(
            reverse('api_collector_submit'),
            data=payload,
            content_type='application/json'
        )
        self.assertEqual(res1.status_code, 201)
        data1 = res1.json()
        self.assertTrue(data1['success'])
        self.assertEqual(data1['today_total'], 1)

        # 2. Successful Missed Submission via JSON (e.g. Locked)
        payload_missed = json.dumps({
            'household_uid': self.hh_alpha.uid,
            'outcome': 'MISSED',
            'missed_reason': MissedReasonChoices.LOCKED,
            'remarks': 'Gate padlocked'
        })
        res2 = self.client.post(
            reverse('api_collector_submit'),
            data=payload_missed,
            content_type='application/json'
        )
        self.assertEqual(res2.status_code, 201)
        data2 = res2.json()
        self.assertEqual(data2['today_total'], 2)

        # 3. Invalid Submission (Missing required rating for collected visit)
        payload_invalid = json.dumps({
            'household_uid': self.hh_alpha.uid,
            'outcome': 'COLLECTED',
            'is_segregated': True,
            'segregation_rating': None,
        })
        res3 = self.client.post(
            reverse('api_collector_submit'),
            data=payload_invalid,
            content_type='application/json'
        )
        self.assertEqual(res3.status_code, 400)
        self.assertFalse(res3.json()['success'])
