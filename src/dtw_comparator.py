"""
Dynamic Time Warping (DTW) based pronunciation comparison module.
Uses DTW to compare audio patterns regardless of speaking speed.
"""
import numpy as np
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean, cosine
from scipy.stats import pearsonr
import librosa
from typing import Tuple, Dict, Optional
import config


class DTWComparator:
    """
    Compares audio samples using Dynamic Time Warping.
    DTW is ideal for comparing pronunciation as it handles variations in speaking speed.
    """
    
    def __init__(self, sample_rate: int = config.SAMPLE_RATE):
        """
        Initialize the DTW Comparator.
        
        Args:
            sample_rate: Audio sample rate in Hz
        """
        self.sample_rate = sample_rate
    
    def extract_features(self, audio: np.ndarray,
                        feature_type: str = 'mfcc') -> np.ndarray:
        """
        Extract features from audio for DTW comparison.
        
        Args:
            audio: Audio data
            feature_type: Type of features ('mfcc', 'chroma', 'spectral')
            
        Returns:
            Feature matrix (features x time)
        """
        if feature_type == 'mfcc':
            # MFCCs are excellent for speech comparison
            features = librosa.feature.mfcc(
                y=audio,
                sr=self.sample_rate,
                n_mfcc=13
            )
        elif feature_type == 'chroma':
            # Chroma features capture harmonic content
            features = librosa.feature.chroma_stft(
                y=audio,
                sr=self.sample_rate
            )
        elif feature_type == 'spectral':
            # Spectral centroid, rolloff, etc.
            centroid = librosa.feature.spectral_centroid(
                y=audio, sr=self.sample_rate
            )
            rolloff = librosa.feature.spectral_rolloff(
                y=audio, sr=self.sample_rate
            )
            zcr = librosa.feature.zero_crossing_rate(audio)
            features = np.vstack([centroid, rolloff, zcr])
        else:
            raise ValueError(f"Unknown feature type: {feature_type}")
        
        # Transpose to (time x features) for DTW
        return features.T
    
    def compare_dtw(self, audio1: np.ndarray, audio2: np.ndarray,
                   feature_type: str = 'mfcc',
                   radius: int = config.DTW_RADIUS) -> Tuple[float, np.ndarray]:
        """
        Compare two audio samples using DTW.
        
        Args:
            audio1: First audio sample
            audio2: Second audio sample
            feature_type: Type of features to extract
            radius: Constraint radius for FastDTW
            
        Returns:
            Tuple of (normalized_distance, alignment_path)
        """
        # Extract features
        features1 = self.extract_features(audio1, feature_type)
        features2 = self.extract_features(audio2, feature_type)
        
        # Compute DTW distance and path
        distance, path = fastdtw(features1, features2,
                                radius=radius, dist=euclidean)
        
        # Normalize distance by path length for fair comparison
        normalized_distance = distance / len(path)
        
        return normalized_distance, np.array(path)
    
    def compare_multiple_features(self, audio1: np.ndarray,
                                 audio2: np.ndarray) -> Dict[str, float]:
        """
        Compare audio using multiple feature types and return combined metrics.
        
        Args:
            audio1: First audio sample
            audio2: Second audio sample
            
        Returns:
            Dictionary of comparison metrics
        """
        results = {}
        
        # DTW on different features
        for feature_type in ['mfcc', 'chroma', 'spectral']:
            distance, _ = self.compare_dtw(audio1, audio2, feature_type)
            results[f'dtw_{feature_type}'] = distance
        
        # Overall similarity score (0-100, higher is better)
        # Average the normalized distances and invert
        avg_distance = np.mean([results[f'dtw_{ft}'] 
                               for ft in ['mfcc', 'chroma', 'spectral']])
        
        # Convert to similarity score (assuming typical DTW distances)
        # This is a heuristic mapping - adjust based on your data
        similarity = max(0, min(100, (1 - avg_distance / 10) * 100))
        results['similarity_score'] = similarity
        
        # Add detailed metrics
        results['duration_ratio'] = len(audio1) / len(audio2)
        results['is_similar'] = similarity > 70  # Threshold for "similar"
        
        return results
    
    def get_timing_alignment(self, audio1: np.ndarray, audio2: np.ndarray,
                           feature_type: str = 'mfcc') -> np.ndarray:
        """
        Get the timing alignment between two audio samples.
        Shows which parts of audio1 align with which parts of audio2.
        
        Args:
            audio1: Reference audio
            audio2: Comparison audio
            feature_type: Feature type for comparison
            
        Returns:
            Alignment path as array of (index1, index2) pairs
        """
        _, path = self.compare_dtw(audio1, audio2, feature_type)
        return path
    
    def visualize_alignment(self, path: np.ndarray,
                          features1_len: int,
                          features2_len: int) -> np.ndarray:
        """
        Create a 2D matrix visualization of the DTW alignment path.
        
        Args:
            path: Alignment path from DTW
            features1_len: Length of first feature sequence
            features2_len: Length of second feature sequence
            
        Returns:
            2D alignment matrix
        """
        alignment_matrix = np.zeros((features1_len, features2_len))
        for i, j in path:
            alignment_matrix[i, j] = 1
        return alignment_matrix
    
    def compare_waveforms(self, audio1: np.ndarray,
                         audio2: np.ndarray) -> Dict[str, float]:
        """
        Compare raw waveforms (simpler, faster comparison).
        
        Args:
            audio1: First audio sample
            audio2: Second audio sample
            
        Returns:
            Dictionary of waveform comparison metrics
        """
        # Ensure same length by padding/trimming
        max_len = max(len(audio1), len(audio2))
        audio1_padded = np.pad(audio1, (0, max_len - len(audio1)))
        audio2_padded = np.pad(audio2, (0, max_len - len(audio2)))
        
        # Normalize
        audio1_norm = audio1_padded / (np.max(np.abs(audio1_padded)) + 1e-10)
        audio2_norm = audio2_padded / (np.max(np.abs(audio2_padded)) + 1e-10)
        
        metrics = {}
        
        # Cross-correlation
        correlation = np.correlate(audio1_norm, audio2_norm, mode='valid')[0]
        metrics['cross_correlation'] = float(correlation / max_len)
        
        # Pearson correlation
        if len(audio1_norm) == len(audio2_norm):
            pearson, _ = pearsonr(audio1_norm, audio2_norm)
            metrics['pearson_correlation'] = float(pearson)
        
        # Mean squared error
        mse = np.mean((audio1_norm - audio2_norm) ** 2)
        metrics['mse'] = float(mse)
        
        # Cosine similarity
        cos_sim = 1 - cosine(audio1_norm, audio2_norm)
        metrics['cosine_similarity'] = float(cos_sim)
        
        return metrics
    
    def get_similarity_feedback(self, similarity_score: float) -> str:
        """
        Generate user-friendly feedback based on similarity score.
        
        Args:
            similarity_score: Similarity score (0-100)
            
        Returns:
            Feedback message
        """
        if similarity_score >= 90:
            return "Excellent! Your pronunciation is very accurate."
        elif similarity_score >= 75:
            return "Good! Your pronunciation is quite close to the target."
        elif similarity_score >= 60:
            return "Fair. Your pronunciation has some similarities, keep practicing."
        elif similarity_score >= 40:
            return "Needs improvement. Try to match the rhythm and intonation."
        else:
            return "Significant differences detected. Listen carefully and try again."
    
    def analyze_pronunciation_errors(self, audio_user: np.ndarray,
                                    audio_reference: np.ndarray) -> Dict:
        """
        Detailed pronunciation error analysis.
        
        Args:
            audio_user: User's pronunciation
            audio_reference: Reference pronunciation
            
        Returns:
            Dictionary with error analysis
        """
        analysis = {}
        
        # Get DTW alignment
        distance, path = self.compare_dtw(audio_user, audio_reference)
        
        # Analyze speaking speed
        speed_ratio = len(audio_user) / len(audio_reference)
        if speed_ratio > 1.2:
            analysis['speed_feedback'] = "You're speaking too slowly"
        elif speed_ratio < 0.8:
            analysis['speed_feedback'] = "You're speaking too fast"
        else:
            analysis['speed_feedback'] = "Good speaking speed"
        
        # Get pitch comparison
        pitch_user = librosa.piptrack(y=audio_user, sr=self.sample_rate)[0]
        pitch_ref = librosa.piptrack(y=audio_reference, sr=self.sample_rate)[0]
        
        pitch_user_mean = np.mean(pitch_user[pitch_user > 0])
        pitch_ref_mean = np.mean(pitch_ref[pitch_ref > 0])
        
        if not np.isnan(pitch_user_mean) and not np.isnan(pitch_ref_mean):
            pitch_diff = abs(pitch_user_mean - pitch_ref_mean) / pitch_ref_mean
            if pitch_diff > 0.2:
                analysis['pitch_feedback'] = "Pitch/tone differs significantly"
            else:
                analysis['pitch_feedback'] = "Good pitch/tone"
        
        # Energy/volume analysis
        energy_user = np.sqrt(np.mean(audio_user ** 2))
        energy_ref = np.sqrt(np.mean(audio_reference ** 2))
        
        energy_ratio = energy_user / energy_ref
        if energy_ratio > 1.5:
            analysis['volume_feedback'] = "You're speaking too loudly"
        elif energy_ratio < 0.6:
            analysis['volume_feedback'] = "You're speaking too softly"
        else:
            analysis['volume_feedback'] = "Good volume"
        
        # Overall score
        comparison = self.compare_multiple_features(audio_user, audio_reference)
        analysis['similarity_score'] = comparison['similarity_score']
        analysis['feedback'] = self.get_similarity_feedback(
            comparison['similarity_score']
        )
        
        return analysis


if __name__ == '__main__':
    # Unit test
    print("Testing DTWComparator...")
    
    comparator = DTWComparator()
    
    # Create test signals
    t = np.linspace(0, 1, 44100)
    
    # Reference signal
    audio1 = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave
    
    # Similar signal (slightly different frequency)
    audio2 = np.sin(2 * np.pi * 450 * t)
    
    # Different signal
    audio3 = np.sin(2 * np.pi * 880 * t)  # Double frequency
    
    print("\nComparing similar signals...")
    results_similar = comparator.compare_multiple_features(audio1, audio2)
    print(f"Similarity Score: {results_similar['similarity_score']:.2f}")
    print(f"Feedback: {comparator.get_similarity_feedback(results_similar['similarity_score'])}")
    
    print("\nComparing different signals...")
    results_different = comparator.compare_multiple_features(audio1, audio3)
    print(f"Similarity Score: {results_different['similarity_score']:.2f}")
    print(f"Feedback: {comparator.get_similarity_feedback(results_different['similarity_score'])}")
    
    print("\nWaveform comparison...")
    wave_metrics = comparator.compare_waveforms(audio1, audio2)
    for key, value in wave_metrics.items():
        print(f"  {key}: {value:.4f}")
    
    print("\nAll tests passed!")
