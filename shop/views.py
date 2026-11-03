import json
import logging
from typing import Any, Dict

from django.conf import settings
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import models, transaction
from django.db.models import QuerySet
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import get_language, gettext as _
from django.views.generic import DetailView, ListView, TemplateView, View
import stripe

from integrations.views import (
    complete_pos_sale,
    get_attr_or_key,
    is_card_present_payment_intent,
    send_pos_receipt,
)
from news.models import NewsItem
from .context_processors import brands as brands_context
from .models import (
    Brand,
    CarouselImage,
    Glaze,
    PosSale,
    PosSaleItem,
    Product,
    ProductType,
    StoreSettings,
)

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


class HomeView(TemplateView):
    template_name = "shop/home.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context: Dict[str, Any] = super().get_context_data(**kwargs)
        context["carousel_images"] = CarouselImage.objects.all()

        news_qs = NewsItem.objects.all()
        if not self.request.user.is_staff:
            news_qs = news_qs.filter(is_draft=False)

        context["news_items"] = news_qs.order_by("-date")[:5]
        return context


class BrandDetailView(DetailView):
    model = Brand
    template_name = "shop/brand_detail.html"
    context_object_name = "brand"
    slug_field = "slug"
    slug_url_kwarg = "brand_slug"


class ProductDetailView(DetailView):
    model = Product
    template_name = "shop/product_detail.html"
    context_object_name = "product"
    slug_field = "slug"
    slug_url_kwarg = "product_slug"

    def get_queryset(self) -> QuerySet[Product]:
        return super().get_queryset().filter(public=True)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context: Dict[str, Any] = super().get_context_data(**kwargs)
        # Recommendation Logic: Other products from the same Brand
        context["related_products"] = (
            Product.objects.filter(brand=self.object.brand, public=True)
            .exclude(id=self.object.id)
            .distinct()[:4]
        )
        return context


class AboutUsView(TemplateView):
    template_name = "shop/about_us.html"


class ContactView(TemplateView):
    template_name = "shop/contact.html"


class TermsConditionsView(TemplateView):
    template_name = "shop/terms_conditions.html"


class PrivacyPolicyView(TemplateView):
    template_name = "shop/privacy_policy.html"


class DeliveryPolicyView(TemplateView):
    template_name = "shop/delivery_policy.html"


class ReturnPolicyView(TemplateView):
    template_name = "shop/return_policy.html"


class CareInstructionsView(TemplateView):
    template_name = "shop/care_instructions.html"


class ProductCharacteristicsView(TemplateView):
    template_name = "shop/product_characteristics.html"


class CheckoutSuccessView(TemplateView):
    template_name = "shop/checkout_success.html"


class AdminHelpView(UserPassesTestMixin, TemplateView):
    template_name = "shop/admin_documentation.html"

    def test_func(self) -> bool | None:
        return self.request.user.is_staff


class ProductInfoView(View):
    """
    Helper view to get product details for the cart UI
    """

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        price_ids = request.GET.getlist("price_ids[]")
        products = Product.objects.filter(stripe_price_id__in=price_ids)
        data = []
        for p in products:
            data.append(
                {
                    "price_id": p.stripe_price_id,
                    "name": p.name,
                    "price": p.price_in_chf,
                    "image": p.main_photo,
                    "stock": p.stock_quantity,
                    "url": reverse(
                        "shop:product_detail", kwargs={"product_slug": p.slug}
                    ),
                }
            )
        return JsonResponse({"products": data})


