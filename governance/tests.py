import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.db import IntegrityError

from .models import Village, Ward
from accounts.models import UserProfile, RoleChoices

class GovernancePhase2Tests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Super Admin
        self.superadmin = User.objects.create_superuser(
            username="superadmin",
            password="adminpassword123",
            email="admin@greenpath.gov.in"
        )

        # 2. Base Village
        self.village = Village.objects.create(
            code="VIL-SHIVAJI-01",
            name="Shivaji Gram Panchayat",
            district="Pune",
            state="Maharashtra"
        )

        # 3. Ward 01
        self.ward_1 = Ward.objects.create(
            village=self.village,
            ward_number="Ward 01",
            ward_name="North Bazaar"
        )

        # 4. Standard Manager
        self.manager_user = User.objects.create_user(
            username="manager_shivaji",
            password="managerpassword123"
        )
        self.manager_user.profile.role = RoleChoices.VILLAGE_MANAGER
        self.manager_user.profile.village = self.village
        self.manager_user.profile.save()

        # 5. Standard Resident
        self.resident_user = User.objects.create_user(
            username="resident_user",
            password="residentpassword123"
        )
        self.resident_user.profile.role = RoleChoices.HOUSEHOLD
        self.resident_user.profile.save()

    def test_village_code_uniqueness(self):
        """FR-09: Village code must be unique across the platform."""
        with self.assertRaises(IntegrityError):
            Village.objects.create(
                code="VIL-SHIVAJI-01",
                name="Duplicate Code Panchayat"
            )

    def test_ward_uniqueness_per_village(self):
        """FR-10: Ward number must be unique within the same Village."""
        with self.assertRaises(IntegrityError):
            Ward.objects.create(
                village=self.village,
                ward_number="Ward 01",
                ward_name="Duplicate Ward"
            )

    def test_superadmin_dashboard_rendering(self):
        """FR-12: Super Admin dashboard renders metrics and village/manager lists."""
        self.client.login(username="superadmin", password="adminpassword123")
        response = self.client.get(reverse('superadmin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'governance/superadmin_dashboard.html')
        self.assertContains(response, "Shivaji Gram Panchayat")
        self.assertContains(response, "manager_shivaji")
        self.assertEqual(response.context['total_villages'], 1)
        self.assertEqual(response.context['total_wards'], 1)

    def test_village_creation_via_browser_form(self):
        """FR-09, FR-58: Super Admin creates village via HTML form with PRG redirect."""
        self.client.login(username="superadmin", password="adminpassword123")
        response = self.client.post(reverse('village_create'), {
            'code': 'VIL-RAMPUR-02',
            'name': 'Rampur Gram Panchayat',
            'district': 'Nashik',
            'state': 'Maharashtra',
            'is_active': True,
        })
        self.assertEqual(response.status_code, 302)
        new_village = Village.objects.get(code='VIL-RAMPUR-02')
        self.assertEqual(new_village.name, 'Rampur Gram Panchayat')

    def test_ward_creation_via_browser_form(self):
        """FR-10, FR-58: Super Admin adds a ward to a village."""
        self.client.login(username="superadmin", password="adminpassword123")
        response = self.client.post(reverse('ward_create', kwargs={'village_id': self.village.id}), {
            'ward_number': 'Ward 02',
            'ward_name': 'South Riverbank',
            'is_active': True,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Ward.objects.filter(village=self.village, ward_number='Ward 02').exists())

    def test_manager_account_creation_and_assignment(self):
        """FR-11: Super Admin creates a Village Manager account and assigns it to a village."""
        self.client.login(username="superadmin", password="adminpassword123")
        response = self.client.post(reverse('manager_create'), {
            'username': 'mgr_new_panchayat',
            'first_name': 'Suresh',
            'last_name': 'Jadhav',
            'email': 'suresh@panchayat.org',
            'phone_number': '+91 9123456789',
            'password': 'initialpassword123',
            'village': self.village.id,
        })
        self.assertEqual(response.status_code, 302)
        new_mgr = User.objects.get(username='mgr_new_panchayat')
        self.assertEqual(new_mgr.profile.role, RoleChoices.VILLAGE_MANAGER)
        self.assertEqual(new_mgr.profile.village, self.village)

    def test_non_superadmin_forbidden_from_governance(self):
        """FR-13: Non-Super Admin accounts must receive HTTP 403 on governance views."""
        # 1. Test with Village Manager
        self.client.login(username="manager_shivaji", password="managerpassword123")
        res1 = self.client.get(reverse('superadmin_dashboard'))
        self.assertEqual(res1.status_code, 403)

        res2 = self.client.get(reverse('village_create'))
        self.assertEqual(res2.status_code, 403)

        # 2. Test with Household Resident
        self.client.login(username="resident_user", password="residentpassword123")
        res3 = self.client.get(reverse('superadmin_dashboard'))
        self.assertEqual(res3.status_code, 403)

    def test_api_villages_list_and_create(self):
        """FR-51, FR-52, FR-54: REST API endpoints for village operations."""
        self.client.login(username="superadmin", password="adminpassword123")

        # 1. GET list of villages
        res_get = self.client.get(reverse('api_villages'))
        self.assertEqual(res_get.status_code, 200)
        data = res_get.json()
        self.assertTrue(data['success'])
        self.assertGreaterEqual(data['count'], 1)

        # 2. POST create new village with wards via JSON
        payload = json.dumps({
            'code': 'VIL-GANESH-03',
            'name': 'Ganesh Gram Panchayat',
            'district': 'Nagpur',
            'state': 'Maharashtra',
            'wards': [
                {'number': 'Ward 01', 'name': 'Temple Sector'},
                {'number': 'Ward 02', 'name': 'Market Yard'}
            ]
        })
        res_post = self.client.post(reverse('api_villages'), data=payload, content_type='application/json')
        self.assertEqual(res_post.status_code, 201)
        created_village = Village.objects.get(code='VIL-GANESH-03')
        self.assertEqual(created_village.wards.count(), 2)

    def test_api_managers_list_and_create(self):
        """FR-51, FR-52, FR-54: REST API endpoints for manager provisioning."""
        self.client.login(username="superadmin", password="adminpassword123")

        # 1. GET list of managers
        res_get = self.client.get(reverse('api_managers'))
        self.assertEqual(res_get.status_code, 200)
        data = res_get.json()
        self.assertTrue(data['success'])

        # 2. POST create manager via JSON
        payload = json.dumps({
            'username': 'mgr_ganesh_api',
            'password': 'password12345',
            'first_name': 'Anita',
            'last_name': 'Deshmukh',
            'village_id': self.village.id,
            'phone_number': '+91 9988776655'
        })
        res_post = self.client.post(reverse('api_managers'), data=payload, content_type='application/json')
        self.assertEqual(res_post.status_code, 201)
        created_mgr = User.objects.get(username='mgr_ganesh_api')
        self.assertEqual(created_mgr.profile.role, RoleChoices.VILLAGE_MANAGER)
        self.assertEqual(created_mgr.profile.village, self.village)
