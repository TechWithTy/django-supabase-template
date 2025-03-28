import asyncio
import pytest
import logging
from contextlib import nullcontext

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

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test."""
    # Close any existing event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.stop()
        if not loop.is_closed():
            loop.close()
    except Exception:
        pass
    
    # Create new event loop
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Yield the loop for the test to use
    yield loop
    
    # Run loop briefly to allow pending tasks to properly clean up
    if not loop.is_closed():
        # Run the event loop a bit longer to ensure proper cleanup
        loop.run_until_complete(asyncio.sleep(0.1))
        
        # Cancel all remaining tasks
        pending = asyncio.all_tasks(loop=loop)
        if pending:
            for task in pending:
                task.cancel()
            # Use a context manager to handle suppressing CancelledError exceptions
            with nullcontext():
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        
        # Close the loop after tests complete
        loop.close()
