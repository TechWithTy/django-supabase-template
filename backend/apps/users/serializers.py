from typing import Dict, Any

from django.contrib.auth.models import User
from rest_framework import serializers

from .models import UserProfile

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for the UserProfile model.
    """
    class Meta:
        model = UserProfile
        fields = ['supabase_uid', 'subscription_tier', 'credits_balance', 'created_at', 'updated_at']
        read_only_fields = ['supabase_uid', 'credits_balance', 'created_at', 'updated_at']

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model with profile information.
    """
    profile = UserProfileSerializer(read_only=True)
    subscription_tier = serializers.CharField(write_only=True, required=False)
    credits_balance = serializers.IntegerField(read_only=True, source='profile.credits_balance')
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile', 
                  'subscription_tier', 'credits_balance', 'date_joined', 'is_active']
        read_only_fields = ['id', 'username', 'date_joined', 'credits_balance']
    
    def update(self, instance: User, validated_data: Dict[str, Any]) -> User:
        """
        Update the User instance and related UserProfile.
        """
        # Get the subscription tier from validated data and remove it
        subscription_tier = validated_data.pop('subscription_tier', None)
        
        # Update the User instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update the UserProfile if subscription_tier is provided
        if subscription_tier and hasattr(instance, 'profile'):
            instance.profile.subscription_tier = subscription_tier
            instance.profile.save(update_fields=['subscription_tier', 'updated_at'])
        
        return instance