class ProductListView(ListView):
    model = Product
    template_name = "shop/product_list.html"
    context_object_name = "products"
    paginate_by = 24

    def get_queryset(self) -> QuerySet[Product]:
        queryset = (
            super()
            .get_queryset()
            .filter(public=True)
            .prefetch_related("images")
            .select_related("brand", "glaze", "product_type")
        )

        # Multiple selections
        brands = self.request.GET.getlist("brand")
        glazes = self.request.GET.getlist("glaze")
        types = self.request.GET.getlist("type")

        # Single click toggle
        stock_filter = self.request.GET.get("stock")

        if brands:
            queryset = queryset.filter(brand__slug__in=brands)
        if glazes:
            queryset = queryset.filter(glaze__slug__in=glazes)
        if types:
            queryset = queryset.filter(product_type__slug__in=types)

        if stock_filter == "in_stock":
            queryset = queryset.filter(stock_quantity__gt=0)
        elif stock_filter == "soon":
            queryset = queryset.filter(stock_quantity=0, soon_in_stock=True)

        # Sorting (Must be done on QuerySet)
        sort = self.request.GET.get("sort")
        if sort == "price_asc":
            queryset = queryset.order_by("price")
        elif sort == "price_desc":
            queryset = queryset.order_by("-price")

        return queryset

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context: Dict[str, Any] = super().get_context_data(**kwargs)
        if hasattr(self, "request") and self.request:
            context["brands"] = brands_context(self.request)["all_brands"]
        else:
            context["brands"] = (
                Brand.objects.annotate(
                    public_product_count=models.Count(
                        "products", filter=models.Q(products__public=True)
                    )
                )
                .filter(public_product_count__gt=0)
                .order_by("name")
            )

        # Sort glazes and types so that 'Other/Others' is always at the bottom
        context["glazes"] = (
            Glaze.objects.filter(products__public=True)
            .distinct()
            .order_by(
                models.Case(
                    models.When(slug__in=["other", "others"], then=models.Value(1)),
                    default=models.Value(0),
                    output_field=models.IntegerField(),
                ),
                "name",
            )
        )
        context["product_types"] = (
            ProductType.objects.filter(products__public=True)
            .distinct()
            .order_by(
                models.Case(
                    models.When(slug__in=["other", "others"], then=models.Value(1)),
                    default=models.Value(0),
                    output_field=models.IntegerField(),
                ),
                "name",
            )
        )

        # Pass active filter lists for template comparison
        context["active_brands"] = self.request.GET.getlist("brand")
        context["active_glazes"] = self.request.GET.getlist("glaze")
        context["active_types"] = self.request.GET.getlist("type")

        context["is_expanded"] = self.request.GET.get("expanded") == "true"

        # Include stock in the total count
        has_stock = 1 if self.request.GET.get("stock") in ["in_stock", "soon"] else 0

        context["total_active_filters"] = (
            len(context["active_brands"])
            + len(context["active_glazes"])
            + len(context["active_types"])
            + has_stock
        )

        return context


class CreateCheckoutSessionView(View):
    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        # Check if sales are paused
        store_settings = StoreSettings.objects.first()
        if store_settings and store_settings.sales_paused:
            return JsonResponse(
                {"error": _("Checkout is temporarily disabled")}, status=403
            )

        # Data from JS: items: [{price_id: '...', qty: 1}]
        try:
            data = json.loads(request.body)
            items = data.get("items", [])
        except (json.JSONDecodeError, KeyError):
            return JsonResponse({"error": _("Invalid request data")}, status=400)

        if not items:
            return JsonResponse({"error": _("Cart is empty")}, status=400)

        # Aggregate quantities by price_id for robustness and atomic check
        aggregated_items = {}
        for item in items:
            try:
                price_id = item["price_id"]
                qty = int(item["qty"])
                if qty <= 0:
                    continue
                aggregated_items[price_id] = aggregated_items.get(price_id, 0) + qty
            except (KeyError, ValueError, TypeError):
                continue

        if not aggregated_items:
            return JsonResponse({"error": _("Invalid cart items")}, status=400)

        line_items = []
        # Atomic check: fetch all relevant products and lock them for the duration of the check
        with transaction.atomic():
            price_ids = list(aggregated_items.keys())
            products = Product.objects.select_for_update().filter(
                stripe_price_id__in=price_ids
            )
            product_map = {p.stripe_price_id: p for p in products}

            for price_id, total_qty in aggregated_items.items():
                product = product_map.get(price_id)
                if not product:
                    return JsonResponse(
                        {
                            "error": _("Product with price %(price_id)s not found")
                            % {"price_id": price_id}
                        },
                        status=400,
                    )

                if product.stock_quantity < total_qty:
                    return JsonResponse(
                        {
                            "error": _("Only %(qty)s left of %(name)s")
                            % {"qty": product.stock_quantity, "name": product.name}
                        },
                        status=400,
                    )

                line_items.append(
                    {
                        "price": price_id,
                        "quantity": total_qty,
                    }
                )

        # Call Stripe outside the atomic block to avoid holding DB locks during network IO
        try:
            current_language = get_language()
            session_kwargs = {
                "payment_method_types": ["card"],
                "line_items": line_items,
                "mode": "payment",
                "allow_promotion_codes": True,
                "shipping_address_collection": {
                    "allowed_countries": ["CH"],
                },
                "shipping_options": [
                    {"shipping_rate": rate_id}
                    for rate_id in settings.STRIPE_SHIPPING_RATES
                ],
                "success_url": request.build_absolute_uri(
                    reverse("shop:checkout_success")
                ),
                "cancel_url": request.build_absolute_uri(reverse("shop:product_list"))
                + "?canceled=true",
            }

            if current_language != "en":
                session_kwargs["locale"] = current_language

            checkout_session = stripe.checkout.Session.create(**session_kwargs)
            return JsonResponse({"url": checkout_session.url})
        except Exception as e:
            logger.error(f"Error creating Stripe checkout session: {e}")
            return JsonResponse(
                {"error": _("An error occurred while creating the checkout session")},
                status=500,
            )


