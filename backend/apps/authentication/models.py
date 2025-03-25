from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    """
    Custom user model that extends Django's AbstractUser.
    Stores Supabase user information for synchronization.
    """
    supabase_uid = models.CharField(max_length=255, unique=True, null=True, blank=True)
    oauth_provider = models.CharField(max_length=50, blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True, null=True)
    
    class Meta:
        swappable = 'AUTH_USER_MODEL'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return self.email or self.username

class UserData(models.Model):
    """
    Model for storing additional user data.
    """
    user = models.OneToOneField('authentication.CustomUser', on_delete=models.CASCADE, related_name='user_data')
    profile_data = models.JSONField(default=dict, blank=True, null=True)
    preferences = models.JSONField(default=dict, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Data for {self.user}"
