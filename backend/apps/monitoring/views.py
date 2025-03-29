from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required

from .metrics import (
    API_REQUESTS_COUNTER,
    API_REQUEST_LATENCY,
    CREDIT_USAGE_COUNTER,
    ACTIVE_USERS,
    API_ERROR_RATE,
    ANOMALY_DETECTION_TRIGGERED
)


@require_GET
@login_required
def api_metrics_view(request):
    """
    View that returns API usage metrics in JSON format for dashboard integrations.
    """
    # Extract API requests by endpoint
    api_requests = {}
    for sample in API_REQUESTS_COUNTER.collect()[0].samples:
        if sample.name == 'api_requests_total'\
                and sample.labels.get('method') == 'GET'\
                and sample.labels.get('status') == '200':
            endpoint = sample.labels.get('endpoint')
            if endpoint not in api_requests:
                api_requests[endpoint] = 0
            api_requests[endpoint] += sample.value
    
    # Extract API latency by endpoint (using 95th percentile)
    api_latency = {}
    for sample in API_REQUEST_LATENCY.collect()[0].samples:
        if sample.name.endswith('_sum'):
            endpoint = sample.labels.get('endpoint')
            if endpoint not in api_latency:
                api_latency[endpoint] = 0
            api_latency[endpoint] += sample.value
    
    # Extract credit usage
    credit_usage = {}
    for sample in CREDIT_USAGE_COUNTER.collect()[0].samples:
        if sample.name == 'credit_usage_total':
            operation = sample.labels.get('operation')
            if operation not in credit_usage:
                credit_usage[operation] = 0
            credit_usage[operation] += sample.value
    
    # Extract active users
    active_users = {}
    for sample in ACTIVE_USERS.collect()[0].samples:
        if sample.name == 'active_users':
            timeframe = sample.labels.get('timeframe')
            active_users[timeframe] = sample.value
    
    # Extract error rates
    error_rates = {}
    for sample in API_ERROR_RATE.collect()[0].samples:
        if sample.name == 'api_error_rate':
            endpoint = sample.labels.get('endpoint')
            error_rates[endpoint] = sample.value
    
    # Extract anomaly detections
    anomalies = {}
    for sample in ANOMALY_DETECTION_TRIGGERED.collect()[0].samples:
        if sample.name == 'anomaly_detection_triggered_total':
            endpoint = sample.labels.get('endpoint')
            reason = sample.labels.get('reason')
            key = f'{endpoint}:{reason}'
            anomalies[key] = sample.value
    
    return JsonResponse({
        'api_requests': api_requests,
        'api_latency': api_latency,
        'credit_usage': credit_usage,
        'active_users': active_users,
        'error_rates': error_rates,
        'anomalies': anomalies
    })