class CartView(TemplateView):
    template_name = "shop/cart.html"


class PosView(UserPassesTestMixin, TemplateView):
    template_name = "shop/pos.html"

    def test_func(self) -> bool | None:
        return self.request.user.is_staff

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context: Dict[str, Any] = super().get_context_data(**kwargs)
        products = (
            Product.objects.filter(public=True)
            .prefetch_related("images")
            .select_related("brand", "glaze", "product_type")
            .order_by("-stock_quantity", "name")
        )
        pos_products = []
        for p in products:
            pos_products.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "price_cents": p.price,
                    "price_chf": p.price_in_chf,
                    "stock": p.stock_quantity,
                    "image": p.main_photo,
                    "brand_name": p.brand.name if p.brand else "",
                    "brand_slug": p.brand.slug if p.brand else "",
                    "type_name": p.product_type.name if p.product_type else "",
                    "type_slug": p.product_type.slug if p.product_type else "",
                    "glaze_name": p.glaze.name if p.glaze else "",
                }
            )
        context["pos_products_json"] = json.dumps(pos_products)
        context["brands"] = (
            Brand.objects.filter(products__public=True).distinct().order_by("name")
        )
        context["product_types"] = (
            ProductType.objects.filter(products__public=True)
            .distinct()
            .order_by("name")
        )
        return context


