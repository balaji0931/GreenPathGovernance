import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.http import HttpResponse

from .models import UserProfile, RoleChoices
from .decorators import role_required, village_access_required
from governance.models import Village, Ward

# Dummy view for testing decorators
@role_required([RoleChoices.VILLAGE_MANAGER])
def dummy_manager_view(request):
    return HttpResponse("Manager Access Granted")

@role_required([RoleChoices.SUPER_ADMIN])
def dummy_admin_view(request):
    return HttpResponse("Admin Access Granted")

@village_access_required
def dummy_village_view(request, village_id=None):
    return HttpResponse(f"Village Access Granted: {village_id}")


class AccountsAuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create two test villages
        self.village_a = Village.objects.create(code="VIL-A", name="Village Alpha")
        self.village_b = Village.objects.create(code="VIL-B", name="Village Beta")

        # 1. Super Admin User
        self.admin_user = User.objects.create_superuser(
            username="superadmin",
            password="adminpassword123",
            email="admin@greenpath.gov.in"
        )

        # 2. Village Manager User (Assigned to Village A)
        self.manager_user = User.objects.create_user(
            username="manager_alpha",
            password="managerpassword123"
        )
        self.manager_user.profile.role = RoleChoices.VILLAGE_MANAGER
        self.manager_user.profile.village = self.village_a
        self.manager_user.profile.save()

        # 3. Waste Collector User (Assigned to Village A)
        self.collector_user = User.objects.create_user(
            username="collector_alpha",
            password="collectorpassword123"
        )
        self.collector_user.profile.role = RoleChoices.WASTE_COLLECTOR
        self.collector_user.profile.village = self.village_a
        self.collector_user.profile.save()

        # 4. Household Resident User
        self.resident_user = User.objects.create_user(
            username="resident_alpha",
            password="residentpassword123"
        )
        self.resident_user.profile.role = RoleChoices.HOUSEHOLD
        self.resident_user.profile.save()

    def test_user_profile_auto_provisioning_and_roles(self):
        """FR-02: Verify UserProfile auto-provisioning and role flags."""
        self.assertEqual(self.admin_user.profile.role, RoleChoices.SUPER_ADMIN)
        self.assertTrue(self.admin_user.profile.is_super_admin)

        self.assertEqual(self.manager_user.profile.role, RoleChoices.VILLAGE_MANAGER)
        self.assertTrue(self.manager_user.profile.is_village_manager)
        self.assertEqual(self.manager_user.profile.village, self.village_a)

        self.assertEqual(self.collector_user.profile.role, RoleChoices.WASTE_COLLECTOR)
        self.assertTrue(self.collector_user.profile.is_waste_collector)

        self.assertEqual(self.resident_user.profile.role, RoleChoices.HOUSEHOLD)
        self.assertTrue(self.resident_user.profile.is_household)

    def test_browser_login_with_invalid_credentials(self):
        """FR-01: Invalid credentials should fail without creating session."""
        response = self.client.post(reverse('login'), {
            'username': 'manager_alpha',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')
        self.assertFalse(response.context['user'].is_authenticated)

    def test_role_based_redirection_on_login(self):
        """FR-04: Authenticated login routes user to their designated dashboard."""
        # 1. Super Admin
        self.client.login(username="superadmin", password="adminpassword123")
        response = self.client.get(reverse('role_redirect'), follow=False)
        self.assertRedirects(response, reverse('superadmin_dashboard'))
        self.client.logout()

        # 2. Village Manager
        self.client.login(username="manager_alpha", password="managerpassword123")
        response = self.client.get(reverse('role_redirect'), follow=False)
        self.assertRedirects(response, reverse('manager_dashboard'))
        self.client.logout()

        # 3. Waste Collector
        self.client.login(username="collector_alpha", password="collectorpassword123")
        response = self.client.get(reverse('role_redirect'), follow=False)
        self.assertRedirects(response, reverse('collector_doorstep'))
        self.client.logout()

        # 4. Household Resident
        self.client.login(username="resident_alpha", password="residentpassword123")
        response = self.client.get(reverse('role_redirect'), follow=False)
        self.assertRedirects(response, reverse('household_dashboard'))
        self.client.logout()

    def test_logout_terminates_session(self):
        """FR-07: Logout action clears the user session and redirects to landing."""
        self.client.login(username="manager_alpha", password="managerpassword123")
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('landing'))

        # Check subsequent status
        status_resp = self.client.get(reverse('accounts_api_me'))
        self.assertEqual(status_resp.status_code, 401)

    def test_role_required_decorator_enforcement(self):
        """FR-05: Verify role-based authorization decorator guards."""
        from django.test import RequestFactory
        rf = RequestFactory()

        # 1. Anonymous user -> Redirects to login
        from django.contrib.auth.models import AnonymousUser
        req = rf.get('/protected/manager/')
        req.user = AnonymousUser()
        resp = dummy_manager_view(req)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp.url)

        # 2. Resident trying to access manager view -> 403
        req.user = self.resident_user
        resp = dummy_manager_view(req)
        self.assertEqual(resp.status_code, 403)

        # 3. Authorized manager -> 200
        req.user = self.manager_user
        resp = dummy_manager_view(req)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Manager Access Granted")

    def test_village_boundary_access_guard(self):
        """FR-06: Manager cannot access a different village's data."""
        from django.test import RequestFactory
        rf = RequestFactory()

        # Manager is assigned to village_a (id)
        # Attempt to access village_b
        req = rf.get(f"/village/{self.village_b.id}/")
        req.user = self.manager_user
        resp = dummy_village_view(req, village_id=self.village_b.id)
        self.assertEqual(resp.status_code, 403)

        # Accessing own village_a -> 200
        req = rf.get(f"/village/{self.village_a.id}/")
        req.user = self.manager_user
        resp = dummy_village_view(req, village_id=self.village_a.id)
        self.assertEqual(resp.status_code, 200)

    def test_rest_api_auth_login_me_logout_cycle(self):
        """FR-51, FR-53, FR-54: REST-style JSON API authentication flow."""
        # 1. Successful API Login
        payload = json.dumps({'username': 'manager_alpha', 'password': 'managerpassword123'})
        response = self.client.post(
            reverse('api_auth_login'),
            data=payload,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['role'], 'VILLAGE_MANAGER')
        self.assertEqual(data['user']['village']['code'], 'VIL-A')

        # 2. Check /api/v1/auth/me/
        me_resp = self.client.get(reverse('api_auth_me'))
        self.assertEqual(me_resp.status_code, 200)
        me_data = me_resp.json()
        self.assertEqual(me_data['user']['username'], 'manager_alpha')

        # 3. API Logout
        logout_resp = self.client.post(reverse('api_auth_logout'))
        self.assertEqual(logout_resp.status_code, 200)

        # 4. Check /api/v1/auth/me/ after logout -> 401
        me_after_resp = self.client.get(reverse('api_auth_me'))
        self.assertEqual(me_after_resp.status_code, 401)
