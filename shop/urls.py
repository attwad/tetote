from django.urls import path
from . import views

app_name = "shop"

urlpatterns = [
    path("", views.ProductListView.as_view(), name="product_list"),
    path("cart/", views.CartView.as_view(), name="cart"),
    path("privacy-policy/", views.PrivacyPolicyView.as_view(), name="privacy_policy"),
    path("terms/", views.TermsConditionsView.as_view(), name="terms"),
    path("api/product-info/", views.ProductInfoView.as_view(), name="product_info"),
    path(
        "products/<slug:product_slug>/",
        views.ProductDetailView.as_view(),
        name="product_detail",
    ),
    path(
        "checkout/",
        views.CreateCheckoutSessionView.as_view(),
        name="create_checkout_session",
    ),
]
