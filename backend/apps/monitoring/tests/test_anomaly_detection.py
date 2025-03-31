from unittest import TestCase
from unittest.mock import patch, Mock
import sys

# Create isolated test that doesn't inherit from Django TestCase
class AnomalyDetectionUnitTests(TestCase):
    """Unit tests for anomaly detection functionality without database dependencies."""

    def setUp(self):
        """Set up test doubles."""
        print(">>> SETUP STARTING", file=sys.stderr, flush=True)
        # Create all mocks at once to avoid real dependencies
        self.patcher = patch('apps.monitoring.utils.ANOMALY_DETECTION_TRIGGERED')
        self.mock_triggered = self.patcher.start()
        
        # Mock the labels method and its return value with inc method
        self.mock_labels = Mock()
        self.mock_inc = Mock()
        self.mock_labels.inc = self.mock_inc
        self.mock_triggered.labels.return_value = self.mock_labels
        
        print(">>> SETUP COMPLETED", file=sys.stderr, flush=True)
    
    def tearDown(self):
        """Clean up patches."""
        print(">>> TEARDOWN STARTING", file=sys.stderr, flush=True)
        self.patcher.stop()
        print(">>> TEARDOWN COMPLETED", file=sys.stderr, flush=True)
    
    def test_high_latency_anomaly_detection(self):
        """Test that high latency anomalies are properly detected."""
        print(">>> TEST_HIGH_LATENCY STARTING", file=sys.stderr, flush=True)
        
        # Mock time to simulate latency
        with patch('time.time') as mock_time:
            # First call returns 0, second call returns 1.5 (exceeding threshold)
            mock_time.side_effect = [0, 1.5]
            
            # Import module only after patching dependencies
            from apps.monitoring.utils import detect_anomalies
            
            # Use the real function with mocked dependencies
            with detect_anomalies('test_endpoint', latency_threshold=1.0):
                print(">>> INSIDE CONTEXT MANAGER", file=sys.stderr, flush=True)
                # Context manager automatically checks latency when exiting
                pass
        
        # Verify high latency was detected - check that labels was called with correct arguments
        self.mock_triggered.labels.assert_called_once_with(
            endpoint='test_endpoint',
            reason='high_latency'
        )
        # Verify inc() was called on the result of labels()
        self.mock_inc.assert_called_once()
        print(">>> TEST_HIGH_LATENCY COMPLETED", file=sys.stderr, flush=True)
    
    def test_anomaly_detection_with_exceptions(self):
        """Test that exceptions during API operations trigger anomaly detection."""
        print(">>> TEST_WITH_EXCEPTIONS STARTING", file=sys.stderr, flush=True)
        
        # Reset mocks for this test to ensure clean state
        self.mock_triggered.reset_mock()
        self.mock_labels.reset_mock()
        self.mock_inc.reset_mock()
        
        # Import module after patching
        from apps.monitoring.utils import detect_anomalies
        
        # Use function with mock dependencies
        try:
            with detect_anomalies('exception_test'):
                print(">>> RAISING EXCEPTION", file=sys.stderr, flush=True)
                raise ValueError("Test exception")
        except ValueError:
            print(">>> CAUGHT EXCEPTION", file=sys.stderr, flush=True)
            pass
            
        # Verify exception anomaly was detected
        self.mock_triggered.labels.assert_called_once_with(
            endpoint='exception_test',
            reason='exception'
        )
        self.mock_inc.assert_called_once()
        print(">>> TEST_WITH_EXCEPTIONS COMPLETED", file=sys.stderr, flush=True)
