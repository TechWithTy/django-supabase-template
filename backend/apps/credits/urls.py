from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(
    r"transactions", views.CreditTransactionViewSet, basename="credit-transaction"
)
router.register(r"rates", views.CreditUsageRateViewSet, basename="credit-rate")

urlpatterns = [
    path("credits/", views.get_credit_balance, name="credit-balance"),
    path("credits/", include(router.urls)),
]
