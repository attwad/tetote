from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.urls import reverse


class Brand(models.Model):
    name = models.CharField(_("Name"), max_length=255)
    slug = models.SlugField(_("Slug"), unique=True)
    description = models.TextField(_("Description"), blank=True)
    location = models.CharField(_("Location"), max_length=255, blank=True)
    hero_image = models.URLField(_("Hero Image URL"), max_length=500, blank=True)
    story_body = models.TextField(_("The Story"), blank=True)
    craftsmanship_body = models.TextField(_("The Craft"), blank=True)
    wares_summary = models.TextField(_("The Wares"), blank=True)
    story_side_image = models.URLField(
        _("Story Side Image URL"), max_length=500, blank=True
    )

    class Meta:
        verbose_name = _("Brand")
        verbose_name_plural = _("Brands")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("shop:brand_detail", kwargs={"brand_slug": self.slug})


class BrandImage(models.Model):
    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name="gallery_images",
        verbose_name=_("Brand"),
    )
    url = models.URLField(_("Image URL"), max_length=500)
    order = models.PositiveIntegerField(_("Order"), default=0)
    caption = models.CharField(_("Caption"), max_length=255, blank=True)

    class Meta:
        verbose_name = _("Brand Image")
        verbose_name_plural = _("Brand Images")
        ordering = ["order"]

    def __str__(self):
        return f"Gallery image for {self.brand.name}"


class Glaze(models.Model):
    name = models.CharField(_("Name"), max_length=255)
    slug = models.SlugField(_("Slug"), unique=True)

    class Meta:
        verbose_name = _("Glaze")
        verbose_name_plural = _("Glazes")

    def __str__(self):
        return self.name


class ProductType(models.Model):
    name = models.CharField(_("Name"), max_length=255)
    slug = models.SlugField(_("Slug"), unique=True)

    class Meta:
        verbose_name = _("Product Type")
        verbose_name_plural = _("Product Types")

    def __str__(self):
        return self.name


class Product(models.Model):
    stripe_product_id = models.CharField(
        _("Stripe Product ID"), max_length=255, unique=True
    )
    stripe_price_id = models.CharField(_("Stripe Price ID"), max_length=255)
    stripe_name = models.CharField(_("Stripe Name"), max_length=255, blank=True)
    name = models.CharField(_("Name"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=255, unique=True)
    description = models.TextField(_("Description"), blank=True)
    price = models.PositiveIntegerField(_("Price (CHF cents)"))
    main_photo = models.URLField(_("Main Photo URL"), max_length=500, blank=True)
    stock_quantity = models.IntegerField(_("Stock Quantity"), default=0)
    public = models.BooleanField(_("Public"), default=settings.DEBUG)
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name=_("Brand"),
    )
    glaze = models.ForeignKey(
        Glaze,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name=_("Glaze"),
    )
    product_type = models.ForeignKey(
        ProductType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name=_("Product Type"),
    )
    date_added = models.DateTimeField(_("Date Added"), default=timezone.now)

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ["-date_added"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("shop:product_detail", kwargs={"product_slug": self.slug})

    @property
    def price_in_chf(self):
        return self.price / 100.0

    @property
    def is_in_stock(self):
        return self.stock_quantity > 0


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name=_("Product"),
    )
    url = models.URLField(_("Image URL"), max_length=500, blank=True)
    image_file = models.ImageField(
        _("Image File"), upload_to="product_images/", blank=True, null=True
    )
    order = models.PositiveIntegerField(_("Order"), default=0)

    class Meta:
        verbose_name = _("Product Image")
        verbose_name_plural = _("Product Images")
        ordering = ["order"]

    def __str__(self):
        return f"Image for {self.product.name}"


class StoreAnnouncement(models.Model):
    text = models.TextField(_("Announcement Text"))
    is_active = models.BooleanField(_("Is Active"), default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Store Announcement")
        verbose_name_plural = _("Store Announcements")

    def __str__(self):
        return self.text[:50]


class StoreSettings(models.Model):
    sales_paused = models.BooleanField(_("Sales Paused"), default=False)

    class Meta:
        verbose_name = _("Store Settings")
        verbose_name_plural = _("Store Settings")

    def __str__(self):
        return str(_("Store Settings"))
