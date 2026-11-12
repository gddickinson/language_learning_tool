"""
Shared DTW alignment utilities used by PracticeTab and LiveComparisonTab.

Extracts duplicated warping/smoothness logic into one place.
"""

import numpy as np

# Hop length (samples) of the feature frames that DTWComparator.compare_dtw aligns (librosa's default, 512).
FEATURE_HOP_LENGTH = 512


def apply_dtw_warping(user_audio, ref_audio, dtw_path, hop_length=FEATURE_HOP_LENGTH):
    """Apply DTW warping to align user audio to reference timeline.

    Args:
        user_audio: User's normalised audio signal.
        ref_audio:  Reference audio signal.
        dtw_path:   DTW alignment path (list of (user_frame, ref_frame) tuples) over feature frames.
        hop_length: Samples per feature frame; frame k is centred on sample k * hop_length.

    Returns:
        Time-warped user audio aligned to reference length.
    """
    from scipy import interpolate

    ref_len = len(ref_audio)
    user_len = len(user_audio)

    dtw_path = np.array(dtw_path)
    # Feature-frame indices -> sample indices (frame k is centred on sample k * hop_length)
    user_indices = np.minimum(dtw_path[:, 0] * hop_length, user_len - 1)
    ref_indices = np.minimum(dtw_path[:, 1] * hop_length, ref_len - 1)

    # Remove duplicate reference indices, keep first occurrence
    unique_ref_indices = []
    unique_user_indices = []
    seen_ref = set()

    for u_idx, r_idx in zip(user_indices, ref_indices):
        if r_idx not in seen_ref:
            seen_ref.add(r_idx)
            unique_ref_indices.append(r_idx)
            unique_user_indices.append(u_idx)

    unique_ref_indices = np.array(unique_ref_indices)
    unique_user_indices = np.array(unique_user_indices)

    # Ensure start and end points
    if unique_ref_indices[0] != 0:
        unique_ref_indices = np.insert(unique_ref_indices, 0, 0)
        unique_user_indices = np.insert(unique_user_indices, 0, 0)

    if unique_ref_indices[-1] != ref_len - 1:
        unique_ref_indices = np.append(unique_ref_indices, ref_len - 1)
        unique_user_indices = np.append(
            unique_user_indices, min(user_len - 1, unique_user_indices[-1] + 1)
        )

    # Interpolation: ref_idx -> user_idx
    f = interpolate.interp1d(
        unique_ref_indices, unique_user_indices,
        kind="linear", bounds_error=False, fill_value="extrapolate",
    )

    ref_positions = np.arange(ref_len)
    user_positions = np.clip(f(ref_positions), 0, user_len - 1)

    user_sample_indices = np.arange(user_len)
    f_audio = interpolate.interp1d(
        user_sample_indices, user_audio,
        kind="cubic", bounds_error=False, fill_value=0.0,
    )

    warped_audio = f_audio(user_positions)
    return smooth_warped_audio(warped_audio)


def smooth_warped_audio(audio, window_size=5):
    """Apply light Savitzky-Golay smoothing to warped audio."""
    if len(audio) < window_size:
        return audio

    if window_size % 2 == 0:
        window_size += 1

    try:
        from scipy.signal import savgol_filter
        return savgol_filter(audio, window_size, 2)
    except Exception:
        return np.convolve(audio, np.ones(window_size) / window_size, mode="same")


def calculate_path_smoothness(dtw_path):
    """Return 0-1 smoothness score for a DTW path (higher = smoother)."""
    if len(dtw_path) < 3:
        return 0.0

    dtw_path = np.array(dtw_path)
    slopes = []
    for i in range(len(dtw_path) - 1):
        dx = dtw_path[i + 1][0] - dtw_path[i][0]
        dy = dtw_path[i + 1][1] - dtw_path[i][1]
        if dx != 0:
            slopes.append(dy / dx)

    if not slopes:
        return 0.0

    return 1.0 / (1.0 + np.var(slopes))
