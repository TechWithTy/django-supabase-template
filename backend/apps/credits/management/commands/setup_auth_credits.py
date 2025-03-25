from django.core.management.base import BaseCommand
from apps.credits.models import CreditUsageRate


class Command(BaseCommand):
    help = 'Sets up credit usage rates for authentication endpoints to be free (0 credits)'

    def handle(self, *args, **options):
        # Define the authentication endpoints that should be free
        free_endpoints = [
            {
                'endpoint_path': '/api/register/',
                'description': 'User registration endpoint - free to use'
            },
            {
                'endpoint_path': '/api/login/',
                'description': 'User login endpoint - free to use'
            },
            {
                'endpoint_path': '/api/login/oauth/',
                'description': 'OAuth login endpoint - free to use'
            },
            {
                'endpoint_path': '/api/reset-password/',
                'description': 'Password reset endpoint - free to use'
            },
            {
                'endpoint_path': '/api/current-user/',
                'description': 'Get current user endpoint - free to use'
            },
            {
                'endpoint_path': '/api/logout/',
                'description': 'User logout endpoint - free to use'
            },
        ]

        # Create or update credit usage rates for each endpoint
        created_count = 0
        updated_count = 0

        for endpoint_data in free_endpoints:
            endpoint_path = endpoint_data['endpoint_path']
            description = endpoint_data['description']

            # Try to get an existing rate for this endpoint
            rate, created = CreditUsageRate.objects.update_or_create(
                endpoint_path=endpoint_path,
                defaults={
                    'credits_per_request': 0,  # Set to 0 credits (free)
                    'description': description,
                    'is_active': True
                }
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created free rate for {endpoint_path}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f'Updated rate for {endpoint_path} to be free'))

        # Summary message
        self.stdout.write(self.style.SUCCESS(
            f'Successfully set up {created_count + updated_count} free authentication endpoints '
            f'({created_count} created, {updated_count} updated)'
        ))
