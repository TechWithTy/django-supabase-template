from celery import shared_task
import logging
from datetime import datetime, timedelta
from django.db.models import F
from django.conf import settings
from django.db import transaction

logger = logging.getLogger('credits')

@shared_task
def cleanup_expired_credit_holds():
    """Task to clean up expired credit holds.
    
    Finds and releases all expired credit holds, returning credits to users.
    This helps maintain the integrity of the credit system by ensuring
    that temporarily held credits don't remain locked indefinitely.
    """
    now = datetime.now()
    logger.info(f"[{now}] Running cleanup for expired credit holds")
    
    try:
        from apps.credits.models import CreditHold
        
        with transaction.atomic():
            expired_holds = CreditHold.objects.filter(expires_at__lt=now, is_active=True)
            count = expired_holds.count()
            
            for hold in expired_holds:
                hold.release()
                
            logger.info(f"Released {count} expired credit holds")
        
        return f"Cleanup completed: released {count} expired holds"
    except Exception as e:
        logger.error(f"Error in cleanup_expired_credit_holds: {str(e)}")
        raise

@shared_task
def periodic_credit_allocation():
    """Task to allocate periodic credits to users.
    
    This task runs on a schedule (typically monthly) to allocate free credits
    to users based on their subscription level or activity status.
    """
    now = datetime.now()
    logger.info(f"[{now}] Running periodic credit allocation")
    
    try:
        from apps.credits.models import CreditTransaction
        from apps.users.models import UserProfile
        
        with transaction.atomic():
            # Get active users with their subscription levels
            active_users = UserProfile.objects.filter(is_active=True)
            
            # Set credits based on subscription level
            standard_credits = 100  # Free tier monthly credits
            premium_credits = 500   # Premium tier monthly credits
            
            standard_count = 0
            premium_count = 0
            
            for user in active_users:
                # Determine credit amount based on subscription
                if user.subscription_level == 'premium':
                    credit_amount = premium_credits
                    premium_count += 1
                else:
                    credit_amount = standard_credits
                    standard_count += 1
                
                # Create transaction
                CreditTransaction.objects.create(
                    user=user,
                    amount=credit_amount,
                    description="Monthly credit allocation",
                    transaction_type="MONTHLY_ALLOCATION"
                )
                
                # Update user's credit balance
                user.credit_balance = F('credit_balance') + credit_amount
                user.save(update_fields=['credit_balance'])
            
            logger.info(f"Allocated credits to {standard_count} standard users and {premium_count} premium users")
            
        return f"Credit allocation completed: {standard_count + premium_count} users updated"
    except Exception as e:
        logger.error(f"Error in periodic_credit_allocation: {str(e)}")
        raise

@shared_task
def process_pending_transactions():
    """Task to process pending credit transactions.
    
    Handles any transactions that are in a pending state and need to be
    finalized, such as temporary holds that need to be committed or released.
    """
    now = datetime.now()
    logger.info(f"[{now}] Processing pending credit transactions")
    
    try:
        from apps.credits.models import CreditTransaction
        
        with transaction.atomic():
            # Find transactions that have been pending for too long (e.g., > 24 hours)
            time_threshold = now - timedelta(hours=24)
            stale_pending_txns = CreditTransaction.objects.filter(
                status='PENDING',
                created_at__lt=time_threshold
            )
            
            count = stale_pending_txns.count()
            
            for txn in stale_pending_txns:
                # Based on transaction type, decide whether to commit or revert
                if txn.transaction_type in ['API_USAGE', 'FEATURE_ACCESS']:
                    # For usage-related transactions, commit them
                    txn.status = 'COMPLETED'
                    txn.save(update_fields=['status'])
                else:
                    # For other types, revert the transaction
                    user = txn.user
                    user.credit_balance = F('credit_balance') + abs(txn.amount)  # Refund credits
                    user.save(update_fields=['credit_balance'])
                    
                    txn.status = 'FAILED'
                    txn.notes = "Automatically cancelled after 24 hours in pending state"
                    txn.save(update_fields=['status', 'notes'])
            
            logger.info(f"Processed {count} stale pending transactions")
            
        return f"Processed {count} pending transactions"
    except Exception as e:
        logger.error(f"Error in process_pending_transactions: {str(e)}")
        raise

@shared_task
def sync_credit_usage_with_supabase():
    """Task to synchronize credit usage data with Supabase.
    
    This task ensures that credit usage data in Django is properly
    synchronized with Supabase for real-time analytics and reporting.
    """
    now = datetime.now()
    logger.info(f"[{now}] Syncing credit usage data with Supabase")
    
    try:
        from apps.credits.models import CreditTransaction
        from apps.supabase_home.init import get_supabase_client
        
        # Get transactions that haven't been synced yet
        unsynced_txns = CreditTransaction.objects.filter(synced_to_supabase=False)
        count = unsynced_txns.count()
        
        if count > 0:
            supabase = get_supabase_client()
            
            for txn in unsynced_txns:
                # Prepare data for Supabase
                txn_data = {
                    "user_id": str(txn.user.user_id),
                    "transaction_id": str(txn.id),
                    "amount": txn.amount,
                    "description": txn.description,
                    "transaction_type": txn.transaction_type,
                    "status": txn.status,
                    "created_at": txn.created_at.isoformat(),
                }
                
                # Insert into Supabase
                supabase.table('credit_transactions').insert(txn_data).execute()
                
                # Mark as synced
                txn.synced_to_supabase = True
                txn.save(update_fields=['synced_to_supabase'])
            
            logger.info(f"Synced {count} credit transactions to Supabase")
        else:
            logger.info("No transactions to sync")
            
        return f"Synced {count} transactions to Supabase"
    except Exception as e:
        logger.error(f"Error in sync_credit_usage_with_supabase: {str(e)}")
        raise
