from django.urls import path
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from .views import api_metrics_view


app_name = 'monitoring'


@login_required
def metrics_view(request):
    """
    View that exposes Prometheus metrics for scraping.
    This view returns the metrics in the Prometheus format.
    """
    return HttpResponse(
        generate_latest(),
        content_type=CONTENT_TYPE_LATEST
    )


urlpatterns = [
    path('metrics/', metrics_view, name='metrics'),
    path('api-metrics/', api_metrics_view, name='api_metrics'),
]
