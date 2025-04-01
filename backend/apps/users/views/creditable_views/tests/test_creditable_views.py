import os
import pytest
from django.urls import reverse
from django.conf import settings
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import UserProfile
from unittest.mock import patch

# Use pytest.mark.django_db to manage database access
@pytest.mark.django_db(transaction=True)
class TestCreditableViews:
    """
    End-to-end tests for the creditable views functionality.
    
    These tests verify that the credit-based access control works correctly
    for both the decorator-based and utility function approaches.
    """
    
    # Add databases attribute to include all required databases
    databases = {"default", "local", "supabase"}
    
    @pytest.fixture(autouse=True)
    def disable_db_routers(self, monkeypatch):
        """Disable database routers for all tests in this class"""
        monkeypatch.setattr(settings, 'DATABASE_ROUTERS', [])
    
    @pytest.fixture
    def api_client(self):
        """Return an unauthenticated API client"""
        return APIClient()
    
    @pytest.fixture
    def user_with_credits(self, django_user_model):
        """Create a regular user with a specific number of credits"""
        user = django_user_model.objects.create_user(
            username='credituser',
            email='credituser@example.com',
            password='testpassword123'
        )
        # Profile is necessary for the tests even if not used in this fixture
        UserProfile.objects.create(
            user=user,
            supabase_uid='credit_test_user',
            credits_balance=10  # Start with 10 credits
        )
        return user
    
    @pytest.fixture
    def admin_user(self, django_user_model):
        """Create an admin user"""
        admin = django_user_model.objects.create_user(
            username='adminuser',
            email='adminuser@example.com',
            password='testpassword123',
            is_staff=True,
            is_superuser=True
        )
        # Profile is necessary for the tests even if not used in this fixture
        UserProfile.objects.create(
            user=admin,
            supabase_uid='admin_test_user',
            credits_balance=5  # Start with 5 credits
        )
        return admin
    
    @pytest.fixture
    def user_without_credits(self, django_user_model):
        """Create a user with zero credits"""
        user = django_user_model.objects.create_user(
            username='brokecredituser',
            email='brokecredituser@example.com',
            password='testpassword123'
        )
        # Profile is necessary for the tests even if not used in this fixture
        UserProfile.objects.create(
            user=user,
            supabase_uid='broke_credit_test_user',
            credits_balance=0  # No credits
        )
        return user
    
    @pytest.fixture
    def authenticated_client(self, api_client, user_with_credits):
        """Return an API client authenticated as a regular user with credits"""
        api_client.force_authenticate(user=user_with_credits)
        return api_client
    
    @pytest.fixture
    def admin_client(self, api_client, admin_user):
        """Return an API client authenticated as an admin user"""
        api_client.force_authenticate(user=admin_user)
        return api_client
    
    @pytest.fixture
    def broke_client(self, api_client, user_without_credits):
        """Return an API client authenticated as a user with no credits"""
        api_client.force_authenticate(user=user_without_credits)
        return api_client
    
    @pytest.fixture(scope="class")
    def create_test_script(self):
        """Create a temporary main.py script for testing"""
        # Get the path to the root directory
        import django
        from pathlib import Path
        root_dir = Path(django.conf.settings.BASE_DIR).parent
        script_path = root_dir / "main.py"
        
        # Create a simple test script
        script_content = """
#!/usr/bin/env python
import sys
import json
import argparse

def main():
    parser = argparse.ArgumentParser(description='Test script for creditable views')
    parser.add_argument('--param1', help='First parameter')
    parser.add_argument('--param2', help='Second parameter')
    args = parser.parse_args()
    
    result = {
        "result": "success",
        "params": {
            "param1": args.param1,
            "param2": args.param2
        }
    }
    
    print(json.dumps(result))
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""
        
        # Only create the script if it doesn't already exist
        if not script_path.exists():
            with open(script_path, 'w') as f:
                f.write(script_content)
        
        yield script_path
        
        # Cleanup - remove the script if we created it
        if script_path.exists():
            os.remove(script_path)
    
    def test_execute_main_script_success(self, authenticated_client, create_test_script, user_with_credits):
        """Test successful execution of main script with credit deduction"""
        # Mock the CreditTransaction.objects.create to avoid database operations
        with patch('apps.credits.models.CreditTransaction.objects.create') as mock_create_transaction:
            # Make the request
            url = reverse('users:run_main_script')
            response = authenticated_client.post(url, {
                'parameters': {'param1': 'value1', 'param2': 'value2'}
            }, format='json')
            
            # Check response
            assert response.status_code == status.HTTP_200_OK
            assert response.data['success'] is True
            assert response.data['credits_used'] == 5  # Default credit cost
            assert response.data['credits_remaining'] == 5  # 10 initial - 5 used
            
            # Verify the user's credits were deducted
            profile = UserProfile.objects.get(user=user_with_credits)
            assert profile.credits_balance == 5
            
            # Verify a transaction was recorded
            mock_create_transaction.assert_called_once()
            # Check the transaction arguments contained the expected values
            call_kwargs = mock_create_transaction.call_args.kwargs
            assert call_kwargs['user'] == user_with_credits
            assert call_kwargs['amount'] == -5
            assert 'Executed main.py script' in call_kwargs['description']
    
    def test_execute_main_script_insufficient_credits(self, broke_client, create_test_script):
        """Test execution fails when user has insufficient credits"""
        # Make the request
        url = reverse('users:run_main_script')
        response = broke_client.post(url, {
            'parameters': {'param1': 'value1'}
        }, format='json')
        
        # Check response
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert 'Insufficient credits' in response.data['error']
        assert response.data['required'] == 5  # Default credit cost
        assert response.data['available'] == 0  # User has 0 credits
    
    def test_admin_override_credit_amount(self, admin_client, create_test_script, admin_user):
        """Test admin can override the credit amount"""
        # Make the request with credit_amount=0 (free execution for admin)
        url = reverse('users:run_main_script')
        response = admin_client.post(url, {
            'parameters': {'param1': 'admin_value'},
            'credit_amount': 0  # Admin sets it to free
        }, format='json')
        
        # Check response
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['credits_used'] == 0  # Admin override
        
        # Verify the admin's credits were not deducted
        profile = UserProfile.objects.get(user=admin_user)
        assert profile.credits_balance == 5  # Still has original 5 credits
    
    def test_utility_function_demo(self, authenticated_client, user_with_credits):
        """Test the utility function demo endpoint"""
        # Mock the CreditTransaction.objects.create to avoid database operations
        with patch('apps.credits.models.CreditTransaction.objects.create') as mock_create_transaction:
            # Make the request
            url = reverse('users:credit-based-function-demo')
            response = authenticated_client.post(url, {
                'parameters': {'test': 'value'}
            }, format='json')
            
            # Check response
            assert response.status_code == status.HTTP_200_OK
            # Check the demo function's response contents
            assert response.data['message'] == 'Function executed successfully'
            assert response.data['processed_parameters'] == {'test': 'value'}
            # Check the credit information
            assert response.data['credits_used'] == 3  # Default credit cost for this endpoint
            assert response.data['credits_remaining'] == 7  # 10 initial - 3 used
            
            # Verify the user's credits were deducted
            profile = UserProfile.objects.get(user=user_with_credits)
            assert profile.credits_balance == 7
            
            # Verify a transaction was recorded
            mock_create_transaction.assert_called_once()
    
    def test_unauthenticated_access(self, api_client):
        """Test unauthenticated access is denied"""
        # Try to access the main script endpoint without authentication
        url = reverse('users:run_main_script')
        response = api_client.post(url, {'parameters': {'test': 'value'}}, format='json')
        
        # Check response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Try to access the utility function demo endpoint without authentication
        url = reverse('users:credit-based-function-demo')
        response = api_client.post(url, {'parameters': {'test': 'value'}}, format='json')
        
        # Check response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
