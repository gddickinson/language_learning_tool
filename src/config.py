"""
Configuration settings for the Language Learning Tool.
"""
import os

# Audio settings
SAMPLE_RATE = 44100  # Hz
CHANNELS = 1  # Mono
CHUNK_SIZE = 1024
FORMAT = 'int16'  # 16-bit audio
MAX_RECORDING_DURATION = 30  # seconds

# Spectrogram settings
NFFT = 2048  # FFT window size
NOVERLAP = 1024  # Overlap between windows
FREQ_MIN = 50  # Hz - minimum frequency to display
FREQ_MAX = 8000  # Hz - maximum frequency for speech

# DTW comparison settings
DTW_DISTANCE_THRESHOLD = 0.3  # Similarity threshold (0-1, lower is more similar)
DTW_RADIUS = 1  # Constraint radius for FastDTW

# Database settings
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'samples.db')

# File paths
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
TEMP_DIR = os.path.join(DATA_DIR, 'temp')
SAMPLES_DIR = os.path.join(DATA_DIR, 'samples')

# Supported audio formats
SUPPORTED_FORMATS = ['.wav', '.mp3', '.ogg', '.flac']

# Download settings
FORVO_API_KEY = None  # User can add their API key
DOWNLOAD_TIMEOUT = 30  # seconds

# GUI settings
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
PLOT_UPDATE_INTERVAL = 50  # milliseconds

# Create directories if they don't exist
for directory in [DATA_DIR, TEMP_DIR, SAMPLES_DIR]:
    os.makedirs(directory, exist_ok=True)
