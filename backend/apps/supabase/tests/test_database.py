import pytest
from unittest.mock import patch, MagicMock

from ..database import SupabaseDatabaseService


class TestSupabaseDatabaseService:
    """Tests for the SupabaseDatabaseService class"""

    @pytest.fixture
    def db_service(self):
        """Create a SupabaseDatabaseService instance for testing"""
        with patch('apps.supabase.service.settings') as mock_settings:
            # Configure mock settings
            mock_settings.SUPABASE_DB_CONNECTION_STRING = 'https://example.supabase.co'
            mock_settings.SUPABASE_ANON_KEY = 'test-anon-key'
            mock_settings.SUPABASE_SERVICE_ROLE_KEY = 'test-service-role-key'
            
            db_service = SupabaseDatabaseService()
            return db_service
    
    @patch.object(SupabaseDatabaseService, '_make_request')
    def test_fetch_data(self, mock_make_request, db_service):
        """Test fetching data from a table"""
        # Configure mock response
        mock_make_request.return_value = [
            {'id': 1, 'name': 'Item 1'},
            {'id': 2, 'name': 'Item 2'}
        ]
        
        # Call fetch_data method
        result = db_service.fetch_data(
            table='test_table',
            auth_token='test-token',
            select='id,name',
            filters={'active': True},
            order='name.asc',
            limit=10,
            offset=0
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='GET',
            endpoint='/rest/v1/test_table',
            auth_token='test-token',
            params={
                'select': 'id,name',
                'active': 'eq.true',
                'order': 'name.asc',
                'limit': 10,
                'offset': 0
            }
        )
        
        # Verify result
        assert len(result) == 2
        assert result[0]['id'] == 1
        assert result[1]['name'] == 'Item 2'
    
    @patch.object(SupabaseDatabaseService, '_make_request')
    def test_fetch_data_with_complex_filters(self, mock_make_request, db_service):
        """Test fetching data with complex filters"""
        # Configure mock response
        mock_make_request.return_value = [
            {'id': 1, 'name': 'Item 1'}
        ]
        
        # Call fetch_data method with complex filters
        result = db_service.fetch_data(
            table='test_table',
            filters={
                'name': {'operator': 'like', 'value': 'Item%'},
                'created_at': {'operator': 'gte', 'value': '2023-01-01'},
                'status': {'operator': 'in', 'value': ['active', 'pending']}
            }
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='GET',
            endpoint='/rest/v1/test_table',
            auth_token=None,
            params={
                'select': '*',
                'name': 'like.Item%',
                'created_at': 'gte.2023-01-01',
                'status': 'in.(active,pending)'
            }
        )
        
        # Verify result
        assert len(result) == 1
        assert result[0]['id'] == 1
    
    @patch.object(SupabaseDatabaseService, '_make_request')
    def test_insert_data(self, mock_make_request, db_service):
        """Test inserting data into a table"""
        # Configure mock response
        mock_make_request.return_value = [
            {'id': 1, 'name': 'New Item', 'created_at': '2023-01-01T00:00:00Z'}
        ]
        
        # Call insert_data method
        result = db_service.insert_data(
            table='test_table',
            data={'name': 'New Item'},
            auth_token='test-token',
            returning='*'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='POST',
            endpoint='/rest/v1/test_table',
            auth_token='test-token',
            data={'name': 'New Item'},
            params={'select': '*'}
        )
        
        # Verify result
        assert result[0]['id'] == 1
        assert result[0]['name'] == 'New Item'
    
    @patch.object(SupabaseDatabaseService, '_make_request')
    def test_update_data(self, mock_make_request, db_service):
        """Test updating data in a table"""
        # Configure mock response
        mock_make_request.return_value = [
            {'id': 1, 'name': 'Updated Item', 'updated_at': '2023-01-02T00:00:00Z'}
        ]
        
        # Call update_data method
        result = db_service.update_data(
            table='test_table',
            data={'name': 'Updated Item'},
            filters={'id': 1},
            auth_token='test-token',
            returning='*'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='PATCH',
            endpoint='/rest/v1/test_table',
            auth_token='test-token',
            data={'name': 'Updated Item'},
            params={'id': 'eq.1', 'select': '*'}
        )
        
        # Verify result
        assert result[0]['id'] == 1
        assert result[0]['name'] == 'Updated Item'
    
    @patch.object(SupabaseDatabaseService, '_make_request')
    def test_upsert_data(self, mock_make_request, db_service):
        """Test upserting data in a table"""
        # Configure mock response
        mock_make_request.return_value = [
            {'id': 1, 'name': 'Upserted Item', 'updated_at': '2023-01-02T00:00:00Z'}
        ]
        
        # Call upsert_data method
        result = db_service.upsert_data(
            table='test_table',
            data={'id': 1, 'name': 'Upserted Item'},
            auth_token='test-token',
            returning='*'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='POST',
            endpoint='/rest/v1/test_table',
            auth_token='test-token',
            data={'id': 1, 'name': 'Upserted Item'},
            params={'select': '*', 'upsert': 'true'}
        )
        
        # Verify result
        assert result[0]['id'] == 1
        assert result[0]['name'] == 'Upserted Item'
    
    @patch.object(SupabaseDatabaseService, '_make_request')
    def test_delete_data(self, mock_make_request, db_service):
        """Test deleting data from a table"""
        # Configure mock response
        mock_make_request.return_value = [
            {'id': 1, 'name': 'Deleted Item'}
        ]
        
        # Call delete_data method
        result = db_service.delete_data(
            table='test_table',
            filters={'id': 1},
            auth_token='test-token',
            returning='*'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='DELETE',
            endpoint='/rest/v1/test_table',
            auth_token='test-token',
            params={'id': 'eq.1', 'select': '*'}
        )
        
        # Verify result
        assert result[0]['id'] == 1
        assert result[0]['name'] == 'Deleted Item'
    
    @patch.object(SupabaseDatabaseService, '_make_request')
    def test_execute_function(self, mock_make_request, db_service):
        """Test executing a PostgreSQL function"""
        # Configure mock response
        mock_make_request.return_value = [
            {'result': 'Function result'}
        ]
        
        # Call execute_function method
        result = db_service.execute_function(
            function_name='test_function',
            params={'param1': 'value1', 'param2': 'value2'},
            auth_token='test-token'
        )
        
        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method='POST',
            endpoint='/rest/v1/rpc/test_function',
            auth_token='test-token',
            data={'param1': 'value1', 'param2': 'value2'}
        )
        
        # Verify result
        assert result[0]['result'] == 'Function result'
