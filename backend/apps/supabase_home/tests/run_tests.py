import os
import sys
import django
import pytest
from pathlib import Path
from utils.sensitive import load_environment_files

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Load environment variables
load_environment_files()

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Initialize Django
django.setup()

def run_tests(test_labels=None, include_integration=False):
    """
    Run the specified tests or all tests if none are specified using pytest.
    
    Args:
        test_labels: List of test labels to run (e.g., ['test_service', 'test_database'])
                     If None, all tests in the current directory will be run.
        include_integration: If True, include integration tests that require actual Supabase connection
    """
    # Get the current directory
    current_dir = Path(__file__).parent
    
    # Build pytest arguments
    pytest_args = ['-xvs']
    
    # Exclude integration tests unless explicitly included
    if not include_integration:
        pytest_args.append('--ignore=test_integration.py')
    
    if test_labels:
        # Add specific test files
        for label in test_labels:
            if label == 'test_integration' and not include_integration:
                print("Skipping integration tests as they require Supabase credentials")
                print("Use --integration flag to include integration tests")
                continue
                
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
    # Parse command line arguments
    include_integration = '--integration' in sys.argv
    if include_integration:
        sys.argv.remove('--integration')
        print("Including integration tests that connect to Supabase")
    
    # Get test labels from remaining command line arguments
    test_labels = [arg for arg in sys.argv[1:] if not arg.startswith('--')]
    test_labels = test_labels if test_labels else None
    
    sys.exit(run_tests(test_labels, include_integration))
