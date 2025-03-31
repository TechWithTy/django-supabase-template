class CelerySupabaseRouter:
    """Route Celery-related database operations to Supabase."""
    
    def db_for_read(self, model, **hints):
        """Send reads from Credits app models to Supabase."""
        if model._meta.app_label == 'credits':
            return 'supabase'
        return None

    def db_for_write(self, model, **hints):
        """Send writes from Credits app models to Supabase."""
        if model._meta.app_label == 'credits':
            return 'supabase'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """Allow any relation if both objects are in the same database."""
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Ensure migrations for the Credits app are run on both databases."""
        if db == 'supabase' and app_label == 'credits':
            return True
        if db != 'supabase' and app_label != 'credits':
            return True
        return False
