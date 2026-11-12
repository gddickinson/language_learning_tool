"""
Plain-text pronunciation report shown in the Practice tab (Qt-free, so it can be tested and mirrored by the web app).
"""


def score_colour(score):
    """Colour name used for the similarity score label (Practice and Live tabs)."""
    if score >= 85:
        return "green"
    if score >= 70:
        return "lightgreen"
    if score >= 50:
        return "orange"
    return "red"


def practice_report(score, correlation, alignment_quality, duration_ratio, results, analysis, overall):
    """Build the Practice tab's analysis text.

    Args:
        score: similarity score 0-100 (DTWComparator.compare_multiple_features).
        correlation: waveform correlation between the reference and the DTW-aligned recording.
        alignment_quality: "Excellent" / "Good" / "Fair" / "Poor" / "Fallback".
        duration_ratio: len(user) / len(reference).
        results: dict from compare_multiple_features.
        analysis: dict from analyze_pronunciation_errors.
        overall: DTWComparator.get_similarity_feedback(score).
    """
    parts = ["=== PRONUNCIATION ANALYSIS ===\n"]
    parts.append(f"Overall: {overall}\n")
    parts.append("\nDetailed Metrics:")
    parts.append(f"\n  Similarity Score: {score:.1f}/100")
    parts.append(f"\n  Alignment Quality: {alignment_quality}")
    parts.append(f"\n  Waveform Correlation: {correlation:.2f}")
    parts.append(f"\n  Duration Ratio: {duration_ratio:.2f}x reference")
    if "mfcc_similarity" in results:
        parts.append(f"\n  Phonetic Match: {results['mfcc_similarity']:.1f}%")
    if "chroma_similarity" in results:
        parts.append(f"\n  Tonal Match: {results['chroma_similarity']:.1f}%")
    if "spectral_similarity" in results:
        parts.append(f"\n  Spectral Match: {results['spectral_similarity']:.1f}%")

    parts.append("\n\nSpecific Feedback:")
    parts.append(f"\n  {analysis.get('speed_feedback', 'N/A')}")
    parts.append(f"\n  {analysis.get('pitch_feedback', 'N/A')}")
    parts.append(f"\n  {analysis.get('volume_feedback', 'N/A')}")

    parts.append("\n\nRecommendations:")
    if score < 85:
        if alignment_quality in ("Poor", "Fallback"):
            parts.append("\n  Poor alignment - check recording quality")
        if duration_ratio > 1.2:
            parts.append("\n  Speak slower to match reference rhythm")
        elif duration_ratio < 0.8:
            parts.append("\n  Speak faster to match reference pace")
        if "differs" in analysis.get("pitch_feedback", "").lower():
            parts.append("\n  Focus on matching pitch contour")
        if correlation < 0.6:
            parts.append("\n  Low correlation - pronunciation very different")
        parts.append("\n  Compare the spectrograms for frequency differences")
        parts.append("\n  Orange shading shows pronunciation differences")
    else:
        parts.append("\n  Excellent work! Keep practicing to maintain this level.")
    return "".join(parts)
