from typing import Any, Dict

from django.db.models import Sum
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.users.models import UserProfile
from .models import CreditTransaction, CreditUsageRate
from .serializers import CreditTransactionSerializer, CreditUsageRateSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_credit_balance(request: Request) -> Response:
    """
    Get the current user's credit balance.
    """
    try:
        profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'supabase_uid': request.user.username}
        )
        
        return Response({
            'credits': profile.credits_balance,
            'subscription_tier': profile.subscription_tier
        })
        
    except Exception as e:
        return Response(
            {"error": f"Failed to retrieve credit balance: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class CreditTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing credit transactions.
    
    Users can only view their own transactions, while admins can view all transactions.
    """
    serializer_class = CreditTransactionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Filter the queryset based on user permissions.
        """
        user = self.request.user
        
        # Admins can see all transactions
        if user.is_staff or user.is_superuser:
            return CreditTransaction.objects.all()
        
        # Regular users can only see their own transactions
        return CreditTransaction.objects.filter(user=user)
    
    @action(detail=False, methods=['get'])
    def summary(self, request: Request) -> Response:
        """
        Get a summary of credit transactions for the current user.
        """
        user = request.user
        
        # Get total credits added and used
        added = CreditTransaction.objects.filter(
            user=user, amount__gt=0
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        used = CreditTransaction.objects.filter(
            user=user, amount__lt=0
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Get current balance
        try:
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'supabase_uid': user.username}
            )
            balance = profile.credits_balance
        except Exception:
            balance = 0
        
        return Response({
            'total_added': added,
            'total_used': abs(used),
            'current_balance': balance
        })

class CreditUsageRateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing credit usage rates.
    
    All authenticated users can view the credit usage rates.
    """
    queryset = CreditUsageRate.objects.filter(is_active=True)
    serializer_class = CreditUsageRateSerializer
    permission_classes = [IsAuthenticated]
