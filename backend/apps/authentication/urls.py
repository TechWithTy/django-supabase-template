from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check, name='health-check'),
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('user/', views.user_info, name='user-info'),
    path('logout/', views.logout, name='logout'),
]
