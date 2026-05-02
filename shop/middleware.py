from django.conf import settings
from django.urls import resolve
from .views import ShopWIPView


class ShopDisabledMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, "SHOP_DISABLED", False):
            try:
                resolver_match = resolve(request.path_info)

                # Check if it belongs to the shop app
                if (
                    resolver_match.app_name == "shop"
                    or resolver_match.namespace == "shop"
                ):
                    allowed_views = [
                        "about_us",
                        "contact",
                        "privacy_policy",
                        "delivery_policy",
                        "return_policy",
                        "terms",
                        "care_instructions",
                        "product_characteristics",
                        "admin_help",
                    ]

                    if resolver_match.url_name not in allowed_views:
                        # For any restricted shop-related pages, render the WIP view directly.
                        # We call .render() explicitly because TemplateResponse is lazy and
                        # needs to be rendered before the middleware returns it in this context.
                        response = ShopWIPView.as_view()(request)
                        if hasattr(response, "render") and callable(response.render):
                            response.render()
                        return response

            except Exception:
                # If URL doesn't resolve, let Django handle it (404 etc.)
                pass

        return self.get_response(request)
