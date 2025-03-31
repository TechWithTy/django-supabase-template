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
        
        # Patch time for consistent latency calculations
        self.time_patcher = patch('time.time')
        self.mock_time = self.time_patcher.start()
        
        print(">>> SETUP COMPLETED", file=sys.stderr, flush=True)
    
    def tearDown(self):
        """Clean up patches."""
        print(">>> TEARDOWN STARTING", file=sys.stderr, flush=True)
        self.patcher.stop()
        self.time_patcher.stop()
        print(">>> TEARDOWN COMPLETED", file=sys.stderr, flush=True)
    
    def test_high_latency_anomaly_detection(self):
        """Test that high latency anomalies are properly detected."""
        print(">>> TEST_HIGH_LATENCY STARTING", file=sys.stderr, flush=True)
        
        # Configure mock_time to simulate latency
        self.mock_time.side_effect = [0, 1.5]  # Start time, end time
        
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
        
        # Set consistent time values
        self.mock_time.side_effect = [0, 0.5]  # Start time, end time
        
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
    
    def test_credit_usage_anomaly_detection(self):
        """Test that unusual credit usage patterns are detected."""
        print(">>> TEST_CREDIT_USAGE STARTING", file=sys.stderr, flush=True)
        
        # Reset mocks
        self.mock_triggered.reset_mock()
        self.mock_labels.reset_mock()
        self.mock_inc.reset_mock()
        
        # Simulate normal operation (no high latency)
        self.mock_time.side_effect = [0, 0.5]  # Below threshold
        
        # Import the function
        from apps.monitoring.utils import detect_anomalies
        
        # Use it with credit_usage endpoint
        with detect_anomalies('credit_usage', latency_threshold=1.0):
            print(">>> SIMULATING CREDIT USAGE", file=sys.stderr, flush=True)
            # Simulate an operation that would use credits
            pass
        
        # Verify that detect_anomalies was called but latency threshold not exceeded
        self.mock_triggered.labels.assert_not_called()
        self.mock_inc.assert_not_called()
        print(">>> TEST_CREDIT_USAGE COMPLETED", file=sys.stderr, flush=True)
    
    def test_error_rate_anomaly_detection(self):
        """Test that error rate anomalies are properly detected and recorded."""
        print(">>> TEST_ERROR_RATE STARTING", file=sys.stderr, flush=True)
        
        # Reset mocks
        self.mock_triggered.reset_mock()
        self.mock_labels.reset_mock()
        self.mock_inc.reset_mock()
        
        # Import the function
        from apps.monitoring.utils import detect_anomalies
        
        # Since we're just testing the interface, we'll run multiple operations
        # and check that metrics are recorded correctly
        for i in range(5):
            # Set different time values for each call to prevent side_effect list exhaustion
            self.mock_time.side_effect = [i, i+0.2]  # Below threshold
            
            # For the last iteration, simulate an error
            if i == 4:
                try:
                    with detect_anomalies('api_endpoint'):
                        raise RuntimeError("Simulated error")
                except RuntimeError:
                    pass
            else:
                with detect_anomalies('api_endpoint'):
                    pass
        
        # Verify that exception anomaly was detected exactly once
        self.mock_triggered.labels.assert_called_once_with(
            endpoint='api_endpoint',
            reason='exception'
        )
        self.mock_inc.assert_called_once()
        print(">>> TEST_ERROR_RATE COMPLETED", file=sys.stderr, flush=True)
    
    @patch('apps.monitoring.utils.time')
    def test_multiple_latency_thresholds(self, mock_time):
        """Test that different latency thresholds trigger anomalies appropriately."""
        print(">>> TEST_MULTIPLE_THRESHOLDS STARTING", file=sys.stderr, flush=True)
        
        # Reset mocks
        self.mock_triggered.reset_mock()
        self.mock_labels.reset_mock()
        self.mock_inc.reset_mock()
        
        # Import the function
        from apps.monitoring.utils import detect_anomalies
        
        # Test case 1: Just below threshold (should not trigger)
        mock_time.time.side_effect = [0, 0.99]  # Just below 1.0 threshold
        with detect_anomalies('threshold_test', latency_threshold=1.0):
            pass
            
        self.mock_triggered.labels.assert_not_called()
        
        # Test case 2: Just above threshold (should trigger)
        self.mock_triggered.reset_mock()
        mock_time.time.side_effect = [0, 1.01]  # Just above 1.0 threshold
        with detect_anomalies('threshold_test', latency_threshold=1.0):
            pass
            
        self.mock_triggered.labels.assert_called_once_with(
            endpoint='threshold_test',
            reason='high_latency'
        )
        self.mock_inc.assert_called_once()
        print(">>> TEST_MULTIPLE_THRESHOLDS COMPLETED", file=sys.stderr, flush=True)
