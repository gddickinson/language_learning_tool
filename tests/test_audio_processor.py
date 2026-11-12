"""
Unit tests for the AudioProcessor module.
"""
import unittest
import numpy as np
import os
import sys
import tempfile

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from audio_processor import AudioProcessor
import config


class TestAudioProcessor(unittest.TestCase):
    """Test cases for AudioProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = AudioProcessor()
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test audio signals
        self.sample_rate = 44100
        duration = 1.0
        t = np.linspace(0, duration, int(duration * self.sample_rate))
        
        # 440 Hz sine wave (A4 note)
        self.test_audio_440 = np.sin(2 * np.pi * 440 * t)
        
        # 880 Hz sine wave (A5 note)
        self.test_audio_880 = np.sin(2 * np.pi * 880 * t)
        
        # Chirp signal (frequency sweep)
        f0, f1 = 200, 800
        self.test_chirp = np.sin(2 * np.pi * (f0 + (f1 - f0) * t / duration) * t)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary files
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_save_and_load_audio(self):
        """Test saving and loading audio files."""
        filepath = os.path.join(self.temp_dir, 'test.wav')
        
        # Save audio
        self.processor.save_audio(self.test_audio_440, filepath)
        self.assertTrue(os.path.exists(filepath))
        
        # Load audio
        loaded_audio, sr = self.processor.load_audio(filepath)
        
        self.assertEqual(sr, self.sample_rate)
        self.assertEqual(len(loaded_audio), len(self.test_audio_440))
        
        # Check if data is similar (allowing for format conversion errors)
        np.testing.assert_array_almost_equal(
            loaded_audio, self.test_audio_440, decimal=3
        )
    
    def test_get_waveform(self):
        """Test waveform extraction."""
        time, amplitude = self.processor.get_waveform(self.test_audio_440)
        
        self.assertEqual(len(time), len(self.test_audio_440))
        self.assertEqual(len(amplitude), len(self.test_audio_440))
        
        # Check time array is correct
        expected_duration = len(self.test_audio_440) / self.sample_rate
        self.assertAlmostEqual(time[-1], expected_duration, places=3)
    
    def test_get_spectrogram(self):
        """Test spectrogram computation."""
        freqs, times, spec = self.processor.get_spectrogram(self.test_audio_440)
        
        # Check dimensions
        self.assertGreater(len(freqs), 0)
        self.assertGreater(len(times), 0)
        self.assertEqual(spec.shape[0], len(freqs))
        self.assertEqual(spec.shape[1], len(times))
        
        # For 440 Hz signal, strongest component should be near 440 Hz
        # Find frequency with maximum power
        max_freq_idx = np.argmax(np.mean(spec, axis=1))
        detected_freq = freqs[max_freq_idx]
        
        # Should be within 50 Hz of 440 (accounting for FFT resolution)
        self.assertLess(abs(detected_freq - 440), 50)
    
    def test_get_mfcc(self):
        """Test MFCC extraction."""
        mfcc = self.processor.get_mfcc(self.test_audio_440, n_mfcc=13)
        
        # Should return 13 MFCCs
        self.assertEqual(mfcc.shape[0], 13)
        
        # Should have time dimension
        self.assertGreater(mfcc.shape[1], 0)
    
    def test_normalize_audio(self):
        """Test audio normalization."""
        # Create audio with known amplitude
        audio = np.array([0.1, -0.5, 0.3, -0.2])
        normalized = self.processor.normalize_audio(audio)
        
        # Max absolute value should be 1.0
        self.assertAlmostEqual(np.max(np.abs(normalized)), 1.0)
        
        # Proportions should be maintained
        self.assertAlmostEqual(normalized[0] / normalized[1],
                              audio[0] / audio[1])
    
    def test_trim_silence(self):
        """Test silence trimming."""
        # Create audio with silence at beginning and end
        # librosa trims whole 512-sample hops of 2048-sample frames, so the silences and the signal must be
        # several frames long (with 1000 samples of each, nothing could be trimmed)
        silence = np.zeros(11025)
        signal = self.test_audio_440[:22050]
        audio_with_silence = np.concatenate([silence, signal, silence])
        
        trimmed = self.processor.trim_silence(audio_with_silence)
        
        # Trimmed audio should be shorter
        self.assertLess(len(trimmed), len(audio_with_silence))
        
        # Should be approximately same length as original signal (within one frame)
        self.assertAlmostEqual(len(trimmed), len(signal), delta=2048)
    
    def test_get_audio_features(self):
        """Test comprehensive feature extraction."""
        features = self.processor.get_audio_features(self.test_audio_440)
        
        # Check required features exist
        required_features = ['duration', 'sample_rate', 'rms_energy',
                            'max_amplitude', 'spectral_centroid_mean']
        
        for feature in required_features:
            self.assertIn(feature, features)
        
        # Check duration is approximately correct
        expected_duration = len(self.test_audio_440) / self.sample_rate
        self.assertAlmostEqual(features['duration'], expected_duration, places=2)
        
        # Check sample rate
        self.assertEqual(features['sample_rate'], self.sample_rate)
    
    def test_get_pitch(self):
        """Test pitch detection."""
        times, pitches = self.processor.get_pitch(self.test_audio_440)
        
        # Should return arrays
        self.assertGreater(len(times), 0)
        self.assertGreater(len(pitches), 0)
        
        # For clean 440 Hz signal, most detected pitches should be near 440
        valid_pitches = pitches[~np.isnan(pitches)]
        if len(valid_pitches) > 0:
            median_pitch = np.median(valid_pitches)
            # Allow for some detection error
            self.assertLess(abs(median_pitch - 440), 100)


class TestAudioComparison(unittest.TestCase):
    """Test audio comparison between similar and different signals."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = AudioProcessor()
        
        # Create test signals
        duration = 1.0
        sr = 44100
        t = np.linspace(0, duration, int(duration * sr))
        
        self.audio_440 = np.sin(2 * np.pi * 440 * t)
        self.audio_450 = np.sin(2 * np.pi * 450 * t)  # Slightly different
        self.audio_880 = np.sin(2 * np.pi * 880 * t)  # Very different
    
    def test_similar_audio_features(self):
        """Test that similar audio has similar features."""
        features_440 = self.processor.get_audio_features(self.audio_440)
        features_450 = self.processor.get_audio_features(self.audio_450)
        
        # Duration should be the same
        self.assertAlmostEqual(
            features_440['duration'],
            features_450['duration'],
            places=2
        )
        
        # Spectral centroids should be close
        diff = abs(features_440['spectral_centroid_mean'] -
                  features_450['spectral_centroid_mean'])
        self.assertLess(diff, 100)  # Within 100 Hz
    
    def test_different_audio_features(self):
        """Test that different audio has different features."""
        features_440 = self.processor.get_audio_features(self.audio_440)
        features_880 = self.processor.get_audio_features(self.audio_880)
        
        # Spectral centroids should be significantly different
        diff = abs(features_440['spectral_centroid_mean'] -
                  features_880['spectral_centroid_mean'])
        self.assertGreater(diff, 200)  # More than 200 Hz difference


if __name__ == '__main__':
    unittest.main()
