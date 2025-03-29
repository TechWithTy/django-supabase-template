from typing import Optional, Tuple, Any
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
import logging

User = get_user_model()
logger = logging.getLogger('apps.authentication')

class SupabaseJWTAuthentication(BaseAuthentication):
    """
    Authentication class for Django REST Framework that validates Supabase JWT tokens.
    
    This class is used by DRF to authenticate requests. It checks for a valid JWT token
    in the Authorization header and validates it against the Supabase JWT secret.
    If valid, it returns the user object and the token payload.
    """
    
    def authenticate(self, request: Request) -> Optional[Tuple[Any, dict]]:
        # Get the Authorization header
        auth_header = request.headers.get('Authorization', '')
        
        # If no Authorization header, return None (anonymous user)
        if not auth_header.startswith('Bearer '):
            return None
        
        # Extract the token
        token = auth_header.split(' ')[1]
        
        try:
            # Decode and verify the token
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=['HS256'],
                options={
                    'verify_signature': True,
                    'verify_iat': False,  # Skip 'issued at' verification for testing
                    'verify_aud': False   # Skip audience verification for testing
                }
            )
            
            # Get or create the user based on Supabase user ID
            user_id = payload.get('sub')
            if not user_id:
                raise AuthenticationFailed('Invalid token payload')
            
            # Try to get the user from the database
            try:
                user = User.objects.get(username=user_id)
            except User.DoesNotExist:
                # Create a new user if they don't exist
                user = User.objects.create(
                    username=user_id,
                    email=payload.get('email', ''),
                    is_active=True
                )
                logger.info(f"Created new user with Supabase ID: {user_id}")
                
                # Create a UserProfile for the new user
                from apps.users.models import UserProfile
                
                try:
                    # Try to get an existing profile first
                    user_profile, created = UserProfile.objects.get_or_create(
                        supabase_uid=user_id,
                        defaults={
                            'user': user,
                            'credits_balance': 0  # Start with 0 credits
                        }
                    )
                    
                    # If the profile exists but is linked to a different user, update it
                    if not created and user_profile.user != user:
                        user_profile.user = user
                        user_profile.save()
                        
                    logger.info(f"{'Created' if created else 'Updated'} UserProfile for user with Supabase ID: {user_id}")
                except Exception as e:
                    logger.error(f"Error creating/updating UserProfile: {str(e)}")
            
            # Add Supabase claims to the user object for use in permission checks
            user.supabase_claims = payload.get('claims', {})
            user.supabase_roles = payload.get('roles', [])
            
            return (user, payload)
            
        except ExpiredSignatureError:
            logger.warning("Expired JWT token received")
            raise AuthenticationFailed('Token expired')
            
        except InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            raise AuthenticationFailed('Invalid authentication token')
            
        except Exception as e:
            logger.error(f"JWT validation error: {str(e)}")
            raise AuthenticationFailed('Authentication error')
    
    def authenticate_header(self, request: Request) -> str:
        return 'Bearer'
