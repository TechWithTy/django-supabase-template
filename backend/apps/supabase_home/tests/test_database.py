import pytest
import os
import uuid
from unittest.mock import patch

from ..database import SupabaseDatabaseService


class TestSupabaseDatabaseService:
    """Tests for the SupabaseDatabaseService class"""

    @pytest.fixture
    def mock_settings(self):
        """Mock Django settings"""
        with patch(" apps.supabase_home._service.settings") as mock_settings:
            # Configure mock settings
            mock_settings.SUPABASE_URL = "https://example.supabase.co"
            mock_settings.SUPABASE_ANON_KEY = "test-anon-key"
            mock_settings.SUPABASE_SERVICE_ROLE_KEY = "test-service-role-key"
            yield mock_settings

    @pytest.fixture
    def db_service(self, mock_settings):
        """Create a SupabaseDatabaseService instance for testing"""
        return SupabaseDatabaseService()

    @patch.object(SupabaseDatabaseService, "_make_request")
    def test_fetch_data(self, mock_make_request, db_service, mock_settings):
        """Test fetching data from a table"""
        # Configure mock response
        mock_make_request.return_value = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
        ]

        # Call fetch_data method
        result = db_service.fetch_data(
            table="test_table",
            auth_token="test-token",
            select="id,name",
            filters={"active": True},
            order="name.asc",
            limit=10,
            offset=0,
        )

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="GET",
            endpoint="/rest/v1/test_table",
            auth_token="test-token",
            params={
                "select": "id,name",
                "active": "eq.true",
                "order": "name.asc",
                "limit": 10,
                "offset": 0,
            },
        )

        # Verify result
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["name"] == "Item 2"

    @patch.object(SupabaseDatabaseService, "_make_request")
    def test_fetch_data_with_complex_filters(
        self, mock_make_request, db_service, mock_settings
    ):
        """Test fetching data with complex filters"""
        # Configure mock response
        mock_make_request.return_value = [{"id": 1, "name": "Item 1"}]

        # Call fetch_data method with complex filters
        result = db_service.fetch_data(
            table="test_table",
            filters={
                "name": {"operator": "like", "value": "Item%"},
                "created_at": {"operator": "gte", "value": "2023-01-01"},
                "status": {"operator": "in", "value": ["active", "pending"]},
            },
        )

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="GET",
            endpoint="/rest/v1/test_table",
            auth_token=None,
            params={
                "select": "*",
                "name": "like.Item%",
                "created_at": "gte.2023-01-01",
                "status": "in.(active,pending)",
            },
        )

        # Verify result
        assert len(result) == 1
        assert result[0]["id"] == 1

    @patch.object(SupabaseDatabaseService, "_make_request")
    def test_insert_data(self, mock_make_request, db_service, mock_settings):
        """Test inserting data into a table"""
        # Configure mock response
        mock_make_request.return_value = [
            {"id": 1, "name": "New Item", "created_at": "2023-01-01T00:00:00Z"}
        ]

        # Call insert_data method
        result = db_service.insert_data(
            table="test_table",
            data={"name": "New Item"},
            auth_token="test-token",
            returning="*",
        )

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="POST",
            endpoint="/rest/v1/test_table",
            auth_token="test-token",
            data={"name": "New Item"},
            params={"select": "*"},
        )

        # Verify result
        assert result[0]["id"] == 1
        assert result[0]["name"] == "New Item"

    @patch.object(SupabaseDatabaseService, "_make_request")
    def test_update_data(self, mock_make_request, db_service, mock_settings):
        """Test updating data in a table"""
        # Configure mock response
        mock_make_request.return_value = [
            {"id": 1, "name": "Updated Item", "updated_at": "2023-01-02T00:00:00Z"}
        ]

        # Call update_data method
        result = db_service.update_data(
            table="test_table",
            data={"name": "Updated Item"},
            filters={"id": 1},
            auth_token="test-token",
            returning="*",
        )

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="PATCH",
            endpoint="/rest/v1/test_table",
            auth_token="test-token",
            data={"name": "Updated Item"},
            params={"id": "eq.1", "select": "*"},
        )

        # Verify result
        assert result[0]["id"] == 1
        assert result[0]["name"] == "Updated Item"

    @patch.object(SupabaseDatabaseService, "_make_request")
    def test_upsert_data(self, mock_make_request, db_service, mock_settings):
        """Test upserting data in a table"""
        # Configure mock response
        mock_make_request.return_value = [
            {"id": 1, "name": "Upserted Item", "updated_at": "2023-01-02T00:00:00Z"}
        ]

        # Call upsert_data method
        result = db_service.upsert_data(
            table="test_table",
            data={"id": 1, "name": "Upserted Item"},
            auth_token="test-token",
            returning="*",
        )

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="POST",
            endpoint="/rest/v1/test_table",
            auth_token="test-token",
            data={"id": 1, "name": "Upserted Item"},
            params={"select": "*", "upsert": "true"},
        )

        # Verify result
        assert result[0]["id"] == 1
        assert result[0]["name"] == "Upserted Item"

    @patch.object(SupabaseDatabaseService, "_make_request")
    def test_delete_data(self, mock_make_request, db_service, mock_settings):
        """Test deleting data from a table"""
        # Configure mock response
        mock_make_request.return_value = [{"id": 1, "name": "Deleted Item"}]

        # Call delete_data method
        result = db_service.delete_data(
            table="test_table",
            filters={"id": 1},
            auth_token="test-token",
            returning="*",
        )

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="DELETE",
            endpoint="/rest/v1/test_table",
            auth_token="test-token",
            params={"id": "eq.1", "select": "*"},
        )

        # Verify result
        assert result[0]["id"] == 1
        assert result[0]["name"] == "Deleted Item"

    @patch.object(SupabaseDatabaseService, "_make_request")
    def test_execute_sql(self, mock_make_request, db_service, mock_settings):
        """Test executing SQL directly"""
        # Configure mock response
        mock_make_request.return_value = [{"id": 1, "count": 10}]

        # Call execute_sql method
        result = db_service.execute_sql(
            sql="SELECT id, COUNT(*) as count FROM test_table GROUP BY id",
            auth_token="test-token",
        )

        # Verify request was made correctly
        mock_make_request.assert_called_once_with(
            method="POST",
            endpoint="/rest/v1/rpc/exec_sql",
            auth_token="test-token",
            data={"query": "SELECT id, COUNT(*) as count FROM test_table GROUP BY id"},
        )

        # Verify result
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["count"] == 10


