from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from django_prometheus.exports import ExportToDjangoView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/', include('apps.authentication.urls')),
    path('api/', include('apps.users.urls', namespace='users')),
    path('api/', include('apps.credits.urls')),
    path('api/', include('apps.monitoring.urls', namespace='monitoring')),  # Added monitoring URLs
    path('api/cache/', include('apps.caching.urls')),  # Added caching URLs
    path('api/stripe/', include(('apps.stripe_home.urls', 'stripe'), namespace='stripe')),  # Added Stripe URLs with namespace
    
    # Prometheus metrics
    path('metrics/', ExportToDjangoView, name='prometheus-metrics'),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Add debug toolbar in development
    try:
        import debug_toolbar
        urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))
    except ImportError:
        pass
