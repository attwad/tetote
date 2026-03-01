from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import datetime


class Brand(models.Model):
    name = models.CharField(_("Name"), max_length=255)
    slug = models.SlugField(_("Slug"), unique=True)
    description = models.TextField(_("Description"), blank=True)

    class Meta:
        verbose_name = _("Brand")
        verbose_name_plural = _("Brands")

    def __str__(self):
        return self.name


class Yakikata(models.Model):
    name = models.CharField(_("Name"), max_length=255)
    slug = models.SlugField(_("Slug"), unique=True)

    class Meta:
        verbose_name = _("Yakikata")
        verbose_name_plural = _("Yakikatas")

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
    yakikata = models.ForeignKey(
        Yakikata,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name=_("Yakikata"),
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

    @property
    def price_in_chf(self):
        return self.price / 100.0

    @property
    def is_in_stock(self):
        return self.stock_quantity > 0

    @property
    def is_recently_added(self):
        return self.date_added >= timezone.now() - datetime.timedelta(days=60)


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name=_("Product"),
    )
    url = models.URLField(_("Image URL"), max_length=500)
    order = models.PositiveIntegerField(_("Order"), default=0)

    class Meta:
        verbose_name = _("Product Image")
        verbose_name_plural = _("Product Images")
        ordering = ["order"]

    def __str__(self):
        return f"Image for {self.product.name}"
