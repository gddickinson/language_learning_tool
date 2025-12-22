"""
Core audio processing module for the Language Learning Tool.
Handles recording, playback, waveform analysis, and spectrogram generation.
"""
import numpy as np
import soundfile as sf
import sounddevice as sd
from scipy import signal
from scipy.fft import fft, fftfreq
import librosa
import os
from typing import Tuple, Optional, Dict
import config


class AudioProcessor:
    """Handles all audio recording, playback, and analysis operations."""
    
    def __init__(self, sample_rate: int = config.SAMPLE_RATE):
        """
        Initialize the AudioProcessor.
        
        Args:
            sample_rate: Sampling rate in Hz
        """
        self.sample_rate = sample_rate
        self.recording = None
        self.is_recording = False
        self.is_playing = False
        self.stream = None
        
    def record(self, duration: float) -> np.ndarray:
        """
        Record audio for specified duration.
        
        Args:
            duration: Recording duration in seconds
            
        Returns:
            Recorded audio as numpy array
        """
        self.is_recording = True
        recording = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=config.CHANNELS,
            dtype=config.FORMAT
        )
        sd.wait()
        self.is_recording = False
        self.recording = recording.flatten()
        return self.recording
    
    def start_recording(self):
        """Start continuous recording (for real-time display)."""
        self.is_recording = True
        self.recording = []
        
        def callback(indata, frames, time, status):
            if status:
                print(f"Recording status: {status}")
            self.recording.extend(indata[:, 0].copy())
        
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=config.CHANNELS,
            callback=callback
        )
        self.stream.start()
    
    def stop_recording(self) -> np.ndarray:
        """
        Stop continuous recording and return recorded audio.
        
        Returns:
            Recorded audio as numpy array
        """
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        self.is_recording = False
        self.recording = np.array(self.recording)
        return self.recording
    
    def play(self, audio: np.ndarray, sample_rate: Optional[int] = None):
        """
        Play audio data.
        
        Args:
            audio: Audio data as numpy array
            sample_rate: Sample rate (uses default if None)
        """
        if sample_rate is None:
            sample_rate = self.sample_rate
            
        self.is_playing = True
        sd.play(audio, sample_rate)
        sd.wait()
        self.is_playing = False
    
    def stop_playback(self):
        """Stop current audio playback."""
        sd.stop()
        self.is_playing = False
    
    def load_audio(self, filepath: str) -> Tuple[np.ndarray, int]:
        """
        Load audio file.
        
        Args:
            filepath: Path to audio file
            
        Returns:
            Tuple of (audio_data, sample_rate)
        """
        audio, sample_rate = sf.read(filepath)
        
        # Convert stereo to mono if needed
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)
        
        # Resample if necessary
        if sample_rate != self.sample_rate:
            audio = librosa.resample(
                audio,
                orig_sr=sample_rate,
                target_sr=self.sample_rate
            )
            sample_rate = self.sample_rate
        
        return audio, sample_rate
    
    def save_audio(self, audio: np.ndarray, filepath: str,
                   sample_rate: Optional[int] = None):
        """
        Save audio data to file.
        
        Args:
            audio: Audio data as numpy array
            filepath: Output file path
            sample_rate: Sample rate (uses default if None)
        """
        if sample_rate is None:
            sample_rate = self.sample_rate
            
        sf.write(filepath, audio, sample_rate)
    
    def get_waveform(self, audio: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get waveform data for plotting.
        
        Args:
            audio: Audio data
            
        Returns:
            Tuple of (time_array, amplitude_array)
        """
        time = np.arange(len(audio)) / self.sample_rate
        return time, audio
    
    def get_spectrogram(self, audio: np.ndarray,
                       nfft: int = config.NFFT,
                       noverlap: int = config.NOVERLAP) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Compute spectrogram using Short-Time Fourier Transform.
        
        Args:
            audio: Audio data
            nfft: FFT window size
            noverlap: Overlap between windows
            
        Returns:
            Tuple of (frequencies, times, spectrogram_db)
        """
        frequencies, times, spectrogram = signal.spectrogram(
            audio,
            fs=self.sample_rate,
            nperseg=nfft,
            noverlap=noverlap,
            scaling='density'
        )
        
        # Convert to dB scale
        spectrogram_db = 10 * np.log10(spectrogram + 1e-10)
        
        return frequencies, times, spectrogram_db
    
    def get_mfcc(self, audio: np.ndarray, n_mfcc: int = 13) -> np.ndarray:
        """
        Extract Mel-Frequency Cepstral Coefficients (MFCCs).
        These are commonly used features for speech analysis.
        
        Args:
            audio: Audio data
            n_mfcc: Number of MFCCs to extract
            
        Returns:
            MFCC features
        """
        mfcc = librosa.feature.mfcc(
            y=audio,
            sr=self.sample_rate,
            n_mfcc=n_mfcc
        )
        return mfcc
    
    def get_pitch(self, audio: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract pitch (fundamental frequency) from audio.
        
        Args:
            audio: Audio data
            
        Returns:
            Tuple of (times, pitches) where pitches are in Hz
        """
        # Use autocorrelation method for pitch detection
        pitches, voiced_flag, voiced_probs = librosa.pyin(
            audio,
            fmin=librosa.note_to_hz('C2'),
            fmax=librosa.note_to_hz('C7'),
            sr=self.sample_rate
        )
        
        # Create time array
        times = librosa.times_like(pitches, sr=self.sample_rate)
        
        return times, pitches
    
    def normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """
        Normalize audio to -1 to 1 range.
        
        Args:
            audio: Audio data
            
        Returns:
            Normalized audio
        """
        max_val = np.abs(audio).max()
        if max_val > 0:
            return audio / max_val
        return audio
    
    def trim_silence(self, audio: np.ndarray,
                    threshold_db: float = -40) -> np.ndarray:
        """
        Trim silence from beginning and end of audio.
        
        Args:
            audio: Audio data
            threshold_db: Threshold in dB below which is considered silence
            
        Returns:
            Trimmed audio
        """
        trimmed, _ = librosa.effects.trim(
            audio,
            top_db=-threshold_db
        )
        return trimmed
    
    def get_audio_features(self, audio: np.ndarray) -> Dict:
        """
        Extract comprehensive audio features for analysis.
        
        Args:
            audio: Audio data
            
        Returns:
            Dictionary of audio features
        """
        features = {}
        
        # Basic features
        features['duration'] = len(audio) / self.sample_rate
        features['sample_rate'] = self.sample_rate
        features['rms_energy'] = np.sqrt(np.mean(audio**2))
        features['max_amplitude'] = np.max(np.abs(audio))
        
        # Spectral features
        spectral_centroid = librosa.feature.spectral_centroid(
            y=audio, sr=self.sample_rate
        )[0]
        features['spectral_centroid_mean'] = np.mean(spectral_centroid)
        features['spectral_centroid_std'] = np.std(spectral_centroid)
        
        # Zero crossing rate (useful for voice/unvoiced detection)
        zcr = librosa.feature.zero_crossing_rate(audio)[0]
        features['zero_crossing_rate_mean'] = np.mean(zcr)
        
        # MFCCs
        mfcc = self.get_mfcc(audio)
        for i in range(mfcc.shape[0]):
            features[f'mfcc_{i+1}_mean'] = np.mean(mfcc[i])
            features[f'mfcc_{i+1}_std'] = np.std(mfcc[i])
        
        return features


if __name__ == '__main__':
    # Unit test
    print("Testing AudioProcessor...")
    
    processor = AudioProcessor()
    
    # Test recording
    print("Recording 2 seconds of audio...")
    audio = processor.record(2.0)
    print(f"Recorded {len(audio)} samples")
    
    # Test saving
    test_file = os.path.join(config.TEMP_DIR, 'test.wav')
    processor.save_audio(audio, test_file)
    print(f"Saved to {test_file}")
    
    # Test loading
    loaded_audio, sr = processor.load_audio(test_file)
    print(f"Loaded {len(loaded_audio)} samples at {sr} Hz")
    
    # Test waveform
    time, amp = processor.get_waveform(loaded_audio)
    print(f"Waveform: {len(time)} time points")
    
    # Test spectrogram
    freqs, times, spec = processor.get_spectrogram(loaded_audio)
    print(f"Spectrogram: {spec.shape[0]} frequencies x {spec.shape[1]} time bins")
    
    # Test features
    features = processor.get_audio_features(loaded_audio)
    print(f"Extracted {len(features)} features")
    print(f"Duration: {features['duration']:.2f}s")
    print(f"RMS Energy: {features['rms_energy']:.4f}")
    
    # Cleanup
    os.remove(test_file)
    print("\nAll tests passed!")
