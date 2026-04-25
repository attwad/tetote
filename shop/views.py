from django.conf import settings
import stripe
from django.views.generic import ListView, DetailView, View, TemplateView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import JsonResponse
from django.urls import reverse
from django.db import transaction
from django.utils.translation import gettext as _, get_language
from .models import Product, Brand, Glaze, ProductType, StoreSettings
import json

stripe.api_key = settings.STRIPE_SECRET_KEY


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

    def get_queryset(self):
        return super().get_queryset().filter(public=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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

    def test_func(self):
        return self.request.user.is_staff


class ProductInfoView(View):
    """
    Helper view to get product details for the cart UI
    """

    def get(self, request, *args, **kwargs):
        price_ids = request.GET.getlist("price_ids[]")
        products = Product.objects.filter(stripe_price_id__in=price_ids)
        data = []
        for p in products:
            data.append(
                {
                    "price_id": p.stripe_price_id,
                    "name": p.name,
                    "description": p.description,
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

    def get_queryset(self):
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

        # Sorting (Must be done on QuerySet)
        sort = self.request.GET.get("sort")
        if sort == "price_asc":
            queryset = queryset.order_by("price")
        elif sort == "price_desc":
            queryset = queryset.order_by("-price")

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["brands"] = Brand.objects.filter(products__public=True).distinct()
        context["glazes"] = Glaze.objects.filter(products__public=True).distinct()
        context["product_types"] = ProductType.objects.filter(
            products__public=True
        ).distinct()

        # Pass active filter lists for template comparison
        context["active_brands"] = self.request.GET.getlist("brand")
        context["active_glazes"] = self.request.GET.getlist("glaze")
        context["active_types"] = self.request.GET.getlist("type")

        context["is_expanded"] = self.request.GET.get("expanded") == "true"

        # Include stock in the total count
        has_stock = 1 if self.request.GET.get("stock") == "in_stock" else 0

        context["total_active_filters"] = (
            len(context["active_brands"])
            + len(context["active_glazes"])
            + len(context["active_types"])
            + has_stock
        )

        return context


class CreateCheckoutSessionView(View):
    def post(self, request, *args, **kwargs):
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
            # Import logging and use it for internal debugging
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error creating Stripe checkout session: {e}")
            return JsonResponse(
                {"error": _("An error occurred while creating the checkout session")},
                status=500,
            )


class CartView(TemplateView):
    template_name = "shop/cart.html"


class ShopWIPView(TemplateView):
    template_name = "shop/wip.html"
