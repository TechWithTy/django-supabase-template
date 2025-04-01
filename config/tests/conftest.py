import os
import sys
import django

# Add the project root directory to Python's module search path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Also add the backend directory to the path
backend_dir = os.path.join(project_root, 'backend')
sys.path.insert(0, backend_dir)

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Initialize Django
django.setup()

# Set environment variable to indicate tests that need authentication should be skipped
os.environ['SKIP_AUTH_TESTS'] = 'True'
