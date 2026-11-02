import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Household
from .qr_service import generate_household_qr_payload
from governance.models import Village, Ward
from accounts.models import UserProfile, RoleChoices

class HouseholdsPhase3Tests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Setup Village Alpha
        self.village_a = Village.objects.create(
            code="VIL-ALPHA-01",
            name="Alpha Gram Panchayat",
            district="Pune"
        )
        self.ward_a1 = Ward.objects.create(village=self.village_a, ward_number="Ward 01", ward_name="East")
        self.ward_a2 = Ward.objects.create(village=self.village_a, ward_number="Ward 02", ward_name="West")

        # 2. Setup Village Beta
        self.village_b = Village.objects.create(
            code="VIL-BETA-02",
            name="Beta Gram Panchayat",
            district="Nashik"
        )
        self.ward_b1 = Ward.objects.create(village=self.village_b, ward_number="Ward 01", ward_name="Central")

        # 3. Manager for Village Alpha
        self.manager_a = User.objects.create_user(username="mgr_alpha", password="password123")
        self.manager_a.profile.role = RoleChoices.VILLAGE_MANAGER
        self.manager_a.profile.village = self.village_a
        self.manager_a.profile.save()

        # 4. Manager for Village Beta
        self.manager_b = User.objects.create_user(username="mgr_beta", password="password123")
        self.manager_b.profile.role = RoleChoices.VILLAGE_MANAGER
        self.manager_b.profile.village = self.village_b
        self.manager_b.profile.save()

        # 5. Base Household in Village Alpha
        self.hh1 = Household.objects.create(
            village=self.village_a,
            ward=self.ward_a1,
            head_name="Sunil Gavaskar",
            house_number="10-A",
            phone_number="9876500001"
        )

    def test_household_auto_uid_and_qr_generation(self):
        """FR-17, FR-23, FR-24: Auto UID generation, QR PNG creation, and payload privacy."""
        self.assertTrue(self.hh1.uid.startswith("HH-VILALP-W01-"))
        self.assertIsNotNone(self.hh1.qr_code_image)
        self.assertTrue(self.hh1.qr_code_image.name.endswith(".png"))

        # Verify QR payload contains ZERO resident PII
        payload_str = generate_household_qr_payload(self.hh1)
        payload = json.loads(payload_str)
        self.assertEqual(payload['uid'], self.hh1.uid)
        self.assertEqual(payload['vcode'], self.village_a.code)
        self.assertNotIn("Sunil Gavaskar", payload_str)
        self.assertNotIn("9876500001", payload_str)

    def test_household_cross_village_ward_assignment_prevented(self):
        """FR-21: Household cannot be registered with a ward outside its village."""
        with self.assertRaises(ValidationError):
            hh_invalid = Household(
                village=self.village_a,
                ward=self.ward_b1,  # Ward from Village Beta!
                head_name="Invalid Household",
                house_number="99"
            )
            hh_invalid.save()

    def test_manager_dashboard_rendering(self):
        """FR-14 to FR-20: Manager views dashboard scoped strictly to their village."""
        self.client.login(username="mgr_alpha", password="password123")
        response = self.client.get(reverse('manager_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'households/manager_dashboard.html')
        self.assertContains(response, "Alpha Gram Panchayat")
        self.assertEqual(response.context['total_households'], 1)

    def test_household_registration_form_with_resident_account(self):
        """FR-16, FR-18: Manager registers household and provisions resident portal account."""
        self.client.login(username="mgr_alpha", password="password123")
        response = self.client.post(reverse('household_create'), {
            'head_name': 'Kapil Dev',
            'house_number': '83-WorldCup',
            'ward': self.ward_a2.id,
            'street_address': 'Champions Lane',
            'phone_number': '9876500083',
            'create_resident_account': True,
            'resident_username': 'resident_kapil',
            'resident_password': 'kapilpassword123',
        })
        self.assertEqual(response.status_code, 302)

        # Verify household saved and linked to new user
        new_hh = Household.objects.get(head_name='Kapil Dev')
        self.assertEqual(new_hh.house_number, '83-WorldCup')
        self.assertEqual(new_hh.ward, self.ward_a2)
        self.assertIsNotNone(new_hh.resident_user)
        self.assertEqual(new_hh.resident_user.username, 'resident_kapil')
        self.assertEqual(new_hh.resident_user.profile.role, RoleChoices.HOUSEHOLD)

    def test_household_search_and_ward_filter(self):
        """FR-20: Search by name/house number and filter by ward."""
        self.client.login(username="mgr_alpha", password="password123")

        # 1. Search by name query
        res_search = self.client.get(reverse('household_list') + '?q=Sunil')
        self.assertEqual(res_search.status_code, 200)
        self.assertContains(res_search, "Sunil Gavaskar")

        # 2. Filter by ward_a1
        res_ward = self.client.get(reverse('household_list') + f'?ward={self.ward_a1.id}')
        self.assertEqual(res_ward.status_code, 200)
        self.assertContains(res_ward, "Sunil Gavaskar")

        # 3. Filter by ward_a2 (empty for now)
        res_ward2 = self.client.get(reverse('household_list') + f'?ward={self.ward_a2.id}')
        self.assertEqual(res_ward2.status_code, 200)
        self.assertEqual(res_ward2.context['total_count'], 0)

    def test_collector_creation_by_manager(self):
        """FR-14, FR-15: Manager provisions collector for their village and toggles active status."""
        self.client.login(username="mgr_alpha", password="password123")

        # Create collector
        response = self.client.post(reverse('collector_manage'), {
            'username': 'collector_alpha_1',
            'first_name': 'Santosh',
            'last_name': 'Rathod',
            'phone_number': '9988771122',
            'password': 'collectorpass123',
        })
        self.assertEqual(response.status_code, 302)

        col_user = User.objects.get(username='collector_alpha_1')
        self.assertEqual(col_user.profile.role, RoleChoices.WASTE_COLLECTOR)
        self.assertEqual(col_user.profile.village, self.village_a)
        self.assertTrue(col_user.is_active)

        # Toggle status to deactivate
        self.client.post(reverse('collector_toggle_status', kwargs={'collector_user_id': col_user.id}))
        col_user.refresh_from_db()
        self.assertFalse(col_user.is_active)

    def test_cross_village_isolation_for_managers(self):
        """FR-06: Manager B cannot edit or access households in Village A."""
        self.client.login(username="mgr_beta", password="password123")
        # Attempt to edit hh1 which belongs to Village Alpha
        response = self.client.get(reverse('household_edit', kwargs={'household_id': self.hh1.id}))
        self.assertEqual(response.status_code, 404)

    def test_api_households_list_and_create(self):
        """FR-51, FR-52, FR-54: REST API endpoints for household operations."""
        self.client.login(username="mgr_alpha", password="password123")

        # 1. GET list of households
        res_get = self.client.get(reverse('api_households'))
        self.assertEqual(res_get.status_code, 200)
        data = res_get.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 1)

        # 2. POST create household via JSON
        payload = json.dumps({
            'head_name': 'Rahul Dravid',
            'house_number': 'Wall-19',
            'ward_id': self.ward_a1.id,
            'phone_number': '9876543219',
        })
        res_post = self.client.post(reverse('api_households'), data=payload, content_type='application/json')
        self.assertEqual(res_post.status_code, 201)
        post_data = res_post.json()
        self.assertTrue(post_data['household']['uid'].startswith("HH-VILALP-W01-"))

    def test_api_household_qr_endpoint(self):
        """FR-25, FR-26: Fetch QR image and payload via JSON API."""
        self.client.login(username="mgr_alpha", password="password123")
        res = self.client.get(reverse('api_household_qr', kwargs={'uid': self.hh1.uid}))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['household']['uid'], self.hh1.uid)
        self.assertIn('vcode', data['household']['qr_payload'])
