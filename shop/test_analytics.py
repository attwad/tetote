from django.test import TestCase, override_settings
from django.urls import reverse


class AnalyticsTests(TestCase):
    @override_settings(UMAMI_WEBSITE_ID="test-id-123")
    def test_umami_script_present_with_id(self):
        url = reverse("shop:product_list")
        response = self.client.get(url)
        self.assertContains(
            response,
            '<script defer src="https://cloud.umami.is/script.js" data-website-id="test-id-123"></script>',
            html=True,
        )

    @override_settings(UMAMI_WEBSITE_ID="")
    def test_umami_script_absent_without_id(self):
        url = reverse("shop:product_list")
        response = self.client.get(url)
        self.assertNotContains(response, "https://cloud.umami.is/script.js")

    @override_settings(UMAMI_WEBSITE_ID=None)
    def test_umami_script_absent_with_none_id(self):
        url = reverse("shop:product_list")
        response = self.client.get(url)
        self.assertNotContains(response, "https://cloud.umami.is/script.js")
