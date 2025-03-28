import pytest
from django.urls import reverse
from rest_framework import status
import uuid


@pytest.mark.django_db
class TestDatabaseViews:
    """Integration tests for Supabase database endpoints"""

    def test_get_table_data(self, authenticated_client, test_user_credentials, test_table, supabase_services):
        """Test getting data from a database table with real Supabase API"""
        # Skip if no test table available
        if not test_table:
            pytest.skip("No test table available")
            
        # Insert test data into the table
        database_service = supabase_services['database']
        auth_token = test_user_credentials['auth_token']
        
        # Create test record
        test_id = str(uuid.uuid4())
        test_data = {
            'id': test_id,
            'name': f'Test Record {uuid.uuid4()}',
            'description': 'Test record for database integration test',
            'user_id': test_user_credentials['id']
        }
        
        # Insert data using the Supabase service
        database_service.insert(
            table=test_table,
            data=test_data,
            auth_token=auth_token
        )
        
        # Make request to the endpoint
        url = reverse('users:database-get-table-data')
        response = authenticated_client.post(url, {'table': test_table}, format='json')
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert 'data' in response.data
        assert isinstance(response.data['data'], list)
        assert len(response.data['data']) >= 1
        
    def test_insert_data(self, authenticated_client, test_user_credentials, test_table):
        """Test inserting data into a database table with real Supabase API"""
        # Skip if no test table available
        if not test_table:
            pytest.skip("No test table available")
            
        # Test data
        test_id = str(uuid.uuid4())
        test_data = {
            'id': test_id,
            'name': f'Test Record {uuid.uuid4()}',
            'description': 'Test record for database integration test',
            'user_id': test_user_credentials['id']
        }
        
        # Make request
        url = reverse('users:database-insert-data')
        request_data = {
            'table': test_table,
            'data': test_data
        }
        response = authenticated_client.post(url, request_data, format='json')
        
        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        assert 'data' in response.data
        assert isinstance(response.data['data'], list)
        assert len(response.data['data']) == 1
        assert response.data['data'][0]['id'] == test_id
        
    def test_update_data(self, authenticated_client, test_user_credentials, test_table, supabase_services):
        """Test updating data in a database table with real Supabase API"""
        # Skip if no test table available
        if not test_table:
            pytest.skip("No test table available")
            
        # Insert test data to update later
        database_service = supabase_services['database']
        auth_token = test_user_credentials['auth_token']
        
        # Create test record
        test_id = str(uuid.uuid4())
        test_data = {
            'id': test_id,
            'name': 'Original Name',
            'description': 'Original description',
            'user_id': test_user_credentials['id']
        }
        
        # Insert data using the Supabase service
        database_service.insert(
            table=test_table,
            data=test_data,
            auth_token=auth_token
        )
        
        # Updated data
        updated_data = {
            'name': 'Updated Name',
            'description': 'Updated description'
        }
        
        # Make request
        url = reverse('users:database-update-data')
        request_data = {
            'table': test_table,
            'id': test_id,
            'data': updated_data
        }
        response = authenticated_client.put(url, request_data, format='json')
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert 'data' in response.data
        assert len(response.data['data']) == 1
        assert response.data['data'][0]['id'] == test_id
        assert response.data['data'][0]['name'] == 'Updated Name'
        assert response.data['data'][0]['description'] == 'Updated description'
        
    def test_delete_data(self, authenticated_client, test_user_credentials, test_table, supabase_services):
        """Test deleting data from a database table with real Supabase API"""
        # Skip if no test table available
        if not test_table:
            pytest.skip("No test table available")
            
        # Insert test data to delete later
        database_service = supabase_services['database']
        auth_token = test_user_credentials['auth_token']
        
        # Create test record
        test_id = str(uuid.uuid4())
        test_data = {
            'id': test_id,
            'name': f'Test Record to Delete {uuid.uuid4()}',
            'description': 'This record will be deleted',
            'user_id': test_user_credentials['id']
        }
        
        # Insert data using the Supabase service
        database_service.insert(
            table=test_table,
            data=test_data,
            auth_token=auth_token
        )
        
        # Make request
        url = reverse('users:database-delete-data')
        request_data = {
            'table': test_table,
            'id': test_id
        }
        response = authenticated_client.delete(url, request_data, format='json')
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert 'data' in response.data
        
        # Verify data is deleted
        get_url = reverse('users:database-get-table-data')
        get_response = authenticated_client.post(get_url, {'table': test_table, 'filter': {'id': test_id}}, format='json')
        assert len(get_response.data['data']) == 0
        
    def test_execute_sql(self, authenticated_client, test_user_credentials, test_table):
        """Test executing SQL with real Supabase API"""
        # Skip if no test table available
        if not test_table:
            pytest.skip("No test table available")
        
        # Test SQL
        sql = f"SELECT * FROM {test_table} LIMIT 5"
        
        # Make request
        url = reverse('users:database-execute-sql')
        request_data = {'sql': sql}
        response = authenticated_client.post(url, request_data, format='json')
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert 'data' in response.data
