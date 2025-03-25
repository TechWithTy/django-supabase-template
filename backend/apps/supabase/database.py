from typing import Any, Dict, List, Optional, Union

from ._service import SupabaseService

class SupabaseDatabaseService(SupabaseService):
    """
    Service for interacting with Supabase Database (PostgreSQL) API.
    
    This class provides methods for database operations using Supabase's
    RESTful API for PostgreSQL.
    """
    
    def fetch_data(self, 
                  table: str, 
                  auth_token: Optional[str] = None,
                  select: str = "*", 
                  filters: Optional[Dict[str, Any]] = None,
                  order: Optional[str] = None,
                  limit: Optional[int] = None,
                  offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch data from a table with optional filtering, ordering, and pagination.
        
        Args:
            table: Table name
            auth_token: Optional JWT token for authenticated requests
            select: Columns to select (default: "*")
            filters: Optional filters as dictionary
            order: Optional order by clause
            limit: Optional limit of rows to return
            offset: Optional offset for pagination
            
        Returns:
            List of rows as dictionaries
        """
        endpoint = f"/rest/v1/{table}"
        params = {"select": select}
        
        # Add filters if provided
        if filters:
            for key, value in filters.items():
                params[key] = value
                
        # Add ordering if provided
        if order:
            params["order"] = order
            
        # Add pagination if provided
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
            
        return self._make_request(
            method="GET",
            endpoint=endpoint,
            auth_token=auth_token,
            params=params,
            headers={"Prefer": "return=representation"}
        )
    
    def insert_data(self, 
                   table: str, 
                   data: Union[Dict[str, Any], List[Dict[str, Any]]], 
                   auth_token: Optional[str] = None,
                   upsert: bool = False) -> List[Dict[str, Any]]:
        """
        Insert data into a table.
        
        Args:
            table: Table name
            data: Data to insert (single record or list of records)
            auth_token: Optional JWT token for authenticated requests
            upsert: Whether to upsert (update on conflict)
            
        Returns:
            Inserted data
        """
        endpoint = f"/rest/v1/{table}"
        headers = {"Prefer": "return=representation"}
        
        if upsert:
            headers["Prefer"] = "resolution=merge-duplicates,return=representation"
            
        return self._make_request(
            method="POST",
            endpoint=endpoint,
            auth_token=auth_token,
            data=data,
            headers=headers
        )
    
    def update_data(self, 
                   table: str, 
                   data: Dict[str, Any], 
                   filters: Dict[str, Any],
                   auth_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Update data in a table.
        
        Args:
            table: Table name
            data: Data to update
            filters: Filters to identify rows to update
            auth_token: Optional JWT token for authenticated requests
            
        Returns:
            Updated data
        """
        endpoint = f"/rest/v1/{table}"
        params = filters
        
        return self._make_request(
            method="PATCH",
            endpoint=endpoint,
            auth_token=auth_token,
            data=data,
            params=params,
            headers={"Prefer": "return=representation"}
        )
    
    def upsert_data(self, 
                   table: str, 
                   data: Union[Dict[str, Any], List[Dict[str, Any]]], 
                   auth_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Upsert data in a table (insert or update).
        
        Args:
            table: Table name
            data: Data to upsert
            auth_token: Optional JWT token for authenticated requests
            
        Returns:
            Upserted data
        """
        return self.insert_data(table, data, auth_token, upsert=True)
    
    def delete_data(self, 
                   table: str, 
                   filters: Dict[str, Any],
                   auth_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Delete data from a table.
        
        Args:
            table: Table name
            filters: Filters to identify rows to delete
            auth_token: Optional JWT token for authenticated requests
            
        Returns:
            Deleted data
        """
        endpoint = f"/rest/v1/{table}"
        params = filters
        
        return self._make_request(
            method="DELETE",
            endpoint=endpoint,
            auth_token=auth_token,
            params=params,
            headers={"Prefer": "return=representation"}
        )
    
    def call_function(self, 
                     function_name: str, 
                     params: Optional[Dict[str, Any]] = None,
                     auth_token: Optional[str] = None) -> Any:
        """
        Call a PostgreSQL function.
        
        Args:
            function_name: Function name
            params: Function parameters
            auth_token: Optional JWT token for authenticated requests
            
        Returns:
            Function result
        """
        endpoint = f"/rest/v1/rpc/{function_name}"
        
        return self._make_request(
            method="POST",
            endpoint=endpoint,
            auth_token=auth_token,
            data=params or {}
        )
