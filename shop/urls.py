from django.urls import path
from . import views

app_name = "shop"

urlpatterns = [
    path(
        "brands/<slug:brand_slug>/",
        views.BrandDetailView.as_view(),
        name="brand_detail",
    ),
    path("", views.ProductListView.as_view(), name="product_list"),
    path("about-us/", views.AboutUsView.as_view(), name="about_us"),
    path("contact/", views.ContactView.as_view(), name="contact"),
    path("cart/", views.CartView.as_view(), name="cart"),
    path("privacy-policy/", views.PrivacyPolicyView.as_view(), name="privacy_policy"),
    path(
        "delivery-policy/", views.DeliveryPolicyView.as_view(), name="delivery_policy"
    ),
    path("return-policy/", views.ReturnPolicyView.as_view(), name="return_policy"),
    path("terms/", views.TermsConditionsView.as_view(), name="terms"),
    path(
        "care-instructions/",
        views.CareInstructionsView.as_view(),
        name="care_instructions",
    ),
    path(
        "product-characteristics/",
        views.ProductCharacteristicsView.as_view(),
        name="product_characteristics",
    ),
    path("api/product-info/", views.ProductInfoView.as_view(), name="product_info"),
    path("help/", views.AdminHelpView.as_view(), name="admin_help"),
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
    path(
        "checkout-success/",
        views.CheckoutSuccessView.as_view(),
        name="checkout_success",
    ),
]
