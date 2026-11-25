from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
from django.core.management import call_command
from django.contrib.auth.models import User
from governance.models import Village
from households.models import Household
from waste_collections.models import CollectionRecord

class CorePublicPagesTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_landing_page_renders_successfully(self):
        """FR-01/Scope: Verify public landing page renders with HTTP 200 and required elements."""
        response = self.client.get(reverse('landing'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'base.html')
        self.assertTemplateUsed(response, 'core/landing.html')
        self.assertContains(response, 'GreenPath')
        self.assertContains(response, 'Door-to-Door')
        self.assertContains(response, 'Waste Segregation Guide')
        self.assertContains(response, '₹5 / household')

    def test_product_page_renders_successfully(self):
        """Verify product showcase renders architecture modules and features."""
        response = self.client.get(reverse('product'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'base.html')
        self.assertTemplateUsed(response, 'core/product.html')
        self.assertContains(response, 'Batch Cryptographic Doorstep QR Engine')
        self.assertContains(response, 'Zero-Hardware Mobile Collector Web PWA')
        self.assertContains(response, '3-Way Segregation Auditing')

    def test_about_page_renders_successfully(self):
        """Verify about page renders mission, civic governance values, and stack."""
        response = self.client.get(reverse('about'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'base.html')
        self.assertTemplateUsed(response, 'core/about.html')
        self.assertContains(response, 'Our Civic Purpose')
        self.assertContains(response, 'Privacy by Design')
        self.assertContains(response, 'contact@greenpath.com')

    def test_pricing_page_renders_successfully(self):
        """Verify pricing page accurately reflects ₹0 for households and ₹5/HH with min ₹500 for orgs."""
        response = self.client.get(reverse('pricing'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'base.html')
        self.assertTemplateUsed(response, 'core/pricing.html')
        self.assertContains(response, 'Direct Households Pay ₹0')
        self.assertContains(response, '₹5')
        self.assertContains(response, '₹500')
        self.assertContains(response, 'contact@greenpath.com')

    def test_contact_page_renders_and_post_submits(self):
        """Verify contact page renders official contact@greenpath.com and accepts inquiry submissions."""
        # GET
        response = self.client.get(reverse('contact'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'base.html')
        self.assertTemplateUsed(response, 'core/contact.html')
        self.assertContains(response, 'contact@greenpath.com')

        # POST valid
        post_response = self.client.post(reverse('contact'), {
            'name': 'Sarpanch Ramesh',
            'org_name': 'Shivaji Gram Panchayat',
            'email': 'sarpanch@shivajigp.org',
            'phone': '9876543210',
            'households': '500-1500',
            'message': 'We want to deploy GreenPath across all 4 wards.'
        }, follow=True)
        self.assertEqual(post_response.status_code, 200)
        self.assertContains(post_response, 'Thank you, Sarpanch Ramesh!')

    def test_no_signup_buttons_on_public_pages(self):
        """Verify strict rule: no signup button or signup link anywhere on public pages."""
        public_urls = [
            reverse('landing'),
            reverse('product'),
            reverse('about'),
            reverse('pricing'),
            reverse('contact'),
            reverse('login'),
        ]
        for url in public_urls:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200)
            content = res.content.decode('utf-8')
            # Check that there is no button or link saying Sign Up / Create Account / Register
            self.assertNotRegex(content, r'>\s*Sign\s*Up\s*<', f"Found 'Sign Up' text on {url}")
            self.assertNotRegex(content, r'>\s*Create\s*(an)?\s*Account\s*<', f"Found 'Create Account' on {url}")

    def test_segregation_guide_renders_successfully(self):
        """Scope: Verify educational segregation advisory renders 3 streams and ratings."""
        response = self.client.get(reverse('segregation_guide'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/segregation_guide.html')
        self.assertContains(response, 'Wet / Organic Waste')
        self.assertContains(response, 'Dry / Recyclables')
        self.assertContains(response, 'Sanitary')
        self.assertContains(response, 'Hazardous')
        self.assertContains(response, 'Segregation Rating')

    def test_timezone_configuration(self):
        """SRS Section 2.5: Verify project timezone is configured for India (Asia/Kolkata)."""
        self.assertEqual(settings.TIME_ZONE, 'Asia/Kolkata')

    def test_custom_404_page(self):
        """FR-60: Verify custom 404 error page renders without exposing debug internals."""
        response = self.client.get('/non-existent-route-for-testing/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, 'errors/404.html')
        self.assertContains(response, 'Page Not Found', status_code=404)

    def test_custom_error_templates_exist_and_render(self):
        """FR-60: Verify custom 400, 403, and 500 error views render cleanly."""
        from core.views import handler400, handler403, handler500
        from django.test import RequestFactory

        rf = RequestFactory()
        req = rf.get('/')

        res400 = handler400(req)
        self.assertEqual(res400.status_code, 400)
        self.assertIn(b"Bad Request", res400.content)

        res403 = handler403(req)
        self.assertEqual(res403.status_code, 403)
        self.assertIn(b"Access Restricted", res403.content)

        res500 = handler500(req)
        self.assertEqual(res500.status_code, 500)
        self.assertIn(b"System Unavailable", res500.content)

    def test_admin_and_auto_assigned_ids_convention(self):
        """Verify ADMIN user, auto village ID (V001), manager ID (V001-M1), collector ID (V001-C1), household ID (V001-H1)."""
        call_command('seed_data')

        # Check ADMIN login
        login_success = self.client.login(username="ADMIN", password="Admin123@")
        self.assertTrue(login_success, "ADMIN user should log in with Admin123@")

        # Check village V001
        vil = Village.objects.filter(code="V001").first()
        self.assertIsNotNone(vil, "Village V001 should exist")

        # Check manager V001-M1
        mgr = User.objects.filter(username="V001-M1").first()
        self.assertIsNotNone(mgr, "Manager V001-M1 should exist")
        self.assertTrue(self.client.login(username="V001-M1", password="Manager123@"))

        # Check collector V001-C1
        col = User.objects.filter(username="V001-C1").first()
        self.assertIsNotNone(col, "Collector V001-C1 should exist")
        self.assertTrue(self.client.login(username="V001-C1", password="Collector123@"))

        # Check household V001-H1
        hh = Household.objects.filter(uid="V001-H1").first()
        self.assertIsNotNone(hh, "Household V001-H1 should exist")
        self.assertTrue(self.client.login(username="V001-H1", password="Resident123@"))
