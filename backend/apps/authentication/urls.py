from django.urls import path
from . import views
from .views import UserDataView

urlpatterns = [
    path('health/', views.health_check, name='health-check'),
    path('login/', views.login, name='login'),
    path('login/oauth/', views.oauth_login, name='oauth-login'),
    path('register/', views.register, name='register'),
    path('reset-password/', views.reset_password, name='reset-password'),
    path('current-user/', views.user_info, name='current-user'),
    path('logout/', views.logout, name='logout'),
    path('user-data/', UserDataView.as_view(), name='user-data'),
]
