# Testing Guide for Django Supabase Template

## Overview

This document provides comprehensive instructions for running tests in the Django Supabase Template project. The test suite includes unit tests, integration tests, and end-to-end tests for various components, with special focus on Supabase integration.

## Test Structure

The test suite is organized as follows:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test interactions between components
- **Supabase Integration Tests**: Test actual connections to Supabase services

## Prerequisites

### Environment Setup

Before running tests, ensure you have the following environment variables configured in your `.env` file:

```
# Required for all tests
DJANGO_SETTINGS_MODULE=core.settings

# Required for Supabase integration tests
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Optional test configuration
SKIP_EMAIL_TESTS=True  # Skip tests that send emails
SKIP_USER_CREATION=True  # Skip tests that create users
TEST_TABLE_NAME=your_test_table  # Use a pre-created table for database tests
```

### Dependencies

Ensure all test dependencies are installed:

```bash
pip install -r requirements-dev.txt
```

## Running Tests

### Using pytest Directly

The recommended way to run tests is using pytest directly. From the project root directory:

```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run tests in a specific directory
pytest backend/apps/supabase_home/tests/

# Run a specific test file
pytest backend/apps/supabase_home/tests/test_auth.py

# Run a specific test class
pytest backend/apps/supabase_home/tests/test_auth.py::TestRealSupabaseAuthService

# Run a specific test function
pytest backend/apps/supabase_home/tests/test_auth.py::TestRealSupabaseAuthService::test_sign_in
```

### Running Supabase Integration Tests

Integration tests that connect to Supabase require additional configuration:

```bash
# Run integration tests
pytest backend/apps/supabase_home/tests/test_integration.py -v

# Run integration tests with specific markers
pytest -m "integration" -v

# Skip specific tests that might hit rate limits
pytest backend/apps/supabase_home/tests/test_integration.py -v --env SKIP_EMAIL_TESTS=True --env SKIP_USER_CREATION=True
```

## Test Configuration Options

### Command Line Options

Pytest provides several useful command line options:

```bash
# Run tests in parallel
pytest -xvs -n auto

# Generate HTML report
pytest --html=report.html

# Run tests that match a keyword expression
pytest -k "auth and not email"

# Stop after first failure
pytest -xvs --exitfirst

# Show local variables in tracebacks
pytest --showlocals
```

### Environment Variables

The following environment variables can be used to configure test behavior:

| Variable | Purpose |
|----------|----------|
| `SKIP_EMAIL_TESTS` | Skip tests that send emails to avoid rate limits |
| `SKIP_USER_CREATION` | Skip tests that create users to avoid rate limits |
| `TEST_TABLE_NAME` | Use a pre-created table for database tests |
| `DEBUG` | Enable debug logging during tests |

## Test Reports and Logging

### HTML Reports

Generate visually appealing HTML reports with test results:

```bash
# Install pytest-html plugin if not already installed
pip install pytest-html

# Generate a basic HTML report
pytest --html=reports/report.html --self-contained-html

# Generate report with additional details
pytest --html=reports/report.html --self-contained-html --capture=tee-sys
```

The HTML report includes:
- Test results summary
- Detailed test outcomes (pass/fail/skip)
- Test duration
- Error messages and tracebacks
- System information

### XML Reports for CI Integration

Generate JUnit XML reports for CI/CD systems:

```bash
# Generate JUnit XML report
pytest --junitxml=reports/junit.xml
```

These reports can be integrated with CI systems like Jenkins, GitHub Actions, or GitLab CI for visualization and trend analysis.

### Coverage Reports

Generate test coverage reports to identify untested code:

```bash
# Install pytest-cov if not already installed
pip install pytest-cov

# Generate coverage report in terminal
pytest --cov=backend

# Generate HTML coverage report
pytest --cov=backend --cov-report=html:reports/coverage

# Generate XML coverage report for CI integration
pytest --cov=backend --cov-report=xml:reports/coverage.xml
```

The coverage report shows:
- Overall code coverage percentage
- Line-by-line coverage analysis
- Missed lines and branches
- Module and package-level statistics

### Detailed Logging

Enhance test logs for better debugging:

```bash
# Enable verbose logging
pytest -v --log-cli-level=DEBUG

# Save logs to file
pytest --log-file=reports/test_log.txt --log-file-level=DEBUG

# Format log output
pytest --log-format="%(asctime)s %(levelname)s %(message)s" --log-date-format="%Y-%m-%d %H:%M:%S"
```

Customize logging in your `conftest.py`:

```python
import logging

def pytest_configure(config):
    """Set up logging for tests"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("reports/test_debug.log"),
            logging.StreamHandler()
        ]
    )
```

### Allure Reports

Generate comprehensive interactive reports with Allure:

```bash
# Install allure-pytest
pip install allure-pytest

# Generate report data
pytest --alluredir=reports/allure-results

# Generate and open the report (requires allure command-line tool)
allure serve reports/allure-results
```

Allure reports provide:
- Interactive dashboards
- Test execution timeline
- Detailed test steps
- Attachments (screenshots, logs)
- Categorized failures
- History trends

### Scheduled Report Generation

Automate report generation with a simple script:

```python
# save as generate_reports.py
import os
import subprocess
from datetime import datetime

def generate_reports():
    """Generate comprehensive test reports"""
    # Create reports directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = f"reports/{timestamp}"
    os.makedirs(report_dir, exist_ok=True)
    
    # Run tests with various reporting options
    subprocess.run([
        "pytest", 
        "--html", f"{report_dir}/report.html", "--self-contained-html",
        "--junitxml", f"{report_dir}/junit.xml",
        "--cov=backend", "--cov-report", f"html:{report_dir}/coverage",
        "--log-file", f"{report_dir}/test_log.txt", "--log-file-level=DEBUG"
    ])
    
    print(f"Reports generated in {report_dir}")

if __name__ == "__main__":
    generate_reports()
```

Run this script to generate all reports at once:

```bash
python generate_reports.py
```

## Writing Tests

### Best Practices

1. **Clean up resources**: Always clean up resources created during tests (users, tables, buckets)
2. **Use fixtures**: Leverage pytest fixtures for setup and teardown
3. **Mock external services**: Use mocks for external services when possible
4. **Handle rate limits**: Implement conditional skips for tests that might hit rate limits
5. **Proper assertions**: Use descriptive assertion messages
6. **Add logging**: Capture test execution details for debugging

### Example Test

```python
import pytest
from ..auth import SupabaseAuthService

class TestSupabaseAuth:
    @pytest.fixture
    def auth_service(self):
        return SupabaseAuthService()
    
    def test_sign_in(self, auth_service):
        # Test implementation
        result = auth_service.sign_in("test@example.com", "password")
        assert result is not None, "Sign in should return a response"
```

## Troubleshooting

### Common Issues

1. **Connection errors**: Ensure Supabase credentials are correct and the service is available
2. **Rate limits**: Use the `SKIP_*` environment variables to avoid hitting rate limits
3. **Database errors**: Check that required tables exist in your Supabase instance
4. **Authentication failures**: Verify that your service role key has sufficient permissions

### Debugging Tips

1. Use `pytest -xvs` for verbose output
2. Add `import pdb; pdb.set_trace()` for interactive debugging
3. Check the Supabase dashboard for logs and errors
4. Verify environment variables are loaded correctly

## Continuous Integration

The test suite is configured to run automatically in CI/CD pipelines. The configuration can be found in the GitHub Actions workflow files.

## Conclusion

Following these testing guidelines will help ensure the reliability and stability of the Django Supabase Template. For additional questions or issues, please refer to the project documentation or open an issue on GitHub.
