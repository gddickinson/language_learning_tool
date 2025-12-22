#!/usr/bin/env python3
"""
Example script demonstrating programmatic use of the Language Learning Tool modules.
This can be used as a starting point for custom scripts or automation.
"""
import sys
import os
import numpy as np

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from audio_processor import AudioProcessor
from dtw_comparator import DTWComparator
from database_manager import DatabaseManager
from downloader import SampleDownloader


def example_1_basic_recording_and_analysis():
    """Example 1: Record audio and analyze it."""
    print("=" * 60)
    print("Example 1: Basic Recording and Analysis")
    print("=" * 60)
    
    processor = AudioProcessor()
    
    # Record audio (3 seconds)
    print("\nRecording 3 seconds of audio...")
    print("Please speak into your microphone!")
    audio = processor.record(3.0)
    print(f"Recorded {len(audio)} samples")
    
    # Get waveform
    time, amplitude = processor.get_waveform(audio)
    print(f"Waveform: {len(time)} time points")
    
    # Get spectrogram
    freqs, times, spec = processor.get_spectrogram(audio)
    print(f"Spectrogram: {spec.shape[0]} frequencies x {spec.shape[1]} time bins")
    
    # Extract features
    features = processor.get_audio_features(audio)
    print(f"\nAudio Features:")
    print(f"  Duration: {features['duration']:.2f} seconds")
    print(f"  RMS Energy: {features['rms_energy']:.4f}")
    print(f"  Spectral Centroid: {features['spectral_centroid_mean']:.2f} Hz")
    
    # Save to file
    output_path = "/tmp/example_recording.wav"
    processor.save_audio(audio, output_path)
    print(f"\nSaved to: {output_path}")


def example_2_compare_two_signals():
    """Example 2: Compare two audio signals."""
    print("\n" + "=" * 60)
    print("Example 2: Comparing Two Signals")
    print("=" * 60)
    
    # Create synthetic test signals
    duration = 1.0
    sr = 44100
    t = np.linspace(0, duration, int(duration * sr))
    
    # Reference: 440 Hz sine wave (A4 note)
    reference = np.sin(2 * np.pi * 440 * t)
    
    # User attempt: 445 Hz (slightly off)
    user_attempt = np.sin(2 * np.pi * 445 * t)
    
    # Compare using DTW
    comparator = DTWComparator()
    
    print("\nComparing reference (440 Hz) with user attempt (445 Hz)...")
    results = comparator.compare_multiple_features(user_attempt, reference)
    
    print(f"\nResults:")
    print(f"  Similarity Score: {results['similarity_score']:.2f}/100")
    print(f"  DTW MFCC Distance: {results['dtw_mfcc']:.4f}")
    print(f"  DTW Chroma Distance: {results['dtw_chroma']:.4f}")
    print(f"  DTW Spectral Distance: {results['dtw_spectral']:.4f}")
    print(f"  Is Similar: {results['is_similar']}")
    
    # Get detailed analysis
    analysis = comparator.analyze_pronunciation_errors(user_attempt, reference)
    print(f"\nDetailed Feedback:")
    print(f"  {analysis['feedback']}")
    print(f"  Speed: {analysis['speed_feedback']}")
    print(f"  Pitch: {analysis.get('pitch_feedback', 'N/A')}")
    print(f"  Volume: {analysis.get('volume_feedback', 'N/A')}")


