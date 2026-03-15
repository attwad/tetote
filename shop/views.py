import stripe
import json
from django.conf import settings
from django.views.generic import ListView, DetailView, View, TemplateView
from django.http import JsonResponse
from django.urls import reverse
from django.db import transaction
from .models import Product, Brand, Yakikata, ProductType

stripe.api_key = settings.STRIPE_SECRET_KEY


class BrandDetailView(DetailView):
    model = Brand
    template_name = "shop/brand_detail.html"
    context_object_name = "brand"
    slug_url_kwarg = "brand_slug"
    slug_field = "slug"


class CartView(TemplateView):
    template_name = "shop/cart.html"


class PrivacyPolicyView(TemplateView):
    template_name = "shop/privacy_policy.html"


class ReturnPolicyView(TemplateView):
    template_name = "shop/return_policy.html"


class TermsConditionsView(TemplateView):
    template_name = "shop/terms_conditions.html"


class CheckoutSuccessView(TemplateView):
    template_name = "shop/checkout_success.html"


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
        queryset = super().get_queryset().filter(public=True)

        # Multiple selections
        brands = self.request.GET.getlist("brand")
        yakikatas = self.request.GET.getlist("yakikata")
        types = self.request.GET.getlist("type")

        # Single click toggle
        stock_filter = self.request.GET.get("stock")
        new_filter = self.request.GET.get("new")

        if brands:
            queryset = queryset.filter(brand__slug__in=brands)
        if yakikatas:
            queryset = queryset.filter(yakikata__slug__in=yakikatas)
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

        if new_filter == "true":
            # Using the model property as requested (converts to list)
            queryset = [p for p in queryset if p.is_recently_added]

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["brands"] = Brand.objects.all()
        context["yakikatas"] = Yakikata.objects.all()
        context["product_types"] = ProductType.objects.all()

        # Pass active filter lists for template comparison
        context["active_brands"] = self.request.GET.getlist("brand")
        context["active_yakikatas"] = self.request.GET.getlist("yakikata")
        context["active_types"] = self.request.GET.getlist("type")

        context["is_expanded"] = self.request.GET.get("expanded") == "true"

        # Include stock and new arrivals in the total count

        has_stock = 1 if self.request.GET.get("stock") == "in_stock" else 0
        has_new = 1 if self.request.GET.get("new") == "true" else 0

        context["total_active_filters"] = (
            len(context["active_brands"])
            + len(context["active_yakikatas"])
            + len(context["active_types"])
            + has_stock
            + has_new
        )

        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = "shop/product_detail.html"
    context_object_name = "product"
    slug_url_kwarg = "product_slug"
    slug_field = "slug"

    def get_queryset(self):
        return super().get_queryset().filter(public=True)


class CreateCheckoutSessionView(View):
    def post(self, request, *args, **kwargs):
        # Data from JS: items: [{price_id: '...', qty: 1}]
        try:
            data = json.loads(request.body)
            items = data.get("items", [])
        except (json.JSONDecodeError, KeyError):
            return JsonResponse({"error": "Invalid request data"}, status=400)

        if not items:
            return JsonResponse({"error": "Cart is empty"}, status=400)

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
            return JsonResponse({"error": "Invalid cart items"}, status=400)

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
                        {"error": f"Product with price {price_id} not found"},
                        status=400,
                    )

                if product.stock_quantity < total_qty:
                    return JsonResponse(
                        {
                            "error": f"Only {product.stock_quantity} left of {product.name}"
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
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items,
                mode="payment",
                success_url=request.build_absolute_uri(
                    reverse("shop:checkout_success")
                ),
                cancel_url=request.build_absolute_uri(reverse("shop:product_list"))
                + "?canceled=true",
            )
            return JsonResponse({"url": checkout_session.url})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
