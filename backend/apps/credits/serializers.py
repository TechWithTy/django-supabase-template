from rest_framework import serializers

from .models import CreditTransaction, CreditUsageRate

class CreditTransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for the CreditTransaction model.
    """
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = CreditTransaction
        fields = ['id', 'username', 'amount', 'balance_after', 'description', 
                  'endpoint', 'created_at']
        read_only_fields = fields

class CreditUsageRateSerializer(serializers.ModelSerializer):
    """
    Serializer for the CreditUsageRate model.
    """
    class Meta:
        model = CreditUsageRate
        fields = ['id', 'endpoint_path', 'credits_per_request', 'description', 'is_active']
        read_only_fields = fields
