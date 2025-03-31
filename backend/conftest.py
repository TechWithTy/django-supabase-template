import logging
import warnings
import os
import sys
import django

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Define pytest plugins at the root level as required by pytest
pytest_plugins = []

# Configure asyncio fixture scope to avoid deprecation warning
pytest_asyncio_default_fixture_loop_scope = "function"

# Suppress specifically the WebSocket task destroyed warnings
class FilterWebSocketWarnings(logging.Filter):
    def filter(self, record):
        # Don't log websocket task destruction warnings
        if 'Task was destroyed but it is pending' in record.getMessage() and 'WebSocketCommonProtocol.close_connection' in record.getMessage():
            return False
        return True

# Configure logging at the start of test session
def pytest_configure(config):
    # Add our websocket filter to the asyncio logger to suppress specific warnings
    asyncio_logger = logging.getLogger('asyncio')
    asyncio_logger.addFilter(FilterWebSocketWarnings())
    
    # Also filter out RuntimeWarnings about coroutines not being awaited
    warnings.filterwarnings("ignore", message="coroutine .* was never awaited")
