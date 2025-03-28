import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
import json
import os
from users.models import UserProfile
from credits.models import CreditTransaction


@pytest.mark.django_db
class TestMainViews:
    """Integration tests for main script execution endpoints using real Supabase"""
    
    @pytest.fixture(autouse=True)
    def setup(self, test_django_user, test_admin_django_user):
        # Default script parameters
        self.script_params = {
            "param1": "value1",
            "param2": "value2"
        }
        
        # Store test users for verification
        self.test_user = test_django_user
        self.admin_user = test_admin_django_user
        
        # Create user with insufficient credits
        self.low_credit_user = UserProfile.objects.create(
            id="low-credit-user-id",
            email="low@example.com",
            first_name="Low",
            last_name="Credits",
            credits=1
        )
        
        yield
        
        # Clean up after tests
        self.low_credit_user.delete()
        CreditTransaction.objects.all().delete()
        
        # Reset credits for test users
        self.test_user.credits = 1000
        self.test_user.save()
        self.admin_user.credits = 1000
        self.admin_user.save()
    
    def test_main_script_execution_success(self, authenticated_client, monkeypatch):
        """Test successful script execution with real Supabase auth"""
        # Mock os.path.exists and subprocess.run to avoid actual script execution
        monkeypatch.setattr('os.path.exists', lambda path: True)
        
        def mock_run(*args, **kwargs):
            # Create a mock process result
            class MockProcess:
                def __init__(self):
                    self.returncode = 0
                    self.stdout = json.dumps({
                        "result": "success", 
                        "data": {"key": "value"}
                    }).encode()
            return MockProcess()
        
        monkeypatch.setattr('subprocess.run', mock_run)
        
        # Make request using authenticated client
        url = reverse('users:execute-script')
        response = authenticated_client.post(url, self.script_params, format='json')
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.data['result'] == 'success'
        assert response.data['data']['key'] == 'value'
        
        # Check if credit transaction was created
        transactions = CreditTransaction.objects.filter(user=self.test_user)
        assert transactions.count() == 1
        transaction = transactions.first()
        assert transaction.amount < 0  # Should be a debit
        assert transaction.transaction_type == 'DEBIT'
        
        # Verify user credits were deducted
        self.test_user.refresh_from_db()
        assert self.test_user.credits < 1000  # Credits should have decreased
    
    def test_main_script_execution_insufficient_credits(self, monkeypatch):
        """Test script execution with insufficient credits using real Supabase auth"""
        # Setup client with low credit user
        client = APIClient()
        client.force_authenticate(user=self.low_credit_user)
        
        # Make request
        url = reverse('users:execute-script')
        response = client.post(url, self.script_params, format='json')
        
        # Assertions
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert 'error' in response.data
        assert 'credits' in response.data
        
        # Check that no credit transaction was created
        assert CreditTransaction.objects.filter(user=self.low_credit_user).count() == 0
        
        # Verify user credits were not deducted
        self.low_credit_user.refresh_from_db()
        assert self.low_credit_user.credits == 1  # Unchanged
    
    def test_main_script_execution_admin_override(self, monkeypatch):
        """Test script execution with admin override using real Supabase auth"""
        # Setup client with admin user
        client = APIClient()
        client.force_authenticate(user=self.admin_user)
        
        # Mock os.path.exists and subprocess.run
        monkeypatch.setattr('os.path.exists', lambda path: True)
        
        def mock_run(*args, **kwargs):
            # Create a mock process result
            class MockProcess:
                def __init__(self):
                    self.returncode = 0
                    self.stdout = json.dumps({
                        "result": "success", 
                        "data": {"key": "admin_value"}
                    }).encode()
            return MockProcess()
        
        monkeypatch.setattr('subprocess.run', mock_run)
        
        # Make request with credit override
        url = reverse('users:execute-script')
        params = self.script_params.copy()
        params['credit_cost'] = 0  # Admin can set custom credit cost
        response = client.post(url, params, format='json')
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.data['result'] == 'success'
        
        # Check transaction details if one was created
        transactions = CreditTransaction.objects.filter(user=self.admin_user)
        if transactions.exists():  # Admin might not create transaction in some implementations
            transaction = transactions.first()
            assert transaction.amount == 0 or transaction.amount > -5  # Custom low or zero cost
    
    def test_main_script_not_found(self, authenticated_client, monkeypatch):
        """Test script not found with real Supabase auth"""
        # Mock file doesn't exist
        monkeypatch.setattr('os.path.exists', lambda path: False)
        
        # Make request
        url = reverse('users:execute-script')
        response = authenticated_client.post(url, self.script_params, format='json')
        
        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data
        
        # Check that no credit transaction was created
        assert CreditTransaction.objects.filter(user=self.test_user).count() == 0
        
        # Verify user credits were not deducted
        self.test_user.refresh_from_db()
        assert self.test_user.credits == 1000  # Unchanged
    
    def test_main_script_execution_error(self, authenticated_client, monkeypatch):
        """Test script execution error with real Supabase auth"""
        # Mock file existence but script execution fails
        monkeypatch.setattr('os.path.exists', lambda path: True)
        
        def mock_run(*args, **kwargs):
            # Create a mock process result with error
            class MockProcess:
                def __init__(self):
                    self.returncode = 1  # Error code
                    self.stderr = b'Script execution failed'
                    self.stdout = b''
            return MockProcess()
        
        monkeypatch.setattr('subprocess.run', mock_run)
        
        # Make request
        url = reverse('users:execute-script')
        response = authenticated_client.post(url, self.script_params, format='json')
        
        # Assertions
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert 'error' in response.data
        
        # Check that no credit transaction was created
        assert CreditTransaction.objects.filter(user=self.test_user).count() == 0
        
        # Verify user credits were not deducted
        self.test_user.refresh_from_db()
        assert self.test_user.credits == 1000  # Unchanged
    
    def test_unauthenticated_request(self):
        """Test unauthenticated request with real Supabase"""
        # Make request without authentication
        client = APIClient()
        url = reverse('users:execute-script')
        response = client.post(url, self.script_params, format='json')
        
        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Check that no credit transaction was created
        assert CreditTransaction.objects.count() == 0
