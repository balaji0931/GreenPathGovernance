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

    def test_seed_data_command(self):
        """Phase 6: Verify seed_data command runs cleanly and provisions complete environment."""
        call_command('seed_data')

        # Assert Super Admin created
        self.assertTrue(User.objects.filter(username="superadmin").exists())

        # Assert Villages created
        self.assertTrue(Village.objects.filter(code="VIL-SHIVAJI-01").exists())
        self.assertTrue(Village.objects.filter(code="VIL-GANESH-02").exists())

        # Assert Households created
        self.assertGreaterEqual(Household.objects.count(), 15)

        # Assert Collection Records created
        self.assertGreaterEqual(CollectionRecord.objects.count(), 5)
