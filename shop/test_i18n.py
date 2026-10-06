from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from shop.models import Brand


class LanguageSwitcherTests(TestCase):
    def test_language_switcher_presence(self):
        url = reverse("shop:product_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check for desktop switcher (uppercase current language)
        self.assertContains(response, "EN")
        # Check for form action
        self.assertContains(response, reverse("set_language"))
        # Check for other languages in the switcher
        for lang_code, _lang_name in [
            ("de", "German"),
            ("fr", "French"),
            ("ja", "Japanese"),
        ]:
            self.assertContains(response, lang_code.upper())

    def test_language_switch_en_to_fr(self):
        # When prefix_default_language=False, English is / and French is /fr/
        url = "/i18n/setlang/"
        data = {"language": "fr", "next": "/"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        # Django's set_language should use translate_url to change / to /fr/
        self.assertEqual(response.url, "/fr/")

    def test_language_switch_fr_to_en(self):
        url = "/fr/i18n/setlang/"
        data = {"language": "en", "next": "/fr/"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        # Django's set_language should use translate_url to change /fr/ to /
        self.assertEqual(response.url, "/")


class TranslationTests(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(
            name_en="Bizen English", name_fr="Bizen French", slug="bizen"
        )

    def test_brand_translation(self):
        with translation.override("en"):
            self.assertEqual(self.brand.name, "Bizen English")

        with translation.override("fr"):
            self.assertEqual(self.brand.name, "Bizen French")
