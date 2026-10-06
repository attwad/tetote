from unittest.mock import MagicMock, PropertyMock, patch

from django.contrib.admin.sites import AdminSite
from django.core.files.base import ContentFile
from django.test import TestCase

from shop.admin import (
    CarouselImageAdmin,
    ProductAdmin,
    ProductImageInline,
    StoreSettingsAdmin,
)
from shop.models import (
    Brand,
    CarouselImage,
    Product,
    ProductImage,
    StoreSettings,
)


class MockObject(dict):
    def __getattr__(self, name):
        if name in self:
            return self[name]
        raise AttributeError(name)


class ProductAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = ProductAdmin(Product, self.site)
        self.brand = Brand.objects.create(name="Bizen", slug="bizen")
        self.product = Product.objects.create(
            stripe_product_id="prod_admin_test",
            stripe_price_id="price_admin_test",
            name="Admin Product",
            slug="admin-prod",
            price=5000,
            brand=self.brand,
            public=True,
        )

    @patch("stripe.Product.modify")
    def test_save_related_syncs_only_first_image_to_stripe(self, mock_modify):
        # Add gallery images
        ProductImage.objects.create(
            product=self.product, url="http://test.com/main.jpg", order=0
        )
        ProductImage.objects.create(
            product=self.product, url="http://test.com/gallery.jpg", order=1
        )

        mock_form = MagicMock()
        mock_form.instance = self.product
        mock_formsets = []
        mock_request = MagicMock()

        self.admin.save_related(mock_request, mock_form, mock_formsets, change=True)

        expected_images = ["http://test.com/main.jpg"]
        mock_modify.assert_called_once_with(
            "prod_admin_test",
            images=expected_images,
        )

    @patch("stripe.Product.modify")
    @patch("stripe.FileLink.create")
    @patch("stripe.File.create")
    @patch("shop.admin.open", create=True)
    def test_save_related_uploads_first_image_to_stripe_and_keeps_local(
        self,
        mock_open,
        mock_file_create,
        mock_file_link_create,
        mock_modify,
    ):
        img = ProductImage.objects.create(
            product=self.product,
            image_file="product_images/test.jpg",
            order=0,
        )

        mock_form = MagicMock()
        mock_form.instance = self.product
        mock_request = MagicMock()

        mock_file_create.return_value = MockObject({"id": "file_123"})
        mock_file_link_create.return_value = MockObject(
            {"url": "https://files.stripe.com/test.jpg"}
        )

        with patch(
            "django.db.models.fields.files.FieldFile.path", new_callable=PropertyMock
        ) as mock_path:
            mock_path.return_value = "/fake/path/test.jpg"

            self.admin.save_related(mock_request, mock_form, [], change=True)

            mock_file_create.assert_called_once()
            img.refresh_from_db()
            self.assertEqual(img.url, "https://files.stripe.com/test.jpg")
            self.assertTrue(img.image_file)

    @patch("stripe.Product.modify")
    def test_save_related_syncs_only_first_image(self, mock_modify):
        for i in range(0, 10):
            ProductImage.objects.create(
                product=self.product, url=f"http://test.com/{i}.jpg", order=i
            )

        mock_form = MagicMock()
        mock_form.instance = self.product
        self.admin.save_related(MagicMock(), mock_form, [], change=True)

        args, kwargs = mock_modify.call_args
        self.assertEqual(len(kwargs["images"]), 1)
        self.assertEqual(kwargs["images"][0], "http://test.com/0.jpg")

    def test_stripe_dashboard_url_returns_link(self):
        url = self.admin.stripe_dashboard_url(self.product)
        expected_url = (
            f"https://dashboard.stripe.com/products/{self.product.stripe_product_id}"
        )
        self.assertIn(expected_url, url)
        self.assertIn('target="_blank"', url)

    def test_stripe_dashboard_url_empty_returns_dash(self):
        self.product.stripe_product_id = ""
        self.assertEqual(self.admin.stripe_dashboard_url(self.product), "-")

    def test_has_add_permission_returns_false(self):
        self.assertFalse(self.admin.has_add_permission(MagicMock()))

    def test_save_related_clears_url_when_image_file_changed(self):
        img = ProductImage.objects.create(
            product=self.product,
            url="http://test.com/old.jpg",
            image_file="product_images/test.jpg",
            order=0,
        )
        mock_form = MagicMock()
        mock_form.instance = self.product

        mock_form_instance = MagicMock()
        mock_form_instance.instance = img
        mock_form_instance.changed_data = ["image_file"]

        mock_formset = MagicMock()
        mock_formset.model = ProductImage
        mock_formset.forms = [mock_form_instance]

        with patch("stripe.Product.modify"):
            self.admin.save_related(MagicMock(), mock_form, [mock_formset], change=True)

        img.refresh_from_db()
        # url was cleared when image_file changed
        self.assertEqual(img.url, "")

    @patch("stripe.Product.modify")
    @patch("stripe.File.create")
    @patch("shop.admin.open", create=True)
    def test_save_related_stripe_upload_failure_warns_user(
        self, mock_open, mock_file_create, mock_modify
    ):
        ProductImage.objects.create(
            product=self.product,
            image_file="product_images/test.jpg",
            url="",
            order=0,
        )
        mock_file_create.side_effect = RuntimeError("Stripe API down")

        mock_form = MagicMock()
        mock_form.instance = self.product
        mock_request = MagicMock()

        with patch(
            "django.db.models.fields.files.FieldFile.path", new_callable=PropertyMock
        ) as mock_path:
            mock_path.return_value = "/fake/path/test.jpg"
            with patch.object(self.admin, "message_user") as mock_message:
                self.admin.save_related(mock_request, mock_form, [], change=True)
                mock_message.assert_any_call(
                    mock_request,
                    "Warning: Failed to upload first image to Stripe: Stripe API down",
                    level="warning",
                )

    @patch("stripe.Product.modify")
    def test_save_related_stripe_modify_failure_warns_user(self, mock_modify):
        ProductImage.objects.create(
            product=self.product,
            url="http://test.com/main.jpg",
            order=0,
        )
        mock_modify.side_effect = RuntimeError("Stripe modify error")

        mock_form = MagicMock()
        mock_form.instance = self.product
        mock_request = MagicMock()

        with patch.object(self.admin, "message_user") as mock_message:
            self.admin.save_related(mock_request, mock_form, [], change=True)
            mock_message.assert_any_call(
                mock_request,
                "Warning: Failed to sync first image to Stripe: Stripe modify error",
                level="warning",
            )

    @patch("stripe.Product.modify")
    def test_save_related_clears_stripe_images_when_no_images_left(self, mock_modify):
        mock_form = MagicMock()
        mock_form.instance = self.product

        self.admin.save_related(MagicMock(), mock_form, [], change=True)
        mock_modify.assert_called_once_with("prod_admin_test", images=[])

    @patch("stripe.Product.modify")
    def test_save_related_clears_stripe_images_silently_ignores_error(
        self, mock_modify
    ):
        mock_modify.side_effect = RuntimeError("Stripe error")
        mock_form = MagicMock()
        mock_form.instance = self.product

        # Should not raise exception
        self.admin.save_related(MagicMock(), mock_form, [], change=True)


