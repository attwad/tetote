from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import sync_playwright
from .models import Brand, Product, Glaze, ProductType, StoreSettings, StoreAnnouncement
from django.urls import reverse
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from django.utils import translation


class IntegrationTests(StaticLiveServerTestCase):
    def setUp(self):
        super().setUp()
        translation.deactivate_all()

        # Set a default store setting
        StoreSettings.objects.get_or_create(sales_paused=False)

        # Journey 1 & 2 Data
        self.brand_bizen = Brand.objects.create(name="Bizen", slug="bizen")
        self.brand_seto = Brand.objects.create(name="Seto", slug="seto")
        self.glaze = Glaze.objects.create(name="Natural", slug="natural")
        self.ptype = ProductType.objects.create(name="Vase", slug="vase")

        self.product = Product.objects.create(
            name="Artisanal Vase",
            slug="artisanal-vase",
            price=15000,
            stock_quantity=10,
            brand=self.brand_bizen,
            glaze=self.glaze,
            product_type=self.ptype,
            stripe_product_id="prod_test",
            stripe_price_id="price_test",
            public=True,
        )

        Product.objects.create(
            name="Bizen Vase",
            slug="bizen-vase",
            price=10000,
            stock_quantity=5,
            brand=self.brand_bizen,
            glaze=self.glaze,
            product_type=self.ptype,
            public=True,
            stripe_product_id="prod_filter_bizen",
            stripe_price_id="price_filter_bizen",
        )
        Product.objects.create(
            name="Seto Vase",
            slug="seto-vase",
            price=12000,
            stock_quantity=5,
            brand=self.brand_seto,
            glaze=self.glaze,
            product_type=self.ptype,
            public=True,
            stripe_product_id="prod_filter_seto",
            stripe_price_id="price_filter_seto",
        )

    def wait_for_js_ready(self, page):
        """
        Wait for window.JS_READY to be true, indicating that the module scripts
        have loaded and executed.
        """
        page.wait_for_function("window.JS_READY === true")

    @patch("shop.views.stripe.checkout.Session.create")
    def test_user_journey_cart_and_checkout(self, mock_stripe_create):
        """
        User Journey 1: Cart and Checkout Navigation
        """
        # Mock Stripe Session
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/pay/test_session"
        mock_stripe_create.return_value = mock_session

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(60000)

            # 2. Visit Home Page
            page.goto(self.live_server_url, wait_until="networkidle")
            self.wait_for_js_ready(page)
            self.assertIn("Tetote", page.title())

            # 3. Go to Product List
            page.click("text=Enter the Shop")
            page.wait_for_url(
                f"**{reverse('shop:product_list')}", wait_until="networkidle"
            )
            self.wait_for_js_ready(page)
            self.assertIn("Artisanal Vase", page.content())

            # 4. View Product Detail
            page.click("text=Artisanal Vase")
            page.wait_for_url(
                f"**{reverse('shop:product_detail', kwargs={'product_slug': self.product.slug})}",
                wait_until="networkidle",
            )
            self.wait_for_js_ready(page)
            self.assertIn("CHF 150.00", page.content())

            # 5. Add to Cart
            # The product-detail script also needs to be ready
            page.wait_for_function('typeof window.addToCart === "function"')
            page.click("button:has-text('Add to Cart')")
            page.wait_for_selector("text=Added to cart")
            # 6. Go to Cart
            page.goto(
                f"{self.live_server_url}{reverse('shop:cart')}",
                wait_until="networkidle",
            )
            self.assertIn("Artisanal Vase", page.content())

            # 7. Proceed to Checkout
            with page.expect_navigation(url="**checkout.stripe.com**", timeout=20000):
                page.click("#checkout-btn")

            self.assertIn("checkout.stripe.com", page.url)
            self.assertTrue(mock_stripe_create.called)
            browser.close()

    def test_user_journey_filtering(self):
        """
        User Journey 2: Shop Filtering
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(60000)

            # 2. Visit Shop
            page.goto(
                f"{self.live_server_url}{reverse('shop:product_list')}",
                wait_until="networkidle",
            )
            self.wait_for_js_ready(page)
            self.assertIn("Bizen Vase", page.content())
            self.assertIn("Seto Vase", page.content())

            # 3. Filter by Bizen
            page.click("#filter-drawer .filter-item:has-text('Bizen')")

            # 4. Verify URL and Visibility
            page.wait_for_url(
                f"**?brand={self.brand_bizen.slug}", wait_until="networkidle"
            )
            self.wait_for_js_ready(page)
            self.assertIn("Bizen Vase", page.content())

            page.wait_for_selector("text=Seto Vase", state="hidden")
            browser.close()

    def test_user_journey_language_switching(self):
        """
        User Journey 3: Language Switching
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(60000)

            page.goto(self.live_server_url, wait_until="networkidle")
            self.wait_for_js_ready(page)
            page.select_option('select[name="language"]', "ja")
            page.wait_for_url(f"{self.live_server_url}/ja/", wait_until="networkidle")
            self.assertIn("/ja/", page.url)
            browser.close()

    def test_user_journey_store_announcement(self):
        """
        User Journey 4: Store Announcement (Global State)
        """
        ann = StoreAnnouncement.objects.create(
            text="Special Holiday Sale: 20% off!", is_active=True
        )

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(60000)
            page.goto(self.live_server_url, wait_until="networkidle")
            self.wait_for_js_ready(page)
            self.assertIn("Special Holiday Sale: 20% off!", page.content())
            self.assertTrue(page.locator(".bg-brand-accent.text-white").is_visible())
            browser.close()

        ann.is_active = False
        ann.save()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(60000)
            page.goto(self.live_server_url, wait_until="networkidle")
            self.wait_for_js_ready(page)
            self.assertNotIn("Special Holiday Sale: 20% off!", page.content())
            self.assertEqual(page.locator(".bg-brand-accent.text-white").count(), 0)
            browser.close()

    def test_user_journey_mobile_navigation(self):
        """
        User Journey 5: Mobile Navigation
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 390, "height": 844},
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1",
            )
            page = context.new_page()
            page.set_default_timeout(60000)

            page.goto(self.live_server_url, wait_until="networkidle")
            self.wait_for_js_ready(page)

            self.assertFalse(page.locator("nav.hidden.md\\:flex").is_visible())
            hamburger = page.locator("button.md\\:hidden").first
            self.assertTrue(hamburger.is_visible())

            # Wait for JS to be fully loaded
            hamburger.click()

            page.wait_for_function(
                '!document.getElementById("mobile-menu-drawer").classList.contains("-translate-x-full")'
            )

            shop_link = page.locator("#mobile-menu-drawer a:has-text('Shop')")
            self.assertTrue(shop_link.is_visible())

            overlay = page.locator("#mobile-menu-overlay")
            overlay.click()

            page.wait_for_function(
                'document.getElementById("mobile-menu-drawer").classList.contains("-translate-x-full")'
            )

            browser.close()

    def test_user_journey_admin_access(self):
        """
        User Journey 6: Admin Access
        """
        User.objects.create_superuser(
            username="admin", password="password123", email="admin@example.com"
        )

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(60000)

            page.goto(
                f"{self.live_server_url}{reverse('shop:admin_help')}",
                wait_until="networkidle",
            )
            self.assertIn("login", page.url)

            page.goto(f"{self.live_server_url}/admin/login/", wait_until="networkidle")
            page.fill('input[name="username"]', "admin")
            page.fill('input[name="password"]', "password123")
            page.click('input[type="submit"]')

            page.goto(
                f"{self.live_server_url}{reverse('shop:admin_help')}",
                wait_until="networkidle",
            )
            self.wait_for_js_ready(page)
            self.assertIn("Admin Documentation", page.content())

            browser.close()

    def test_user_journey_no_product_recommendations(self):
        """
        User Journey 7: No Product Recommendations
        """
        brand_kyoto = Brand.objects.create(name="Kyoto", slug="kyoto")
        p1 = Product.objects.create(
            name="Kyoto Bowl",
            slug="kyoto-bowl",
            price=5000,
            stock_quantity=10,
            brand=brand_kyoto,
            glaze=self.glaze,
            product_type=self.ptype,
            public=True,
            stripe_product_id="prod_k1",
            stripe_price_id="price_k1",
        )
        Product.objects.create(
            name="Kyoto Plate",
            slug="kyoto-plate",
            price=6000,
            stock_quantity=10,
            brand=brand_kyoto,
            glaze=self.glaze,
            product_type=self.ptype,
            public=True,
            stripe_product_id="prod_k2",
            stripe_price_id="price_k2",
        )

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(60000)

            page.goto(
                f"{self.live_server_url}{reverse('shop:product_detail', kwargs={'product_slug': p1.slug})}",
                wait_until="networkidle",
            )
            self.wait_for_js_ready(page)

            self.assertNotIn("Kyoto Plate", page.content())

            browser.close()
