from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.urls import reverse


class Brand(models.Model):
    name = models.CharField(_("Name"), max_length=255)
    slug = models.SlugField(_("Slug"), unique=True)
    content_slug = models.SlugField(
        _("Content Slug"),
        max_length=255,
        blank=True,
        help_text=_("The slug for the static markdown page (e.g., bizen)"),
    )

    class Meta:
        verbose_name = _("Brand")
        verbose_name_plural = _("Brands")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("shop:brand_detail", kwargs={"brand_slug": self.slug})

    @property
    def full_content_slug(self):
        if self.content_slug:
            return f"brands/{self.content_slug}"
        return ""


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
    details = models.TextField(_("Details"), blank=True)
    price = models.PositiveIntegerField(_("Price (CHF cents)"))
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
    def main_photo(self):
        """
        Returns the URL of the first image in the gallery (order=0).
        """
        first_image = self.images.all().first()
        if first_image:
            return first_image.image_url
        return ""

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

    @property
    def image_url(self):
        """
        Returns the public URL from Stripe if available, otherwise fallback to local file URL.
        """
        if self.url:
            return self.url
        if self.image_file:
            return self.image_file.url
        return ""


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


class CarouselImage(models.Model):
    image = models.ImageField(_("Image"), upload_to="carousel/")
    link = models.CharField(
        _("Link"),
        max_length=500,
        blank=True,
        help_text=_("Internal path (e.g. /shop/) or external URL"),
    )
    order = models.PositiveIntegerField(_("Order"), default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Carousel Image")
        verbose_name_plural = _("Carousel Images")
        ordering = ["order", "-created_at"]

    def __str__(self):
        return f"Carousel Image {self.id}"

    @property
    def localized_link(self):
        """
        Returns the link with the current language prefix if it's an internal path.
        """
        if not self.link:
            return ""

        if self.link.startswith(("http://", "https://", "mailto:", "tel:")):
            return self.link

        from django.utils.translation import get_language

        lang = get_language()
        # If it's a path and not the default language, prepend the language code
        # assuming 'en' is the default and URLs are prefixed for others
        if lang and lang != "en" and self.link.startswith("/"):
            # Avoid double prefixing if the link already has it
            if not self.link.startswith(f"/{lang}/"):
                return f"/{lang}{self.link}"
        return self.link
