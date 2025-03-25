import unittest
from django.test import TransactionTestCase
from django.contrib.auth.models import User
from apps.users.models import UserProfile
from apps.credits.models import CreditTransaction, CreditHold
from concurrent.futures import ThreadPoolExecutor
import threading
import time
import random
from django.db import transaction


class CreditSystemConcurrencyTest(TransactionTestCase):
    """Test suite for validating credit system concurrency safety."""
    
    reset_sequences = True
    
    def setUp(self):
        # Create test users with initial credit balances
        self.user1 = User.objects.create_user(username='testuser1', password='password123')
        self.user_profile1 = UserProfile.objects.get(user=self.user1)
        self.user_profile1.credits_balance = 1000
        self.user_profile1.save()
        
        self.user2 = User.objects.create_user(username='testuser2', password='password123')
        self.user_profile2 = UserProfile.objects.get(user=self.user2)
        self.user_profile2.credits_balance = 1000
        self.user_profile2.save()
    
    def test_concurrent_deductions(self):
        """
        Test concurrent deductions from the same user account to verify
        that the total credits deducted matches expectations and no race
        conditions occur.
        """
        num_threads = 10
        credits_per_deduction = 10
        expected_final_balance = 1000 - (num_threads * credits_per_deduction)
        
        # Track successful deductions
        success_count = [0]  # Using list for mutable reference
        lock = threading.Lock()
        
        def deduct_credits():
            # Add some random delay to increase chance of concurrency issues
            time.sleep(random.uniform(0.01, 0.05))
            
            # Reload user profile in this thread
            profile = UserProfile.objects.get(user=self.user1)
            result = profile.deduct_credits(credits_per_deduction)
            
            with lock:
                if result:
                    success_count[0] += 1
            
            return result
        
        # Run concurrent deductions
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            results = list(executor.map(lambda _: deduct_credits(), range(num_threads)))
        
        # Refresh user profile from database
        self.user_profile1.refresh_from_db()
        
        # Verify results
        self.assertEqual(success_count[0], num_threads, 
                        f"Expected {num_threads} successful deductions, got {success_count[0]}")
        self.assertEqual(self.user_profile1.credits_balance, expected_final_balance,
                        f"Expected final balance of {expected_final_balance}, got {self.user_profile1.credits_balance}")
        
        # Check transaction records
        transactions = CreditTransaction.objects.filter(
            user=self.user1, 
            transaction_type='deduction'
        )
        self.assertEqual(transactions.count(), num_threads, 
                        f"Expected {num_threads} transaction records, got {transactions.count()}")
    
    def test_concurrent_holds(self):
        """
        Test placing concurrent credit holds to ensure proper locking and accounting.
        """
        num_threads = 5
        credits_per_hold = 50
        expected_final_balance = 1000 - (num_threads * credits_per_hold)
        
        # Track successful holds
        successful_holds = []
        lock = threading.Lock()
        
        def place_hold():
            # Add random delay
            time.sleep(random.uniform(0.01, 0.05))
            
            hold = CreditHold.place_hold(
                user=self.user2,
                amount=credits_per_hold,
                description=f"Test hold {threading.get_ident()}",
                endpoint="/api/test/"
            )
            
            with lock:
                if hold:
                    successful_holds.append(hold)
            
            return hold is not None
        
        # Run concurrent holds
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            results = list(executor.map(lambda _: place_hold(), range(num_threads)))
        
        # Refresh user profile
        self.user_profile2.refresh_from_db()
        
        # Verify results
        self.assertEqual(len(successful_holds), num_threads,
                        f"Expected {num_threads} successful holds, got {len(successful_holds)}")
        self.assertEqual(self.user_profile2.credits_balance, expected_final_balance, 
                        f"Expected final balance of {expected_final_balance}, got {self.user_profile2.credits_balance}")
        
        # Check hold records and transactions
        holds = CreditHold.objects.filter(user=self.user2, is_active=True)
        self.assertEqual(holds.count(), num_threads,
                        f"Expected {num_threads} hold records, got {holds.count()}")
        
        transactions = CreditTransaction.objects.filter(
            user=self.user2, 
            transaction_type='hold'
        )
        self.assertEqual(transactions.count(), num_threads,
                        f"Expected {num_threads} hold transactions, got {transactions.count()}")
    
    def test_hold_commit_and_release(self):
        """
        Test concurrent hold commits and releases to ensure proper accounting.
        """
        # Create initial holds
        holds = []
        hold_amount = 40
        num_holds = 10
        
        for i in range(num_holds):
            hold = CreditHold.place_hold(
                user=self.user1,
                amount=hold_amount,
                description=f"Test hold {i}",
                endpoint="/api/test/"
            )
            holds.append(hold)
        
        # Refresh user profile
        self.user_profile1.refresh_from_db()
        initial_balance = self.user_profile1.credits_balance
        
        # Commit half the holds, release the other half
        commit_holds = holds[:num_holds//2]
        release_holds = holds[num_holds//2:]
        
        for hold in commit_holds:
            result = hold.commit()
            self.assertTrue(result, "Hold commit should succeed")
        
        for hold in release_holds:
            result = hold.release()
            self.assertTrue(result, "Hold release should succeed")
        
        # Refresh user profile
        self.user_profile1.refresh_from_db()
        
        # Expected: initial balance + (release_amount * num_released)
        expected_balance = initial_balance + (hold_amount * len(release_holds))
        self.assertEqual(self.user_profile1.credits_balance, expected_balance,
                         f"Expected balance of {expected_balance}, got {self.user_profile1.credits_balance}")
        
        # Check that all holds are now inactive
        active_holds = CreditHold.objects.filter(user=self.user1, is_active=True)
        self.assertEqual(active_holds.count(), 0, "All holds should be inactive")
        
        # Verify transactions
        commit_txns = CreditTransaction.objects.filter(
            user=self.user1,
            transaction_type='deduction',
            reference_id__in=[hold.id for hold in commit_holds]
        )
        self.assertEqual(commit_txns.count(), len(commit_holds),
                        "Should have a deduction transaction for each committed hold")
        
        release_txns = CreditTransaction.objects.filter(
            user=self.user1,
            transaction_type='release',
            reference_id__in=[hold.id for hold in release_holds]
        )
        self.assertEqual(release_txns.count(), len(release_holds),
                        "Should have a release transaction for each released hold")


# CLI runner for manual testing
if __name__ == "__main__":
    unittest.main()
