import time
from django.utils.deprecation import MiddlewareMixin
from .metrics import (
    API_REQUESTS_COUNTER,
    API_REQUEST_LATENCY,
    API_ERROR_RATE,
    ANOMALY_DETECTION_TRIGGERED
)


class PrometheusMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware that collects metrics for Prometheus monitoring.
    This middleware extends the basic django-prometheus middleware with custom metrics.
    """

    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.get_response = get_response
        self.api_path_prefix = '/api/'
    
    def process_request(self, request):
        # Only track API requests
        if request.path.startswith(self.api_path_prefix):
            request._prometheus_start_time = time.time()
            # Extract endpoint for labeling
            request._prometheus_endpoint = self._get_endpoint_name(request.path)
        return None
    
    def process_response(self, request, response):
        # Only track API requests
        if hasattr(request, '_prometheus_start_time') and request.path.startswith(self.api_path_prefix):
            endpoint = request._prometheus_endpoint
            method = request.method
            status = str(response.status_code)
            latency = time.time() - request._prometheus_start_time
            
            # Track request count
            API_REQUESTS_COUNTER.labels(endpoint=endpoint, method=method, status=status).inc()
            
            # Track request latency
            API_REQUEST_LATENCY.labels(endpoint=endpoint, method=method).observe(latency)
            
            # Track error rate
            if 400 <= response.status_code < 600:
                API_ERROR_RATE.labels(endpoint=endpoint).set(1)
                
                # Check for anomalies
                if response.status_code >= 500:
                    ANOMALY_DETECTION_TRIGGERED.labels(endpoint=endpoint, reason='server_error').inc()
                elif latency > 1.0:  # 1 second threshold for slow requests
                    ANOMALY_DETECTION_TRIGGERED.labels(endpoint=endpoint, reason='high_latency').inc()
            else:
                # Gradually reduce error rate if no errors
                current_error_rate = API_ERROR_RATE.labels(endpoint=endpoint)._value.get((endpoint,), 0)
                if current_error_rate > 0:
                    API_ERROR_RATE.labels(endpoint=endpoint).set(max(0, current_error_rate - 0.1))
            
        return response
    
    def _get_endpoint_name(self, path):
        """
        Extract a clean endpoint name from the path for metrics labeling.
        Examples:
        - /api/users/profile/ -> users
        - /api/credits/balance/ -> credits
        """
        parts = path.strip('/').split('/')
        if len(parts) > 1 and parts[0] == 'api':
            return parts[1]
        return 'unknown'
