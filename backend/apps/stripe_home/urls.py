from django.urls import path
from .views import CheckoutSessionView, StripeWebhookView, CustomerPortalView, CustomerDashboardView, ProgrammableCheckoutView, ProductManagementView

urlpatterns = [
    # Checkout session endpoints
    path('subscription/checkout/<int:plan_id>/', CheckoutSessionView.as_view(), name='subscription_checkout'),
    path('checkout/programmable/', ProgrammableCheckoutView.as_view(), name='programmable_checkout'),
    
    # Customer portal endpoint
    path('customer-portal/', CustomerPortalView.as_view(), name='customer_portal'),
    
    # Customer dashboard endpoint
    path('dashboard/', CustomerDashboardView.as_view(), name='customer_dashboard'),
    
    # Product management endpoints
    path('products/', ProductManagementView.as_view(), name='product_management'),
    
    # Webhook endpoint
    path('webhook/', StripeWebhookView.as_view(), name='webhook'),
]
