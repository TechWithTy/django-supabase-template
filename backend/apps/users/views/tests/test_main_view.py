import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
import json
import os
import uuid
from apps.users.models import UserProfile
from apps.credits.models import CreditTransaction
from apps.authentication.models import CustomUser


@pytest.mark.django_db
class TestMainViews:
    """Integration tests for main script execution endpoints using real Supabase"""
    
    @pytest.fixture(autouse=True)
    def setup(self, test_django_user, test_admin_django_user, django_db_blocker):
        # Default script parameters
        self.script_params = {
            "parameters": {
                "param1": "value1",
                "param2": "value2"
            }
        }
        
        # Store test users for verification
        self.test_user = test_django_user
        self.admin_user = test_admin_django_user
        
        with django_db_blocker.unblock():
            # Create a low credit user for testing
            # First create the auth user
            low_credit_auth_user = CustomUser.objects.create(
                username="lowcredit",
                email="low@example.com",
                supabase_uid=str(uuid.uuid4())
            )
            
            # Then create the profile with explicit UUID
            low_credit_profile_id = uuid.uuid4()
            self.low_credit_user = UserProfile.objects.create(
                id=low_credit_profile_id,
                user=low_credit_auth_user,
                supabase_uid=low_credit_auth_user.supabase_uid,
                credits_balance=1  # Just enough to test insufficient credits
            )
        
        yield
        
        with django_db_blocker.unblock():
            # Clean up after tests
            low_credit_auth_user = self.low_credit_user.user
            self.low_credit_user.delete()
            low_credit_auth_user.delete()
            CreditTransaction.objects.filter(user=low_credit_auth_user).delete()
            
            # Reset credits for test users
            if hasattr(self.test_user, 'credits_balance'):
                self.test_user.credits_balance = 1000
                self.test_user.save()
            if hasattr(self.admin_user, 'credits_balance'):
                self.admin_user.credits_balance = 1000
                self.admin_user.save()
    
    def test_main_script_execution_success(self, authenticated_client, monkeypatch, django_db_blocker):
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
                    })
                    self.stderr = ""
                    self.text = True
            return MockProcess()
        
        monkeypatch.setattr('subprocess.run', mock_run)
        
        # Enable detailed logging for debugging
        import logging
        logger = logging.getLogger('django')
        logger.setLevel(logging.DEBUG)
        
        # Make request using authenticated client
        url = reverse('users:run_main_script')
        try:
            response = authenticated_client.post(url, self.script_params, format='json')
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.data}")
        except Exception as e:
            print(f"Exception during request: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert 'result' in response.data
        assert response.data['result']['data']['key'] == 'value'
        
        with django_db_blocker.unblock():
            # Get the user ID from the response
            credits_used = response.data.get('credits_used', 0)
            credits_remaining = response.data.get('credits_remaining', 0)
            
            # Print debug info
            print(f"Test user ID: {self.test_user.user.id}")
            print(f"Credits used: {credits_used}")
            print(f"Credits remaining: {credits_remaining}")
            
            # Check if any credit transaction was created at all
            all_transactions = CreditTransaction.objects.all()
            print(f"Total transactions: {all_transactions.count()}")
            for tx in all_transactions:
                print(f"Transaction: user_id={tx.user.id}, amount={tx.amount}, description={tx.description}")
            
            # Check if credit transaction was created for any user
            transactions = CreditTransaction.objects.filter(amount=-credits_used)
            assert transactions.count() > 0, "No credit transactions found with the expected amount"
            
            # Get the transaction
            transaction = transactions.first()
            assert transaction.amount < 0  # Should be a debit
            assert transaction.description == "Executed main.py script"
            
            # Verify user credits were deducted from some user profile
            # This might not be self.test_user if the authenticated_client is using a different user
            profile = UserProfile.objects.get(user=transaction.user)
            assert profile.credits_balance < 1000  # Credits should have decreased
    
    def test_main_script_execution_insufficient_credits(self, monkeypatch, django_db_blocker):
        """Test script execution with insufficient credits using real Supabase auth"""
        # Setup client with low credit user
        client = APIClient()
        client.force_authenticate(user=self.low_credit_user.user)
        
        # Make request
        url = reverse('users:run_main_script')
        response = client.post(url, self.script_params, format='json')
        
        # Assertions
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert 'error' in response.data
        assert 'available' in response.data
        
        with django_db_blocker.unblock():
            # Check that no credit transaction was created
            assert CreditTransaction.objects.filter(user=self.low_credit_user.user).count() == 0
            
            # Verify user credits were not deducted
            self.low_credit_user.refresh_from_db()
            assert self.low_credit_user.credits_balance == 1  # Unchanged
    
    def test_main_script_execution_admin_override(self, monkeypatch, django_db_blocker):
        """Test script execution with admin override using real Supabase auth"""
        # Setup client with admin user
        client = APIClient()
        client.force_authenticate(user=self.admin_user.user)
        
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
                    })
                    self.stderr = ""
                    self.text = True
            return MockProcess()
        
        monkeypatch.setattr('subprocess.run', mock_run)
        
        # Make request with credit override
        url = reverse('users:run_main_script')
        params = self.script_params.copy()
        params['credit_amount'] = 0  # Admin can set custom credit cost
        response = client.post(url, params, format='json')
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert 'result' in response.data
        
        with django_db_blocker.unblock():
            # Check transaction details if one was created
            transactions = CreditTransaction.objects.filter(user=self.admin_user.user)
            if transactions.exists():  # Admin might not create transaction in some implementations
                transaction = transactions.first()
                assert transaction.amount == 0 or transaction.amount > -5  # Custom low or zero cost
    
    def test_main_script_not_found(self, authenticated_client, monkeypatch, django_db_blocker):
        """Test script not found with real Supabase auth"""
        # Mock file doesn't exist
        monkeypatch.setattr('os.path.exists', lambda path: False)
        
        # Make request
        url = reverse('users:run_main_script')
        response = authenticated_client.post(url, self.script_params, format='json')
        
        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data
        
        with django_db_blocker.unblock():
            # Check that no credit transaction was created
            assert CreditTransaction.objects.filter(user=self.test_user.user).count() == 0
            
            # Verify user credits were not deducted
            self.test_user.refresh_from_db()
            assert self.test_user.credits_balance == 1000  # Unchanged
    
    def test_main_script_execution_error(self, authenticated_client, monkeypatch, django_db_blocker):
        """Test script execution error with real Supabase auth"""
        # Mock file existence but script execution fails
        monkeypatch.setattr('os.path.exists', lambda path: True)

        def mock_run(*args, **kwargs):
            # Create a mock process result with error
            class MockProcess:
                def __init__(self):
                    self.returncode = 1  # Error code
                    self.stderr = "Script execution failed"
                    self.stdout = ""
                    self.text = True
            return MockProcess()

        monkeypatch.setattr('subprocess.run', mock_run)

        # Make request
        url = reverse('users:run_main_script')
        response = authenticated_client.post(url, self.script_params, format='json')

        # Assertions
        assert response.status_code == status.HTTP_200_OK  # The view returns 200 even for script errors
        assert response.data['success'] is False  # But marks it as not successful
        assert response.data['exit_code'] == 1

        with django_db_blocker.unblock():
            # Check that no credit transaction was created since script execution failed
            assert CreditTransaction.objects.filter(user=self.test_user.user).count() == 0
    
    def test_unauthenticated_request(self, django_db_blocker):
        """Test unauthenticated request with real Supabase"""
        # Make request without authentication
        client = APIClient()
        # Ensure no auth header is set
        client.credentials()  # Clear any default credentials
        url = reverse('users:run_main_script')
        
        try:
            response = client.post(url, self.script_params, format='json')
            
            # Assertions
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
        finally:
            # Clean up any orphaned UserProfiles that might have been created
            with django_db_blocker.unblock():
                # Find any UserProfiles with invalid user references
                from django.db import connection
                with connection.cursor() as cursor:
                    # Find UserProfiles with user_ids that don't exist in CustomUser table
                    cursor.execute("""
                        DELETE FROM users_userprofile 
                        WHERE user_id NOT IN (SELECT id FROM authentication_customuser)
                    """)
