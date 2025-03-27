import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def run_tests(test_labels=None):
    """
    Run the specified tests or all tests if none are specified.
    
    Args:
        test_labels: List of test labels to run (e.g., ['test_service', 'test_database'])
                     If None, all tests in the current directory will be run.
    """
    if test_labels is None:
        # Run all tests in the current directory
        test_labels = ['apps.supabase.tests']
    elif isinstance(test_labels, list):
        # Prefix each test label with the package name
        test_labels = [f'apps.supabase.tests.{label}' for label in test_labels]
    
    # Get the test runner
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=True)
    
    # Run the tests
    failures = test_runner.run_tests(test_labels)
    
    # Return the exit code (0 for success, 1 for failure)
    return 1 if failures else 0

if __name__ == '__main__':
    # Get test labels from command line arguments
    test_labels = sys.argv[1:] if len(sys.argv) > 1 else None
    
    # Run the tests and exit with the appropriate code
    sys.exit(run_tests(test_labels))
