from .auth import SupabaseAuthService
from .database import SupabaseDatabaseService
from .storage import SupabaseStorageService
from .edge_functions import SupabaseEdgeFunctionsService
from .realtime import SupabaseRealtimeService

class SupabaseClient:
    """
    Client for interacting with all Supabase services.
    
    This class provides a unified interface to access all Supabase services:
    - Auth
    - Database
    - Storage
    - Edge Functions
    - Realtime
    """
    
    def __init__(self):
        self.auth = SupabaseAuthService()
        self.database = SupabaseDatabaseService()
        self.storage = SupabaseStorageService()
        self.edge_functions = SupabaseEdgeFunctionsService()
        self.realtime = SupabaseRealtimeService()
        
    def get_auth_service(self) -> SupabaseAuthService:
        """
        Get the Auth service.
        
        Returns:
            SupabaseAuthService instance
        """
        return self.auth
    
    def get_database_service(self) -> SupabaseDatabaseService:
        """
        Get the Database service.
        
        Returns:
            SupabaseDatabaseService instance
        """
        return self.database
    
    def get_storage_service(self) -> SupabaseStorageService:
        """
        Get the Storage service.
        
        Returns:
            SupabaseStorageService instance
        """
        return self.storage
    
    def get_edge_functions_service(self) -> SupabaseEdgeFunctionsService:
        """
        Get the Edge Functions service.
        
        Returns:
            SupabaseEdgeFunctionsService instance
        """
        return self.edge_functions
    
    def get_realtime_service(self) -> SupabaseRealtimeService:
        """
        Get the Realtime service.
        
        Returns:
            SupabaseRealtimeService instance
        """
        return self.realtime

# Create a singleton instance
supabase = SupabaseClient()