class TestRealSupabaseDatabaseService:
    """Real-world integration tests for SupabaseDatabaseService
    
    These tests make actual API calls to Supabase and require:
    1. A valid Supabase URL and API keys in env variables
    2. Use of the --integration flag when running tests
    3. A test table must exist in your Supabase instance
    """
    
    @pytest.fixture
    def db_service(self):
        """Create a real SupabaseDatabaseService instance"""
        return SupabaseDatabaseService()
    
    @pytest.fixture
    def test_table_name(self):
        """Get test table name from environment or use default"""
        return os.getenv("TEST_TABLE_NAME", "test_table")
    
    @pytest.fixture
    def test_record(self):
        """Create a unique test record"""
        return {
            "name": f"Test Item {uuid.uuid4()}",
            "description": "Created by automated test",
            "is_active": True
        }
    
    @pytest.mark.skipif(
        not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_ANON_KEY"),
        reason="Supabase credentials not set in environment variables",
    )
    def test_real_database_operations(self, db_service, test_table_name, test_record):
        """Test the full CRUD cycle with a real Supabase database"""
        # Skip if not using --integration flag
        if os.getenv("SKIP_INTEGRATION_TESTS", "true").lower() == "true":
            pytest.skip("Integration tests disabled")
        
        try:
            # 1. Insert test data
            insert_result = db_service.insert_data(
                table=test_table_name,
                data=test_record,
                returning="*"
            )
            
            assert insert_result is not None
            assert len(insert_result) > 0
            assert "id" in insert_result[0]
            assert insert_result[0]["name"] == test_record["name"]
            
            # Store the ID for subsequent operations
            record_id = insert_result[0]["id"]
            
            # 2. Fetch the inserted data
            fetch_result = db_service.fetch_data(
                table=test_table_name,
                filters={"id": record_id}
            )
            
            assert fetch_result is not None
            assert len(fetch_result) == 1
            assert fetch_result[0]["id"] == record_id
            assert fetch_result[0]["name"] == test_record["name"]
            
            # 3. Update the data
            updated_data = {"description": "Updated by automated test"}
            update_result = db_service.update_data(
                table=test_table_name,
                data=updated_data,
                filters={"id": record_id},
                returning="*"
            )
            
            assert update_result is not None
            assert len(update_result) == 1
            assert update_result[0]["id"] == record_id
            assert update_result[0]["description"] == updated_data["description"]
            
            # 4. Delete the test data to clean up
            delete_result = db_service.delete_data(
                table=test_table_name,
                filters={"id": record_id},
                returning="*"
            )
            
            assert delete_result is not None
            assert len(delete_result) == 1
            assert delete_result[0]["id"] == record_id
            
            # 5. Verify deletion by attempting to fetch
            empty_result = db_service.fetch_data(
                table=test_table_name,
                filters={"id": record_id}
            )
            
            assert len(empty_result) == 0
            
        except Exception as e:
            pytest.fail(f"Real-world Supabase database test failed: {str(e)}")