class PosCreateSaleView(UserPassesTestMixin, View):
    def test_func(self) -> bool | None:
        return self.request.user.is_staff

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": _("Invalid request data")}, status=400)

        raw_items = data.get("items", [])
        if not raw_items or not isinstance(raw_items, list):
            return JsonResponse({"error": _("No items selected")}, status=400)

        payment_method = data.get("payment_method", PosSale.METHOD_TAP_TO_PAY)
        if payment_method not in (PosSale.METHOD_TAP_TO_PAY, PosSale.METHOD_TWINT):
            return JsonResponse({"error": _("Invalid payment method")}, status=400)

        try:
            discount_amount = int(data.get("discount_amount", 0) or 0)
        except (ValueError, TypeError):
            return JsonResponse({"error": _("Invalid discount amount")}, status=400)

        if discount_amount < 0:
            return JsonResponse({"error": _("Discount cannot be negative")}, status=400)

        customer_email = (data.get("customer_email") or "").strip()
        if customer_email:
            try:
                validate_email(customer_email)
            except ValidationError:
                return JsonResponse(
                    {"error": _("Please enter a valid email address")}, status=400
                )

        aggregated_items: Dict[int, int] = {}
        for item in raw_items:
            try:
                product_id = int(item["product_id"])
                qty = int(item["qty"])
                if qty <= 0:
                    continue
                aggregated_items[product_id] = aggregated_items.get(product_id, 0) + qty
            except (KeyError, ValueError, TypeError):
                continue

        if not aggregated_items:
            return JsonResponse({"error": _("Invalid items selected")}, status=400)

        with transaction.atomic():
            product_ids = list(aggregated_items.keys())
            products = Product.objects.select_for_update().filter(
                id__in=product_ids, public=True
            )
            product_map = {p.id: p for p in products}

            subtotal_amount = 0
            sale_items_to_create = []

            for product_id, qty in aggregated_items.items():
                product = product_map.get(product_id)
                if not product:
                    return JsonResponse(
                        {"error": _("Product not found or not public")}, status=400
                    )
                if product.stock_quantity < qty:
                    return JsonResponse(
                        {
                            "error": _("Only %(qty)s left of %(name)s")
                            % {"qty": product.stock_quantity, "name": product.name}
                        },
                        status=400,
                    )
                subtotal_amount += product.price * qty
                sale_items_to_create.append((product, qty, product.price))

            if discount_amount >= subtotal_amount:
                return JsonResponse(
                    {"error": _("Discount must be less than the subtotal")}, status=400
                )

            total_amount = subtotal_amount - discount_amount
            if total_amount < 50:
                return JsonResponse(
                    {"error": _("Total amount must be at least CHF 0.50")}, status=400
                )

            # Cancel any previous pending POS sales so only one is active at a time
            PosSale.objects.filter(status=PosSale.STATUS_PENDING).update(
                status=PosSale.STATUS_CANCELED
            )

            sale = PosSale.objects.create(
                status=PosSale.STATUS_PENDING,
                payment_method=payment_method,
                subtotal_amount=subtotal_amount,
                discount_amount=discount_amount,
                total_amount=total_amount,
                customer_email=customer_email,
            )
            for product, qty, unit_price in sale_items_to_create:
                PosSaleItem.objects.create(
                    sale=sale,
                    product=product,
                    quantity=qty,
                    unit_price=unit_price,
                )

        if payment_method == PosSale.METHOD_TWINT:
            summary = sale.items_summary()
            return_url = (
                request.build_absolute_uri(reverse("shop:pos"))
                + f"?twint_sale={sale.id}"
            )
            pi_kwargs: Dict[str, Any] = {
                "amount": sale.total_amount,
                "currency": "chf",
                "payment_method_types": ["twint"],
                "payment_method_data": {"type": "twint"},
                "confirm": True,
                "return_url": return_url,
                "description": summary,
                "metadata": {
                    "pos_sale_id": str(sale.id),
                    "items": summary[:500],
                    "subtotal_chf": f"{sale.subtotal_in_chf:.2f}",
                    "discount_chf": f"{sale.discount_in_chf:.2f}",
                    "total_chf": f"{sale.total_in_chf:.2f}",
                },
            }
            if sale.customer_email:
                pi_kwargs["receipt_email"] = sale.customer_email

            try:
                pi = stripe.PaymentIntent.create(**pi_kwargs)
                pi_id = get_attr_or_key(pi, "id")
                next_action = get_attr_or_key(pi, "next_action", {}) or {}
                redirect_obj = get_attr_or_key(next_action, "redirect_to_url", {}) or {}
                twint_url = get_attr_or_key(redirect_obj, "url", "")

                sale.stripe_payment_intent_id = pi_id
                sale.twint_redirect_url = twint_url or ""
                sale.save(
                    update_fields=["stripe_payment_intent_id", "twint_redirect_url"]
                )
            except Exception as e:
                logger.error(
                    f"Error creating TWINT PaymentIntent for POS Sale #{sale.id}: {e}"
                )
                sale.status = PosSale.STATUS_CANCELED
                sale.save(update_fields=["status"])
                return JsonResponse(
                    {"error": _("Failed to initialize TWINT payment with Stripe")},
                    status=500,
                )

        return JsonResponse(
            {
                "sale_id": sale.id,
                "status": sale.status,
                "payment_method": sale.payment_method,
                "subtotal_cents": sale.subtotal_amount,
                "discount_cents": sale.discount_amount,
                "total_cents": sale.total_amount,
                "subtotal_chf": f"{sale.subtotal_in_chf:.2f}",
                "discount_chf": f"{sale.discount_in_chf:.2f}",
                "total_chf": f"{sale.total_in_chf:.2f}",
                "twint_redirect_url": sale.twint_redirect_url,
                "customer_email": sale.customer_email,
            }
        )


