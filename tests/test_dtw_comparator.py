"""
Unit tests for the DTWComparator module.
"""
import unittest
import numpy as np
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dtw_comparator import DTWComparator


class TestDTWComparator(unittest.TestCase):
    """Test cases for DTWComparator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.comparator = DTWComparator()
        
        # Create test audio signals
        duration = 1.0
        sr = 44100
        t = np.linspace(0, duration, int(duration * sr))
        
        # Similar signals
        self.audio1 = np.sin(2 * np.pi * 440 * t)
        self.audio2 = np.sin(2 * np.pi * 450 * t)  # Slightly different freq
        
        # Very different signal
        self.audio3 = np.sin(2 * np.pi * 880 * t)  # Double frequency
        
        # Same signal at different speeds
        t_slow = np.linspace(0, duration * 1.2, int(duration * sr))
        self.audio_slow = np.sin(2 * np.pi * 440 * t_slow)
    
    def test_extract_features_mfcc(self):
        """Test MFCC feature extraction."""
        features = self.comparator.extract_features(self.audio1, 'mfcc')
        
        # Should return 2D array (time x features)
        self.assertEqual(len(features.shape), 2)
        
        # Should have 13 MFCC features by default
        self.assertEqual(features.shape[1], 13)
    
    def test_extract_features_chroma(self):
        """Test chroma feature extraction."""
        features = self.comparator.extract_features(self.audio1, 'chroma')
        
        # Should return 2D array
        self.assertEqual(len(features.shape), 2)
        
        # Should have 12 chroma features
        self.assertEqual(features.shape[1], 12)
    
    def test_extract_features_spectral(self):
        """Test spectral feature extraction."""
        features = self.comparator.extract_features(self.audio1, 'spectral')
        
        # Should return 2D array
        self.assertEqual(len(features.shape), 2)
    
    def test_compare_dtw_identical(self):
        """Test DTW comparison of identical signals."""
        distance, path = self.comparator.compare_dtw(self.audio1, self.audio1)
        
        # Distance should be very small for identical signals
        self.assertLess(distance, 0.1)
        
        # Path should exist
        self.assertGreater(len(path), 0)
    
    def test_compare_dtw_similar(self):
        """Test DTW comparison of similar signals."""
        distance1, _ = self.comparator.compare_dtw(self.audio1, self.audio2)
        distance2, _ = self.comparator.compare_dtw(self.audio1, self.audio3)
        
        # Similar signals should have smaller distance than different signals
        self.assertLess(distance1, distance2)
    
    def test_compare_dtw_different_speeds(self):
        """Test DTW handles different speaking speeds."""
        # DTW should handle speed differences
        distance, path = self.comparator.compare_dtw(self.audio1, self.audio_slow)
        
        # Distance should still be reasonable despite speed difference
        self.assertLess(distance, 5.0)
        
        # Path should show alignment
        self.assertGreater(len(path), 0)
    
    def test_compare_multiple_features(self):
        """Test multi-feature comparison."""
        results = self.comparator.compare_multiple_features(
            self.audio1, self.audio2
        )
        
        # Should return dictionary with required keys
        required_keys = ['dtw_mfcc', 'dtw_chroma', 'dtw_spectral',
                        'similarity_score', 'duration_ratio']
        
        for key in required_keys:
            self.assertIn(key, results)
        
        # Similarity score should be 0-100
        self.assertGreaterEqual(results['similarity_score'], 0)
        self.assertLessEqual(results['similarity_score'], 100)
    
    def test_compare_waveforms(self):
        """Test waveform comparison metrics."""
        metrics = self.comparator.compare_waveforms(self.audio1, self.audio2)
        
        # Should return multiple metrics
        expected_metrics = ['cross_correlation', 'mse', 'cosine_similarity']
        
        for metric in expected_metrics:
            self.assertIn(metric, metrics)
            # All metrics should be numeric
            self.assertIsInstance(metrics[metric], (int, float))
    
    def test_get_similarity_feedback(self):
        """Test feedback generation."""
        # Test different score ranges
        feedback_90 = self.comparator.get_similarity_feedback(90)
        self.assertIn('Excellent', feedback_90)
        
        feedback_70 = self.comparator.get_similarity_feedback(70)
        self.assertIn('Good', feedback_70)
        
        feedback_30 = self.comparator.get_similarity_feedback(30)
        self.assertIn('improvement', feedback_30.lower())
    
    def test_analyze_pronunciation_errors(self):
        """Test detailed pronunciation error analysis."""
        analysis = self.comparator.analyze_pronunciation_errors(
            self.audio1, self.audio2
        )
        
        # Should return dictionary with feedback
        required_keys = ['speed_feedback', 'feedback', 'similarity_score']
        
        for key in required_keys:
            self.assertIn(key, analysis)
        
        # Feedback should be strings
        self.assertIsInstance(analysis['feedback'], str)
        self.assertIsInstance(analysis['speed_feedback'], str)
    
    def test_get_timing_alignment(self):
        """Test timing alignment path extraction."""
        path = self.comparator.get_timing_alignment(self.audio1, self.audio_slow)
        
        # Path should be 2D array
        self.assertEqual(len(path.shape), 2)
        self.assertEqual(path.shape[1], 2)
        
        # Should have multiple alignment points
        self.assertGreater(len(path), 10)


class TestDTWSimilarityScoring(unittest.TestCase):
    """Test DTW similarity scoring accuracy."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.comparator = DTWComparator()
        
        duration = 1.0
        sr = 44100
        t = np.linspace(0, duration, int(duration * sr))
        
        # Create signals with known relationships
        self.signal_original = np.sin(2 * np.pi * 440 * t)
        
        # Nearly identical (with small noise)
        self.signal_nearly_same = self.signal_original + np.random.normal(
            0, 0.01, len(self.signal_original)
        )
        
        # Different frequency
        self.signal_different = np.sin(2 * np.pi * 660 * t)
    
    def test_high_similarity_for_nearly_identical(self):
        """Nearly identical signals should have high similarity."""
        results = self.comparator.compare_multiple_features(
            self.signal_original, self.signal_nearly_same
        )
        
        # Should have high similarity score
        self.assertGreater(results['similarity_score'], 70)
    
    def test_low_similarity_for_different(self):
        """Different signals should have lower similarity."""
        results_same = self.comparator.compare_multiple_features(
            self.signal_original, self.signal_nearly_same
        )
        results_diff = self.comparator.compare_multiple_features(
            self.signal_original, self.signal_different
        )
        
        # Different signal should have lower score
        self.assertLess(
            results_diff['similarity_score'],
            results_same['similarity_score']
        )


if __name__ == '__main__':
    unittest.main()
