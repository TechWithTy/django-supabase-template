from django.urls import path
from . import base
from .base import UserDataView

urlpatterns = [
    path('health/', base.health_check, name='health-check'),
    path('login/', base.login, name='login'),
    path('login/oauth/', base.oauth_login, name='oauth-login'),
    path('register/', base.register, name='register'),
    path('reset-password/', base.reset_password, name='reset-password'),
    path('current-user/', base.user_info, name='current-user'),
    path('logout/', base.logout, name='logout'),
    path('user-data/', UserDataView.as_view(), name='user-data'),
]