def example_3_database_operations():
    """Example 3: Database operations."""
    print("\n" + "=" * 60)
    print("Example 3: Database Operations")
    print("=" * 60)
    
    # Use temporary database
    import tempfile
    temp_db = os.path.join(tempfile.gettempdir(), 'example.db')
    
    db = DatabaseManager(temp_db)
    
    # Add samples
    print("\nAdding sample pronunciations...")
    
    sample1_id = db.add_sample(
        word='hello',
        language='en',
        filepath='/tmp/hello_speaker1.wav',
        source='example',
        speaker='Speaker 1',
        category='greetings',
        duration=1.2
    )
    print(f"Added sample 1: ID={sample1_id}")
    
    sample2_id = db.add_sample(
        word='hello',
        language='en',
        filepath='/tmp/hello_speaker2.wav',
        source='example',
        speaker='Speaker 2',
        category='greetings',
        duration=1.5
    )
    print(f"Added sample 2: ID={sample2_id}")
    
    # Search samples
    print("\nSearching for 'hello' samples...")
    samples = db.get_samples(word='hello', language='en')
    print(f"Found {len(samples)} samples:")
    for sample in samples:
        print(f"  - {sample['word']} by {sample['speaker']} ({sample['duration']:.1f}s)")
    
    # Add user recording
    print("\nAdding user practice recording...")
    recording_id = db.add_user_recording(
        word='hello',
        language='en',
        filepath='/tmp/user_hello.wav',
        reference_id=sample1_id,
        similarity_score=78.5,
        feedback='Good attempt! Work on intonation.'
    )
    print(f"Added user recording: ID={recording_id}")
    
    # Get practice history
    print("\nPractice history:")
    history = db.get_practice_history()
    for entry in history:
        print(f"  - {entry['word']}: {entry['attempts']} attempts, "
              f"best score: {entry['best_score']:.1f}")
    
    # Get statistics
    print("\nDatabase statistics:")
    stats = db.get_statistics()
    print(f"  Total samples: {stats['total_samples']}")
    print(f"  Total recordings: {stats['total_recordings']}")
    print(f"  Languages: {', '.join(stats['languages'])}")
    
    # Cleanup
    os.remove(temp_db)
    print(f"\nCleaned up temporary database")


def example_4_download_suggestions():
    """Example 4: Get suggested vocabulary."""
    print("\n" + "=" * 60)
    print("Example 4: Vocabulary Suggestions")
    print("=" * 60)
    
    downloader = SampleDownloader()
    
    # Get suggested words for different categories
    categories = ['greetings', 'numbers', 'colors', 'days']
    
    for category in categories:
        words = downloader.get_suggested_words(category)
        print(f"\n{category.title()}:")
        print(f"  {', '.join(words[:5])}...")  # Show first 5


def example_5_batch_processing():
    """Example 5: Batch process multiple recordings."""
    print("\n" + "=" * 60)
    print("Example 5: Batch Processing")
    print("=" * 60)
    
    # Create synthetic signals for demonstration
    duration = 1.0
    sr = 44100
    t = np.linspace(0, duration, int(duration * sr))
    
    # Reference
    reference = np.sin(2 * np.pi * 440 * t)
    
    # Multiple user attempts with varying quality
    attempts = [
        np.sin(2 * np.pi * 440 * t),      # Perfect match
        np.sin(2 * np.pi * 445 * t),      # Slightly off
        np.sin(2 * np.pi * 460 * t),      # More off
        np.sin(2 * np.pi * 880 * t),      # Very different
    ]
    
    comparator = DTWComparator()
    
    print("\nProcessing 4 pronunciation attempts...")
    
    results = []
    for i, attempt in enumerate(attempts, 1):
        result = comparator.compare_multiple_features(attempt, reference)
        results.append(result)
        print(f"  Attempt {i}: Score = {result['similarity_score']:.1f}/100")
    
    # Find best attempt
    best_idx = max(range(len(results)), 
                   key=lambda i: results[i]['similarity_score'])
    print(f"\nBest attempt: #{best_idx + 1} "
          f"(Score: {results[best_idx]['similarity_score']:.1f})")
    
    # Calculate average score
    avg_score = sum(r['similarity_score'] for r in results) / len(results)
    print(f"Average score: {avg_score:.1f}")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Language Learning Tool - Usage Examples")
    print("=" * 60)
    
    try:
        # Example 1: Recording (requires microphone)
        # Uncomment to test recording:
        # example_1_basic_recording_and_analysis()
        
        # Example 2: Signal comparison (no hardware required)
        example_2_compare_two_signals()
        
        # Example 3: Database operations
        example_3_database_operations()
        
        # Example 4: Vocabulary suggestions
        example_4_download_suggestions()
        
        # Example 5: Batch processing
        example_5_batch_processing()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
