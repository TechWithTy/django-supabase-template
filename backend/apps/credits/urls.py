from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import base

router = DefaultRouter()
router.register(
    r"transactions", base.CreditTransactionViewSet, basename="credit-transaction"
)
router.register(r"rates", base.CreditUsageRateViewSet, basename="credit-rate")

urlpatterns = [
    path("credits/", base.get_credit_balance, name="credit-balance"),
    path("credits/", include(router.urls)),
]
