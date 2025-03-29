from django.db.models import Model, QuerySet
from django.db.models.query import Prefetch
from typing import Any, Dict, List, Optional, Type, Union


class QueryOptimizer:
    """
    A utility class for optimizing Django database queries by intelligently
    using select_related and prefetch_related to reduce the number of database queries.
    """
    
    @staticmethod
    def optimize_single_object_query(model_class: Type[Model], 
                                    query_params: Dict[str, Any],
                                    select_related_fields: Optional[List[str]] = None,
                                    prefetch_related_fields: Optional[List[str]] = None,
                                    prefetch_related_querysets: Optional[List[Prefetch]] = None) -> Optional[Model]:
        """
        Optimizes a query for retrieving a single object by using select_related and prefetch_related.
        
        Args:
            model_class: The Django model class to query
            query_params: Dictionary of query parameters to filter the object
            select_related_fields: List of field names for select_related (OneToOne or ForeignKey relationships)
            prefetch_related_fields: List of field names for prefetch_related (ManyToMany or reverse relationships)
            prefetch_related_querysets: List of Prefetch objects for more complex prefetch operations
            
        Returns:
            A single model instance or None if not found
        """
        queryset = model_class.objects.filter(**query_params)
        
        if select_related_fields:
            queryset = queryset.select_related(*select_related_fields)
            
        if prefetch_related_fields:
            queryset = queryset.prefetch_related(*prefetch_related_fields)
            
        if prefetch_related_querysets:
            for prefetch_qs in prefetch_related_querysets:
                queryset = queryset.prefetch_related(prefetch_qs)
        
        try:
            return queryset.get()
        except model_class.DoesNotExist:
            return None
    
    @staticmethod
    def optimize_queryset(queryset: QuerySet,
                         select_related_fields: Optional[List[str]] = None,
                         prefetch_related_fields: Optional[List[str]] = None,
                         prefetch_related_querysets: Optional[List[Prefetch]] = None) -> QuerySet:
        """
        Optimizes an existing queryset by adding select_related and prefetch_related.
        
        Args:
            queryset: The existing queryset to optimize
            select_related_fields: List of field names for select_related
            prefetch_related_fields: List of field names for prefetch_related
            prefetch_related_querysets: List of Prefetch objects for complex prefetch operations
            
        Returns:
            An optimized queryset
        """
        if select_related_fields:
            queryset = queryset.select_related(*select_related_fields)
            
        if prefetch_related_fields:
            queryset = queryset.prefetch_related(*prefetch_related_fields)
            
        if prefetch_related_querysets:
            for prefetch_qs in prefetch_related_querysets:
                queryset = queryset.prefetch_related(prefetch_qs)
                
        return queryset


class OptimizedQuerySetMixin:
    """
    A mixin for Django views that adds methods for optimizing querysets with
    select_related and prefetch_related.
    
    This can be used with Django's class-based views like ListView, DetailView, etc.
    """
    
    select_related_fields: List[str] = []
    prefetch_related_fields: List[str] = []
    prefetch_related_querysets: List[Prefetch] = []
    
    def get_queryset(self):
        """
        Override the default get_queryset method to apply optimizations.
        """
        queryset = super().get_queryset()
        return self._optimize_queryset(queryset)
    
    def _optimize_queryset(self, queryset):
        """
        Apply select_related and prefetch_related optimizations to a queryset.
        """
        # Apply select_related if fields are defined
        if self.select_related_fields:
            queryset = queryset.select_related(*self.select_related_fields)
        
        # Apply prefetch_related for regular fields
        if self.prefetch_related_fields:
            queryset = queryset.prefetch_related(*self.prefetch_related_fields)
        
        # Apply complex prefetch_related operations
        if self.prefetch_related_querysets:
            for prefetch_qs in self.prefetch_related_querysets:
                queryset = queryset.prefetch_related(prefetch_qs)
        
        return queryset


# Common optimization patterns for the UserProfile model and related models
def get_optimized_user_profile(user_id: Union[str, int]) -> Optional[Model]:
    """
    Get a UserProfile with all commonly needed related objects prefetched.
    
    Args:
        user_id: The primary key of the user
        
    Returns:
        UserProfile object with optimized queries or None if not found
    """
    from apps.users.models import UserProfile
    
    return QueryOptimizer.optimize_single_object_query(
        model_class=UserProfile,
        query_params={'user_id': user_id},
        select_related_fields=['user'],
        # Add other related fields if needed
    )
