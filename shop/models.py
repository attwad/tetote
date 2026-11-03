from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import get_language, gettext_lazy as _
from markdownx.models import MarkdownxField


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

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse("shop:brand_detail", kwargs={"brand_slug": self.slug})

    @property
    def full_content_slug(self) -> str:
        if self.content_slug:
            return f"brands/{self.content_slug}"
        return ""


class Glaze(models.Model):
    name = models.CharField(_("Name"), max_length=255)
    slug = models.SlugField(_("Slug"), unique=True)

    class Meta:
        verbose_name = _("Glaze")
        verbose_name_plural = _("Glazes")

    def __str__(self) -> str:
        return self.name


class ProductType(models.Model):
    name = models.CharField(_("Name"), max_length=255)
    slug = models.SlugField(_("Slug"), unique=True)

    class Meta:
        verbose_name = _("Product Type")
        verbose_name_plural = _("Product Types")

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    stripe_product_id = models.CharField(
        _("Stripe Product ID"), max_length=255, unique=True
    )
    stripe_price_id = models.CharField(_("Stripe Price ID"), max_length=255)
    stripe_name = models.CharField(_("Stripe Name"), max_length=255, blank=True)
    name = models.CharField(_("Name"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=255, unique=True)
    description = MarkdownxField(_("Description"), blank=True)
    details = MarkdownxField(_("Details"), blank=True)
    price = models.PositiveIntegerField(_("Price (CHF cents)"))
    stock_quantity = models.IntegerField(_("Stock Quantity"), default=0)
    soon_in_stock = models.BooleanField(_("Soon in stock"), default=False)
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

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse("shop:product_detail", kwargs={"product_slug": self.slug})

    @property
    def main_photo(self) -> str:
        """
        Returns the URL of the first image in the gallery (order=0).
        """
        first_image = self.images.all().first()
        if first_image:
            return first_image.image_url
        return ""

    @property
    def price_in_chf(self) -> float:
        return self.price / 100.0

    @property
    def is_in_stock(self) -> bool:
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

    def __str__(self) -> str:
        return f"Image for {self.product.name}"

    @property
    def image_url(self) -> str:
        """
        Returns the local file URL. We no longer serve images from Stripe URLs directly.
        """
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

    def __str__(self) -> str:
        return self.text[:50]


class StoreSettings(models.Model):
    sales_paused = models.BooleanField(_("Sales Paused"), default=False)

    class Meta:
        verbose_name = _("Store Settings")
        verbose_name_plural = _("Store Settings")

    def __str__(self) -> str:
        return str(_("Store Settings"))


class CarouselImage(models.Model):
    image = models.ImageField(_("Image"), upload_to="carousel/")
    alt_text = models.CharField(_("Alt Text"), max_length=255, blank=True)
    overlay_image = models.FileField(
        _("Overlay Image"),
        upload_to="carousel/overlays/",
        blank=True,
        null=True,
        help_text=_(
            "Optional SVG overlay centered horizontally and stuck to the right."
        ),
    )
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

    def __str__(self) -> str:
        return f"Carousel Image {self.id}"

    @property
    def localized_link(self) -> str:
        """
        Returns the link with the current language prefix if it's an internal path.
        """
        if not self.link:
            return ""

        if self.link.startswith(("http://", "https://", "mailto:", "tel:")):
            return self.link

        lang = get_language()
        # If it's a path and not the default language, prepend the language code
        # assuming 'en' is the default and URLs are prefixed for others
        if lang and lang != "en" and self.link.startswith("/"):
            # Avoid double prefixing if the link already has it
            if not self.link.startswith(f"/{lang}/"):
                return f"/{lang}{self.link}"
        return self.link


class PosSale(models.Model):
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELED = "canceled"
    STATUS_CHOICES = [
        (STATUS_PENDING, _("Pending")),
        (STATUS_COMPLETED, _("Completed")),
        (STATUS_CANCELED, _("Canceled")),
    ]

    METHOD_TAP_TO_PAY = "tap_to_pay"
    METHOD_TWINT = "twint"
    METHOD_CHOICES = [
        (METHOD_TAP_TO_PAY, _("Tap to Pay (Card)")),
        (METHOD_TWINT, _("TWINT")),
    ]

    status = models.CharField(
        _("Status"), max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    payment_method = models.CharField(
        _("Payment Method"),
        max_length=20,
        choices=METHOD_CHOICES,
        default=METHOD_TAP_TO_PAY,
    )
    subtotal_amount = models.PositiveIntegerField(_("Subtotal (CHF cents)"))
    discount_amount = models.PositiveIntegerField(_("Discount (CHF cents)"), default=0)
    total_amount = models.PositiveIntegerField(_("Total (CHF cents)"))
    customer_email = models.EmailField(_("Customer Email"), blank=True)
    stripe_payment_intent_id = models.CharField(
        _("Stripe PaymentIntent ID"), max_length=255, blank=True, null=True, unique=True
    )
    twint_redirect_url = models.URLField(
        _("TWINT Redirect URL"), max_length=1000, blank=True
    )
    receipt_sent = models.BooleanField(_("Receipt Sent"), default=False)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    completed_at = models.DateTimeField(_("Completed At"), null=True, blank=True)

    class Meta:
        verbose_name = _("POS Sale")
        verbose_name_plural = _("POS Sales")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"POS Sale #{self.id} ({self.get_status_display()} - CHF {self.total_in_chf:.2f})"

    @property
    def subtotal_in_chf(self) -> float:
        return self.subtotal_amount / 100.0

    @property
    def discount_in_chf(self) -> float:
        return self.discount_amount / 100.0

    @property
    def total_in_chf(self) -> float:
        return self.total_amount / 100.0

    def items_summary(self) -> str:
        parts = [
            f"{item.quantity}x {item.product.name}"
            for item in self.items.select_related("product").all()
        ]
        summary = f"POS Sale #{self.id}: " + ", ".join(parts)
        if self.discount_amount > 0:
            summary += f" (Discount: CHF {self.discount_in_chf:.2f})"
        return summary


class PosSaleItem(models.Model):
    sale = models.ForeignKey(
        PosSale,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("POS Sale"),
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="pos_sale_items",
        verbose_name=_("Product"),
    )
    quantity = models.PositiveIntegerField(_("Quantity"))
    unit_price = models.PositiveIntegerField(_("Unit Price (CHF cents)"))

    class Meta:
        verbose_name = _("POS Sale Item")
        verbose_name_plural = _("POS Sale Items")

    def __str__(self) -> str:
        return f"{self.quantity}x {self.product.name}"

    @property
    def unit_price_in_chf(self) -> float:
        return self.unit_price / 100.0

    @property
    def line_total_in_chf(self) -> float:
        return (self.unit_price * self.quantity) / 100.0
