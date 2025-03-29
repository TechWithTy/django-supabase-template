from django.apps import AppConfig


class CachingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.caching'
    verbose_name = 'Caching'
    
    def ready(self):
        # Import any signals or perform initialization tasks here
        pass
