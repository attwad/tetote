import stripe
import json
from django.conf import settings
from django.views.generic import ListView, DetailView, View, TemplateView
from django.http import JsonResponse
from django.urls import reverse
from django.db import transaction
from .models import Product, Brand, Yakikata, ProductType

stripe.api_key = settings.STRIPE_SECRET_KEY


class CartView(TemplateView):
    template_name = "shop/cart.html"


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
        brand_slug = self.request.GET.get("brand")
        yakikata_slug = self.request.GET.get("yakikata")
        type_slug = self.request.GET.get("type")
        stock_filter = self.request.GET.get("stock")

        if brand_slug:
            queryset = queryset.filter(brand__slug=brand_slug)
        if yakikata_slug:
            queryset = queryset.filter(yakikata__slug=yakikata_slug)
        if type_slug:
            queryset = queryset.filter(product_type__slug=type_slug)
        if stock_filter == "in_stock":
            queryset = queryset.filter(stock_quantity__gt=0)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["brands"] = Brand.objects.all()
        context["yakikatas"] = Yakikata.objects.all()
        context["product_types"] = ProductType.objects.all()
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

        line_items = []
        for item in items:
            price_id = item["price_id"]
            qty = int(item["qty"])

            # Check stock atomically
            with transaction.atomic():
                product = Product.objects.select_for_update().get(
                    stripe_price_id=price_id
                )
                if product.stock_quantity < qty:
                    return JsonResponse(
                        {
                            "error": f"Only {product.stock_quantity} left of {product.name}"
                        },
                        status=400,
                    )

                # We don't decrement yet, we'll do it on webhook 'checkout.session.completed'
                # but we might want to "reserve" it for 15 mins. For now, simple checkout.
                line_items.append(
                    {
                        "price": price_id,
                        "quantity": qty,
                    }
                )

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items,
                mode="payment",
                success_url=request.build_absolute_uri(reverse("shop:product_list"))
                + "?success=true",
                cancel_url=request.build_absolute_uri(reverse("shop:product_list"))
                + "?canceled=true",
            )
            return JsonResponse({"url": checkout_session.url})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
