from django.test import TestCase, override_settings
from django.urls import reverse


class ShopDisabledTests(TestCase):
    def test_shop_active_by_default(self):
        # By default shop should be active
        response = self.client.get(reverse("shop:product_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shop/product_list.html")

    @override_settings(SHOP_DISABLED=True)
    def test_shop_disabled_shows_wip(self):
        # When SHOP_DISABLED=True, home page should show WIP
        response = self.client.get(reverse("shop:product_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Coming Soon")
        # Shop and Cart links should still be in the navigation
        self.assertContains(response, reverse("shop:product_list"))
        self.assertContains(response, reverse("shop:cart"))

    @override_settings(SHOP_DISABLED=True)
    def test_shop_detail_renders_wip(self):
        # When SHOP_DISABLED=True, product detail should render WIP directly
        response = self.client.get(
            reverse("shop:product_detail", kwargs={"product_slug": "some-slug"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Coming Soon")

    @override_settings(SHOP_DISABLED=True)
    def test_cart_renders_wip(self):
        # When SHOP_DISABLED=True, cart should render WIP directly
        response = self.client.get(reverse("shop:cart"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Coming Soon")

    @override_settings(SHOP_DISABLED=True)
    def test_static_pages_remain_accessible(self):
        # Static pages like 'about-us' should remain accessible
        response = self.client.get(reverse("shop:about_us"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shop/about_us.html")

    @override_settings(SHOP_DISABLED=True)
    def test_blog_remains_accessible(self):
        # Blog should remain accessible
        response = self.client.get(reverse("blog:post_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "blog/post_list.html")
