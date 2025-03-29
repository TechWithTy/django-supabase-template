from typing import Optional, Any
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.request import Request


class IPRateThrottle(AnonRateThrottle):
    """
    Throttle class that limits requests based on IP address for both authenticated and anonymous users.
    
    This throttle provides an additional layer of security by limiting requests from a single IP address,
    helping to prevent brute force attacks, DDoS attacks, and other forms of API abuse.
    """
    scope = 'ip'
    
    def get_cache_key(self, request: Request, view: Any) -> Optional[str]:
        """
        Get a unique cache key for the current request based on the client's IP address.
        
        This method uses X-Forwarded-For header if available (for requests behind a proxy),
        otherwise it falls back to REMOTE_ADDR.
        """
        # Get the client's IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Take the first IP in case of multiple proxies
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        # Create a unique cache key for this IP address and view
        return f"ip_throttle_{ip}_{self.scope}"


class IPBasedUserRateThrottle(UserRateThrottle):
    """
    Throttle class that limits requests based on both user ID and IP address.
    
    This provides more granular control by tracking rate limits per user per IP address,
    which helps prevent credential sharing and API abuse from multiple locations.
    """
    scope = 'user_ip'
    
    def get_cache_key(self, request: Request, view: Any) -> Optional[str]:
        """
        Get a unique cache key combining both user ID and IP address.
        """
        if not request.user.is_authenticated:
            return None  # Let AnonRateThrottle handle anonymous users
        
        # Get the client's IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        # Create a unique cache key for this user and IP combination
        return f"user_ip_throttle_{request.user.pk}_{ip}_{self.scope}"
