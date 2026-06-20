from django.test import TestCase
from django.urls import reverse
from django.utils import translation


class ContactPageTests(TestCase):
    def test_contact_page_en(self):
        # Test contact page in English (default)
        with translation.override("en"):
            url = reverse("shop:contact")
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(
                response,
                "If you have any questions or inquiries, please feel free to reach out to us.",
            )
            self.assertContains(
                response, "We will get back to you as soon as possible."
            )
            self.assertContains(response, "mailto:info@tetote.ch")
            self.assertContains(response, "https://www.instagram.com/tetote.ch/")
            self.assertContains(response, "info@tetote.ch")
            self.assertContains(response, "tetote.ch")
            self.assertContains(response, "Operating Hours (for Shipping):")
            self.assertContains(response, "Mon-Fri")
            self.assertContains(response, "9:00-18:00")
            self.assertContains(response, "Sat, Sun, & Public Holidays")
            self.assertContains(response, "closed")
            self.assertContains(response, "/blog/business-calendar-2026/")
            self.assertContains(response, "our business calendar 2026")

    def test_contact_page_de(self):
        # Test contact page in German
        with translation.override("de"):
            url = reverse("shop:contact")
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(
                response,
                "Wenn Sie Fragen oder Anfragen haben, wenden Sie sich bitte an uns.",
            )
            self.assertContains(
                response, "Wir werden uns so schnell wie möglich bei Ihnen melden."
            )
            self.assertContains(response, "E-Mail")
            self.assertContains(response, "Mo–Fr")
            self.assertContains(response, "Sa, So & Feiertage")
            self.assertContains(response, "geschlossen")
            self.assertContains(response, "/de/blog/business-calendar-2026/")
            self.assertContains(response, "Geschäftskalender 2026")

    def test_contact_page_fr(self):
        # Test contact page in French
        with translation.override("fr"):
            url = reverse("shop:contact")
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(
                response,
                "Si vous avez des questions ou des demandes, n'hésitez pas à nous contacter.",
            )
            self.assertContains(response, "Nous vous répondrons dès que possible.")
            self.assertContains(response, "E-mail")
            self.assertContains(response, "Lun-Ven")
            self.assertContains(response, "Sam, Dim & Jours Fériés")
            self.assertContains(response, "fermé")
            self.assertContains(response, "/fr/blog/business-calendar-2026/")
            self.assertContains(response, "calendrier des jours ouvrables 2026")

    def test_contact_page_ja(self):
        # Test contact page in Japanese
        with translation.override("ja"):
            url = reverse("shop:contact")
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(
                response,
                "ご質問やご相談がございましたら、お気軽にお問い合わせください。",
            )
            self.assertContains(response, "なるべく早く返信させていただきます。")
            self.assertContains(response, "メール")
            self.assertContains(response, "月-金")
            self.assertContains(response, "土・日・祝日")
            self.assertContains(response, "定休日")
            self.assertContains(response, "/ja/blog/business-calendar-2026/")
            self.assertContains(response, "営業カレンダー")
