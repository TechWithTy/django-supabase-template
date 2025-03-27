# Re-export SupabaseService from _service.py for compatibility with tests
from ._service import SupabaseService, SupabaseError, SupabaseAuthError, SupabaseAPIError

__all__ = ['SupabaseService', 'SupabaseError', 'SupabaseAuthError', 'SupabaseAPIError']