class PosSaleStatusView(UserPassesTestMixin, View):
    def test_func(self) -> bool | None:
        return self.request.user.is_staff

    def _serialize_sale(self, sale: PosSale) -> Dict[str, Any]:
        updated_stocks = {}
        if sale.status == PosSale.STATUS_COMPLETED:
            for item in sale.items.select_related("product").all():
                updated_stocks[item.product_id] = item.product.stock_quantity

        return {
            "sale_id": sale.id,
            "status": sale.status,
            "payment_method": sale.payment_method,
            "total_chf": f"{sale.total_in_chf:.2f}",
            "customer_email": sale.customer_email,
            "receipt_sent": sale.receipt_sent,
            "updated_stocks": updated_stocks,
        }

    def get(
        self, request: HttpRequest, sale_id: int, *args: Any, **kwargs: Any
    ) -> JsonResponse:
        sale = get_object_or_404(PosSale, id=sale_id)

        if sale.status == PosSale.STATUS_PENDING:
            try:
                if (
                    sale.payment_method == PosSale.METHOD_TWINT
                    and sale.stripe_payment_intent_id
                ):
                    pi = stripe.PaymentIntent.retrieve(sale.stripe_payment_intent_id)
                    if get_attr_or_key(pi, "status") == "succeeded":
                        complete_pos_sale(sale.id, payment_intent=pi)
                        sale.refresh_from_db()
                elif sale.payment_method == PosSale.METHOD_TAP_TO_PAY:
                    created_gte = max(0, int(sale.created_at.timestamp()) - 10)
                    pis = stripe.PaymentIntent.list(
                        created={"gte": created_gte}, limit=5
                    )
                    for pi in get_attr_or_key(pis, "data", []) or []:
                        pi_id = get_attr_or_key(pi, "id")
                        if (
                            get_attr_or_key(pi, "status") == "succeeded"
                            and get_attr_or_key(pi, "amount") == sale.total_amount
                            and is_card_present_payment_intent(pi)
                            and not PosSale.objects.filter(
                                stripe_payment_intent_id=pi_id
                            ).exists()
                        ):
                            complete_pos_sale(sale.id, payment_intent=pi)
                            sale.refresh_from_db()
                            break
            except Exception as e:
                logger.warning(
                    f"Polling check against Stripe failed for POS Sale #{sale.id}: {e}"
                )

        return JsonResponse(self._serialize_sale(sale))

    def post(
        self, request: HttpRequest, sale_id: int, *args: Any, **kwargs: Any
    ) -> JsonResponse:
        sale = get_object_or_404(PosSale, id=sale_id)
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": _("Invalid request data")}, status=400)

        action = data.get("action")
        if action == "cancel":
            if sale.status == PosSale.STATUS_PENDING:
                sale.status = PosSale.STATUS_CANCELED
                sale.save(update_fields=["status"])
                if sale.stripe_payment_intent_id:
                    try:
                        stripe.PaymentIntent.cancel(sale.stripe_payment_intent_id)
                    except Exception as e:
                        logger.warning(
                            f"Could not cancel Stripe PaymentIntent '{sale.stripe_payment_intent_id}': {e}"
                        )
            return JsonResponse(self._serialize_sale(sale))

        if action == "send_receipt":
            customer_email = (data.get("customer_email") or "").strip()
            try:
                validate_email(customer_email)
            except ValidationError:
                return JsonResponse(
                    {"error": _("Please enter a valid email address")}, status=400
                )

            if sale.status == PosSale.STATUS_PENDING:
                sale.customer_email = customer_email
                sale.save(update_fields=["customer_email"])
                return JsonResponse(self._serialize_sale(sale))

            if sale.status == PosSale.STATUS_COMPLETED:
                sent = send_pos_receipt(sale, email=customer_email)
                if not sent:
                    return JsonResponse(
                        {"error": _("Failed to send receipt via Stripe")}, status=500
                    )
                return JsonResponse(self._serialize_sale(sale))

            return JsonResponse(
                {"error": _("Cannot send receipt for a canceled sale")}, status=400
            )

        return JsonResponse({"error": _("Invalid action")}, status=400)
