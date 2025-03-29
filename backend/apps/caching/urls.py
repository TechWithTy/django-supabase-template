from django.urls import path
from . import views

app_name = 'caching'

urlpatterns = [
    path('example/', views.cached_data_example, name='cached_data_example'),
    path('invalidate/', views.invalidate_cache_example, name='invalidate_cache'),
    path('status/', views.cache_status, name='cache_status'),
    path('rate-limited/', views.rate_limited_example, name='rate_limited_example'),
]
