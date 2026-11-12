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

# Similarity score (DTWComparator.compare_multiple_features). Before DTW both clips are peak-normalised and each
# feature set is put on a comparable scale: MFCCs from a log-mel spectrogram floored MFCC_TOP_DB below its peak,
# in units of 10 dB; spectral centroid and roll-off as fractions of the Nyquist frequency; chroma and zero-crossing
# rate as they are (0-1). Frame distances are Euclidean / sqrt(number of coefficients) (RMS per coefficient) and each
# DTW distance is divided by the path length. Each distance d becomes a 0-100 score 100 * exp(-d / d0); the overall
# score is the weighted mean. d0 comes from scripts/calibrate_score.py: the largest distance between a synthetic voice
# and its time-stretched (0.8x, 1.25x), pitch-shifted (+-6 %) and re-noised copies, divided by ln(100 / 70), so
# each such copy scores at least 70 on every feature.
MFCC_TOP_DB = 40.0
MFCC_SCALE_DB = 10.0
SCORE_D0 = {'mfcc': 0.71, 'chroma': 0.15, 'spectral': 0.023}
SCORE_WEIGHTS = {'mfcc': 0.5, 'chroma': 0.3, 'spectral': 0.2}

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
