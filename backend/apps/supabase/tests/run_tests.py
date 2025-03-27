import os
import sys
import django
import pytest
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Set environment variables to avoid database connections in tests
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'

# Initialize Django
django.setup()

def run_tests(test_labels=None):
    """
    Run the specified tests or all tests if none are specified using pytest.
    
    Args:
        test_labels: List of test labels to run (e.g., ['test_service', 'test_database'])
                     If None, all tests in the current directory will be run.
    """
    # Get the current directory
    current_dir = Path(__file__).parent
    
    # Build pytest arguments
    pytest_args = ['-xvs']
    
    if test_labels:
        # Add specific test files
        for label in test_labels:
            if not label.endswith('.py'):
                label = f"{label}.py"
            pytest_args.append(str(current_dir / label))
    else:
        # Run all test files in the current directory
        pytest_args.append(str(current_dir))
    
    # Add configuration options
    pytest_args.extend(['--no-header', '--no-summary'])
    
    print(f"Running tests with arguments: {pytest_args}")
    
    # Run pytest with the arguments
    return pytest.main(pytest_args)

if __name__ == '__main__':
    # Get test labels from command line arguments
    test_labels = sys.argv[1:] if len(sys.argv) > 1 else None
    
    # Run the tests and exit with the appropriate code
    sys.exit(run_tests(test_labels))