class AdminInlineAndOtherTests(TestCase):
    def setUp(self):
        self.site = AdminSite()

    def test_product_image_inline_image_preview(self):
        inline = ProductImageInline(Product, self.site)
        # Without image_url
        img_no_url = ProductImage()
        self.assertEqual(inline.image_preview(img_no_url), "-")

        # With image_file
        img_with_file = ProductImage(image_file="product_images/photo.jpg")
        preview = inline.image_preview(img_with_file)
        self.assertIn('<img src="/media/product_images/photo.jpg"', preview)

    def test_carousel_image_admin_image_preview(self):
        admin = CarouselImageAdmin(CarouselImage, self.site)
        c_no_img = CarouselImage()
        self.assertEqual(admin.image_preview(c_no_img), "-")

        image_content = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x01D\x00;"
        c_with_img = CarouselImage(image=ContentFile(image_content, name="slide.gif"))
        preview = admin.image_preview(c_with_img)
        self.assertIn("<img src=", preview)

    def test_store_settings_admin_has_add_permission(self):
        admin = StoreSettingsAdmin(StoreSettings, self.site)
        request = MagicMock()

        StoreSettings.objects.all().delete()
        self.assertTrue(admin.has_add_permission(request))

        StoreSettings.objects.create(sales_paused=False)
        self.assertFalse(admin.has_add_permission(request))
