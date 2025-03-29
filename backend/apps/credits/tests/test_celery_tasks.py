import pytest
from unittest.mock import patch, MagicMock
from django.test import override_settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.cache import cache

from apps.credits.tasks import (
    cleanup_expired_credit_holds,
    periodic_credit_allocation,
    process_pending_transactions,
    sync_credit_usage_with_supabase
)


# Settings override for all tests in this module
@pytest.fixture(autouse=True)
def settings_override():
    with override_settings(
        # Disable throttling for tests
        REST_FRAMEWORK={
            'DEFAULT_THROTTLE_CLASSES': [],
            'DEFAULT_THROTTLE_RATES': {
                'user': None,
                'user_ip': None,
                'anon': None,
            }
        },
        # Enable eager execution for Celery tasks during tests
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    ):
        yield


@pytest.fixture
def setup_mocks(db):
    """Set up common test mocks."""
    # Clear cache to avoid interference from previous tests
    cache.clear()
    
    # Create test user and profile
    User = get_user_model()
    test_user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )
    
    # Start mocks
    with patch('apps.users.models.UserProfile') as mock_user_profile, \
         patch('apps.credits.models.CreditHold') as mock_credit_hold, \
         patch('apps.credits.models.CreditTransaction') as mock_credit_transaction:
        
        yield {
            'user': test_user,
            'user_profile': mock_user_profile,
            'credit_hold': mock_credit_hold,
            'credit_transaction': mock_credit_transaction,
            'now': timezone.now()
        }
    
    # Clean up after test
    cache.clear()


@pytest.mark.django_db
def test_cleanup_expired_credit_holds(setup_mocks):
    """Test the cleanup_expired_credit_holds task."""
    # Set up mock objects and return values
    mock_expired_holds = MagicMock()
    mock_expired_holds.count.return_value = 3
    
    # Configure the mock filters
    setup_mocks['credit_hold'].objects.filter.return_value = mock_expired_holds
    
    # Execute the task
    result = cleanup_expired_credit_holds.apply()
    
    # Verify task execution
    setup_mocks['credit_hold'].objects.filter.assert_called_once()
    assert mock_expired_holds.count.call_count == 1
    
    # Verify the holds were released
    assert result.successful() is True
    assert "released 3 expired holds" in result.result


@pytest.mark.django_db
def test_periodic_credit_allocation(setup_mocks):
    """Test the periodic_credit_allocation task."""
    # Configure user profile mock
    standard_user = MagicMock()
    standard_user.subscription_level = 'standard'
    
    premium_user = MagicMock()
    premium_user.subscription_level = 'premium'
    
    # Set up the mock query result
    mock_users = [standard_user, premium_user]
    setup_mocks['user_profile'].objects.filter.return_value = mock_users
    
    # Execute the task
    result = periodic_credit_allocation.apply()
    
    # Verify task execution
    setup_mocks['user_profile'].objects.filter.assert_called_once_with(is_active=True)
    
    # Verify transactions were created for each user
    assert setup_mocks['credit_transaction'].objects.create.call_count == 2
    
    # Verify credit balances were updated
    assert standard_user.save.call_count == 1
    assert premium_user.save.call_count == 1
    
    # Verify task result
    assert result.successful() is True
    assert "2 users updated" in result.result


@pytest.mark.django_db
def test_process_pending_transactions(setup_mocks):
    """Test the process_pending_transactions task."""
    # Configure transaction mock
    api_txn = MagicMock()
    api_txn.transaction_type = 'API_USAGE'
    
    other_txn = MagicMock()
    other_txn.transaction_type = 'PURCHASE'
    other_txn.user = MagicMock()
    
    # Set up the mock query result
    mock_txns = [api_txn, other_txn]
    mock_txns_queryset = MagicMock()
    mock_txns_queryset.count.return_value = 2
    setup_mocks['credit_transaction'].objects.filter.return_value = mock_txns_queryset
    mock_txns_queryset.__iter__.return_value = iter(mock_txns)
    
    # Execute the task
    result = process_pending_transactions.apply()
    
    # Verify task execution
    setup_mocks['credit_transaction'].objects.filter.assert_called_once()
    
    # Verify transactions were processed
    assert api_txn.save.call_count == 1
    assert other_txn.save.call_count == 1
    
    # Verify user balance was updated for non-API transaction
    assert other_txn.user.save.call_count == 1
    
    # Verify task result
    assert result.successful() is True
    assert "Processed 2 pending" in result.result


@pytest.mark.django_db
@patch('apps.supabase_home.init.get_supabase_client')
def test_sync_credit_usage_with_supabase(mock_get_client, setup_mocks):
    """Test the sync_credit_usage_with_supabase task."""
    # Configure supabase client mock
    mock_supabase = MagicMock()
    mock_table = MagicMock()
    mock_get_client.return_value = mock_supabase
    mock_supabase.table.return_value = mock_table
    mock_table.insert.return_value = mock_table
    
    # Configure transaction mock
    txn1 = MagicMock()
    txn1.user.user_id = 'user-123'
    txn1.id = 'txn-456'
    txn1.amount = -10
    txn1.created_at = setup_mocks['now']
    
    txn2 = MagicMock()
    txn2.user.user_id = 'user-789'
    txn2.id = 'txn-101'
    txn2.amount = -5
    txn2.created_at = setup_mocks['now']
    
    # Set up the mock query result
    mock_txns = [txn1, txn2]
    mock_txns_queryset = MagicMock()
    mock_txns_queryset.count.return_value = 2
    setup_mocks['credit_transaction'].objects.filter.return_value = mock_txns_queryset
    mock_txns_queryset.__iter__.return_value = iter(mock_txns)
    
    # Execute the task
    result = sync_credit_usage_with_supabase.apply()
    
    # Verify supabase client was called
    mock_get_client.assert_called_once()
    
    # Verify transactions were processed
    assert mock_supabase.table.call_count == 2
    assert mock_table.insert.call_count == 2
    assert mock_table.execute.call_count == 2
    
    # Verify transactions were marked as synced
    assert txn1.save.call_count == 1
    assert txn2.save.call_count == 1
    
    # Verify task result
    assert result.successful() is True
    assert "Synced 2 transactions" in result.result


@pytest.mark.django_db
def test_sync_credit_usage_with_supabase_no_transactions(setup_mocks):
    """Test sync task when there are no unsynced transactions."""
    # Configure empty query result
    mock_txns_queryset = MagicMock()
    mock_txns_queryset.count.return_value = 0
    setup_mocks['credit_transaction'].objects.filter.return_value = mock_txns_queryset
    
    # Execute the task
    with patch('apps.supabase_home.init.get_supabase_client') as mock_get_client:
        mock_supabase = MagicMock()
        mock_get_client.return_value = mock_supabase
        
        result = sync_credit_usage_with_supabase.apply()
        
        # Verify supabase client was not called
        mock_get_client.assert_not_called()
    
    # Verify task result
    assert result.successful() is True
    assert "Synced 0 transactions" in result.result
