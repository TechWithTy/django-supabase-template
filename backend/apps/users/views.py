from typing import Any, Dict

from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
import requests

from .models import UserProfile
from .serializers import UserSerializer, UserProfileSerializer

class IsAdminOrSelf(permissions.BasePermission):
    """
    Custom permission to allow users to access only their own resources
    or admins to access any resource.
    """
    
    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        # Allow admins to access any resource
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Allow users to access only their own resources
        if isinstance(obj, User):
            return obj == request.user
        if isinstance(obj, UserProfile):
            return obj.user == request.user
        
        return False

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing users.
    
    This viewset provides CRUD operations for users, with appropriate
    permissions and additional endpoints for managing user-specific data.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrSelf]
    
    def get_queryset(self):
        """
        Filter the queryset based on user permissions.
        """
        user = self.request.user
        
        # Admins can see all users
        if user.is_staff or user.is_superuser:
            return User.objects.all()
        
        # Regular users can only see themselves
        return User.objects.filter(id=user.id)
    
    @action(detail=False, methods=['get'])
    def me(self, request: Request) -> Response:
        """
        Get the current user's information.
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_credits(self, request: Request, pk=None) -> Response:
        """
        Add credits to a user's account.
        
        Only admins can add credits to any user. Users can't add credits to themselves.
        """
        user = self.get_object()
        amount = request.data.get('amount', 0)
        
        try:
            amount = int(amount)
            if amount <= 0:
                return Response(
                    {"error": "Amount must be a positive integer"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {"error": "Amount must be a valid integer"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Only admins can add credits
        if not request.user.is_staff and not request.user.is_superuser:
            return Response(
                {"error": "Only administrators can add credits"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Add credits to the user's profile
        try:
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'supabase_uid': user.username}
            )
            profile.add_credits(amount)
            
            return Response({
                "message": f"Added {amount} credits to {user.username}'s account",
                "new_balance": profile.credits_balance
            })
        except Exception as e:
            return Response(
                {"error": f"Failed to add credits: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def supabase_users(self, request: Request) -> Response:
        """
        Get a list of users from Supabase.
        
        Only admins can access this endpoint.
        """
        # Only admins can list Supabase users
        if not request.user.is_staff and not request.user.is_superuser:
            return Response(
                {"error": "Only administrators can list Supabase users"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Call Supabase Admin API to list users
            response = requests.get(
                f"{settings.SUPABASE_URL}/auth/v1/admin/users",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}"
                }
            )
            
            return Response(response.json(), status=response.status_code)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to retrieve Supabase users: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
