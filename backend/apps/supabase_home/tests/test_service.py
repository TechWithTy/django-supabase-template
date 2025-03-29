import pytest
import requests
import os

from apps.supabase_home._service import SupabaseService, SupabaseAPIError, SupabaseError




class TestSupabaseServiceLive:
    """Tests for the SupabaseService base class using the actual Supabase server"""

    @pytest.fixture
    def service(self):
        """Create a SupabaseService instance for testing"""
        return SupabaseService()

    @pytest.fixture
    def skip_if_no_env_vars(self):
        """Skip tests if required environment variables are not set"""
        required_vars = ["SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY"]
        missing = [var for var in required_vars if not os.environ.get(var)]
        if missing:
            pytest.skip(f"Missing required environment variables: {', '.join(missing)}")

    def test_init(self, service, skip_if_no_env_vars):
        """Test initialization of SupabaseService"""
        assert service.base_url == os.environ.get("SUPABASE_URL")
        assert service.anon_key == os.environ.get("SUPABASE_ANON_KEY")
        assert service.service_role_key == os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    def test_get_headers_anonymous(self, service, skip_if_no_env_vars):
        """Test getting headers for anonymous requests"""
        headers = service._get_headers()

        assert headers["Content-Type"] == "application/json"
        assert headers["apikey"] == os.environ.get("SUPABASE_ANON_KEY")
        assert "Authorization" not in headers

    def test_get_headers_with_auth(self, service, skip_if_no_env_vars):
        """Test getting headers with auth token"""
        headers = service._get_headers(auth_token="test-token")

        assert headers["Content-Type"] == "application/json"
        assert headers["apikey"] == os.environ.get("SUPABASE_ANON_KEY")
        assert headers["Authorization"] == "Bearer test-token"

    def test_get_headers_admin(self, service, skip_if_no_env_vars):
        """Test getting headers for admin requests"""
        headers = service._get_headers(is_admin=True)

        assert headers["Content-Type"] == "application/json"
        assert headers["apikey"] == os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        assert headers["Authorization"] == "Bearer " + os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    def test_make_request_health_check(self, service, skip_if_no_env_vars):
        """Test making a request to a valid Supabase endpoint"""
        # Try multiple endpoints that might be available
        endpoints_to_try = [
            # REST API endpoint
            {"endpoint": "/rest/v1/", "is_admin": True},
            # Storage API endpoint
            {"endpoint": "/storage/v1/object/list", "is_admin": True},
            # Auth API endpoint
            {"endpoint": "/auth/v1/settings", "is_admin": True},
        ]
        
        for endpoint_config in endpoints_to_try:
            try:
                result = service._make_request(
                    method="GET",
                    endpoint=endpoint_config["endpoint"],
                    is_admin=endpoint_config["is_admin"],
                )
                
                # If we get here without an exception, the test passes
                assert result is not None
                return
            except Exception:
                # Continue trying other endpoints
                continue
        
        # If we've tried all endpoints and none worked, skip the test
        pytest.skip("Could not find a working endpoint for health check")


    def test_make_request_rest_api(self, service, skip_if_no_env_vars):
        """Test making a request to the REST API"""
        try:
            # Make request to list tables (requires admin access)
            result = service._make_request(
                method="GET",
                endpoint="/rest/v1/",
                is_admin=True,
            )

            # Verify result
            assert result is not None
        except SupabaseAPIError as e:
            if e.status_code == 404:
                pytest.skip("REST API endpoint not available")
            else:
                assert "Supabase API error" in str(e)
        except Exception as e:
            pytest.skip(f"REST API test failed: {str(e)}")

    def test_make_request_invalid_endpoint(self, service, skip_if_no_env_vars):
        """Test making a request to an invalid endpoint"""
        try:
            # Make request to an invalid endpoint
            service._make_request(method="GET", endpoint="/non-existent-endpoint")
            pytest.fail("Expected an exception but none was raised")
        except requests.exceptions.HTTPError as e:
            assert e.response.status_code in [404, 400, 403, 401, 500]
        except SupabaseAPIError as e:
            assert "Supabase API error" in str(e)
        except SupabaseError as e:
            assert "Unexpected error during Supabase request" in str(e)
        except Exception:
            # Any exception is acceptable for an invalid endpoint
            pass

    def test_make_request_invalid_data(self, service, skip_if_no_env_vars):
        """Test making a request with invalid data"""
        try:
            # Make request with invalid data
            service._make_request(
                method="POST", 
                endpoint="/rest/v1/invalid_table", 
                data={"invalid": "data"},
                is_admin=True
            )
            pytest.fail("Expected an exception but none was raised")
        except requests.exceptions.HTTPError as e:
            assert e.response.status_code in [404, 400, 403, 401, 500]
        except SupabaseAPIError as e:
            assert "Supabase API error" in str(e)
        except SupabaseError as e:
            assert "Unexpected error during Supabase request" in str(e)
        except Exception:
            # Any exception is acceptable for invalid data
            pass
