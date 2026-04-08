"""
Live comparison tab — real-time microphone monitoring with DTW alignment.
"""

import os
import time

import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QSlider,
    QTextEdit, QVBoxLayout, QWidget,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

import config
from waveform_canvas import WaveformCanvas
from alignment_utils import apply_dtw_warping, calculate_path_smoothness


class LiveComparisonTab(QWidget):
    """Tab for live comparison with real-time microphone overlay."""

    def __init__(self, audio_processor, dtw_comparator, db_manager):
        super().__init__()
        self.audio = audio_processor
        self.dtw = dtw_comparator
        self.db = db_manager

        self.reference_audio = None
        self.is_monitoring = False
        self.recorded_segments = []

        self.init_ui()

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_live_display)

    def init_ui(self):
        layout = QVBoxLayout()

        # Controls
        controls = QHBoxLayout()
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("Enter word...")
        controls.addWidget(QLabel("Word:"))
        controls.addWidget(self.word_input)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["en", "es", "fr", "de", "it", "pt", "ja"])
        controls.addWidget(QLabel("Language:"))
        controls.addWidget(self.lang_combo)

        self.load_ref_btn = QPushButton("Load Reference")
        self.load_ref_btn.clicked.connect(self.load_reference)
        controls.addWidget(self.load_ref_btn)

        self.play_ref_btn = QPushButton("Play Reference")
        self.play_ref_btn.clicked.connect(self.play_reference)
        self.play_ref_btn.setEnabled(False)
        controls.addWidget(self.play_ref_btn)
        layout.addLayout(controls)

        # Monitoring controls
        monitor_layout = QHBoxLayout()
        self.start_monitor_btn = QPushButton("Start Live Monitoring")
        self.start_monitor_btn.clicked.connect(self.start_monitoring)
        self.start_monitor_btn.setEnabled(False)
        self.start_monitor_btn.setStyleSheet("font-size: 14pt; padding: 10px;")
        monitor_layout.addWidget(self.start_monitor_btn)

        self.stop_monitor_btn = QPushButton("Stop Monitoring")
        self.stop_monitor_btn.clicked.connect(self.stop_monitoring)
        self.stop_monitor_btn.setEnabled(False)
        self.stop_monitor_btn.setStyleSheet("font-size: 14pt; padding: 10px;")
        monitor_layout.addWidget(self.stop_monitor_btn)

        monitor_layout.addWidget(QLabel("Detection Threshold:"))
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setMinimum(1)
        self.threshold_slider.setMaximum(100)
        self.threshold_slider.setValue(20)
        self.threshold_slider.setTickPosition(QSlider.TicksBelow)
        self.threshold_slider.setTickInterval(10)
        monitor_layout.addWidget(self.threshold_slider)
        layout.addLayout(monitor_layout)

        # Canvas
        self.canvas = WaveformCanvas(dual_spec=True)
        layout.addWidget(self.canvas)

        # Feedback
        feedback_group = QGroupBox("Live Feedback & Alignment Info")
        feedback_layout = QVBoxLayout()

        similarity_layout = QHBoxLayout()
        self.similarity_label = QLabel("Similarity: --")
        self.similarity_label.setFont(QFont("Arial", 16, QFont.Bold))
        similarity_layout.addWidget(self.similarity_label)
        similarity_layout.addStretch()

        save_btn = QPushButton("Save Comparison")
        save_btn.setMaximumWidth(150)
        save_btn.clicked.connect(self.save_comparison)
        similarity_layout.addWidget(save_btn)

        help_btn = QPushButton("Help")
        help_btn.setMaximumWidth(100)
        help_btn.clicked.connect(self.show_alignment_help)
        similarity_layout.addWidget(help_btn)
        feedback_layout.addLayout(similarity_layout)

        self.feedback_text = QTextEdit()
        self.feedback_text.setReadOnly(True)
        self.feedback_text.setMaximumHeight(100)
        feedback_layout.addWidget(self.feedback_text)

        feedback_group.setLayout(feedback_layout)
        layout.addWidget(feedback_group)

        self.status_label = QLabel("Load a reference to begin")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    # ── reference ─────────────────────────────────────────────────────────

    def load_reference(self):
        word = self.word_input.text().strip()
        language = self.lang_combo.currentText()
        if not word:
            QMessageBox.warning(self, "Input Required", "Please enter a word")
            return

        samples = self.db.get_samples(word=word, language=language)
        if samples:
            filepath = samples[0]["filepath"]
            if os.path.exists(filepath):
                self.reference_audio, _ = self.audio.load_audio(filepath)
                self.display_reference()
                self.play_ref_btn.setEnabled(True)
                self.start_monitor_btn.setEnabled(True)
                self.status_label.setText(
                    f"Reference loaded for '{word}' - Ready to monitor"
                )
            else:
                QMessageBox.warning(self, "File Not Found",
                                    f"File not found: {filepath}")
        else:
            filepath, _ = QFileDialog.getOpenFileName(
                self, "Select Reference Audio", config.SAMPLES_DIR,
                "Audio Files (*.wav *.mp3 *.ogg *.flac)",
            )
            if filepath:
                self.reference_audio, _ = self.audio.load_audio(filepath)
                self.display_reference()
                self.play_ref_btn.setEnabled(True)
                self.start_monitor_btn.setEnabled(True)
                self.status_label.setText("Reference loaded - Ready to monitor")

    def display_reference(self):
        if self.reference_audio is None:
            return
        t, amp = self.audio.get_waveform(self.reference_audio)
        freqs, times, spec = self.audio.get_spectrogram(self.reference_audio)

        self.canvas.ax_wave.clear()
        self.canvas.ax_spec_ref.clear()
        self.canvas.ax_spec_user.clear()

        self.canvas.ax_wave.plot(t, amp, "b-", linewidth=1.0, label="Reference")
        self.canvas.ax_wave.set_xlabel("Time (s)")
        self.canvas.ax_wave.set_ylabel("Amplitude")
        self.canvas.ax_wave.set_title(
            "Reference Waveform (Blue) - Start Monitoring to Compare"
        )
        self.canvas.ax_wave.legend(loc="upper right")
        self.canvas.ax_wave.grid(True, alpha=0.3)

        freq_mask = freqs <= config.FREQ_MAX
        self.canvas.ax_spec_ref.pcolormesh(
            times, freqs[freq_mask], spec[freq_mask, :],
            shading="gouraud", cmap="viridis",
        )
        self.canvas.ax_spec_ref.set_ylabel("Frequency (Hz)")
        self.canvas.ax_spec_ref.set_title("Reference Spectrogram")
        self.canvas.ax_spec_ref.set_ylim([config.FREQ_MIN, config.FREQ_MAX])

        self.canvas.ax_spec_user.text(
            0.5, 0.5,
            "Your spectrogram will appear here\nwhen you start monitoring",
            horizontalalignment="center", verticalalignment="center",
            transform=self.canvas.ax_spec_user.transAxes,
            fontsize=12, style="italic", color="gray",
        )
        self.canvas.ax_spec_user.set_xlabel("Time (s)")
        self.canvas.ax_spec_user.set_ylabel("Frequency (Hz)")
        self.canvas.ax_spec_user.set_title("Your Spectrogram (Time-Warped)")

        self.canvas.figure.tight_layout()
        self.canvas.draw()

    def play_reference(self):
        if self.reference_audio is not None:
            self.audio.play(self.reference_audio)

    # ── monitoring ────────────────────────────────────────────────────────

    def start_monitoring(self):
        if self.reference_audio is None:
            return
        self.is_monitoring = True
        self.recorded_segments = []
        self.audio.start_recording()
        self.update_timer.start(100)
        self.start_monitor_btn.setEnabled(False)
        self.stop_monitor_btn.setEnabled(True)
        self.status_label.setText("Monitoring... Speak the word!")

    def stop_monitoring(self):
        self.is_monitoring = False
        self.update_timer.stop()
        user_audio = self.audio.stop_recording()
        self.start_monitor_btn.setEnabled(True)
        self.stop_monitor_btn.setEnabled(False)
        if len(user_audio) > 0:
            self.process_and_compare(user_audio)
        self.status_label.setText("Monitoring stopped")

    def update_live_display(self):
        if not self.is_monitoring or not self.audio.recording:
            return
        current_audio = np.array(self.audio.recording)
        if len(current_audio) < 1000:
            return
        threshold = self.threshold_slider.value() / 100.0
        energy = np.sqrt(np.mean(current_audio[-4410:] ** 2))
        if energy > threshold:
            self.detect_and_align(current_audio)

    def detect_and_align(self, audio_buffer):
        threshold = self.threshold_slider.value() / 100.0
        frame_size = 2205

        energy_profile = []
        for i in range(0, len(audio_buffer) - frame_size, frame_size):
            frame = audio_buffer[i : i + frame_size]
            energy_profile.append(np.sqrt(np.mean(frame ** 2)))
        energy_profile = np.array(energy_profile)

        onset_frames = np.where(energy_profile > threshold)[0]
        if len(onset_frames) == 0:
            return

        onset_idx = onset_frames[0] * frame_size
        pre_roll = int(0.05 * self.audio.sample_rate)
        start_idx = max(0, onset_idx - pre_roll)
        segment = audio_buffer[start_idx:]

        if len(segment) < len(self.reference_audio) * 0.3:
            return

        segment = self.audio.normalize_audio(segment)
        max_length = len(self.reference_audio) * 2
        if len(segment) > max_length:
            segment = segment[:max_length]

        try:
            results = self.dtw.compare_multiple_features(segment, self.reference_audio)
            analysis = self.dtw.analyze_pronunciation_errors(segment, self.reference_audio)
            score = results["similarity_score"]
            self.similarity_label.setText(f"Similarity: {score:.1f}/100")

            color = ("green" if score >= 85 else "lightgreen" if score >= 70
                     else "orange" if score >= 50 else "red")
            self.similarity_label.setStyleSheet(f"color: {color}; font-weight: bold;")

            duration_ratio = len(segment) / len(self.reference_audio)
            timing_penalty = abs(1.0 - duration_ratio)

            parts = [self.dtw.get_similarity_feedback(score)]
            if timing_penalty > 0.3:
                parts.append(f"\nTiming: {analysis.get('speed_feedback', 'N/A')}")
                parts.append(f"   (Duration ratio: {duration_ratio:.2f}x reference)")
            if "pitch_feedback" in analysis and "differs" in analysis["pitch_feedback"].lower():
                parts.append(f"\n{analysis['pitch_feedback']}")
            if "volume_feedback" in analysis and "too" in analysis["volume_feedback"].lower():
                parts.append(f"\n{analysis['volume_feedback']}")

            self.feedback_text.setText("".join(parts))
            self.overlay_visualization(segment)
        except Exception as e:
            print(f"Live comparison error: {e}")

    def overlay_visualization(self, user_segment):
        ref_norm = self.audio.normalize_audio(self.reference_audio)
        user_norm = self.audio.normalize_audio(user_segment)

        alignment_quality = "Good"
        try:
            _, dtw_path = self.dtw.compare_dtw(
                user_segment, self.reference_audio, "mfcc",
            )
            user_aligned = apply_dtw_warping(user_norm, ref_norm, dtw_path)
            smoothness = calculate_path_smoothness(dtw_path)
            if smoothness > 0.5:
                alignment_quality = "Excellent"
            elif smoothness > 0.3:
                alignment_quality = "Good"
            elif smoothness > 0.15:
                alignment_quality = "Fair"
            else:
                alignment_quality = "Poor"
        except Exception as e:
            print(f"DTW alignment warning: {e}")
            alignment_quality = "Fallback"
            ref_len = len(ref_norm)
            if len(user_norm) < ref_len:
                user_aligned = np.pad(user_norm, (0, ref_len - len(user_norm)))
            else:
                user_aligned = user_norm[:ref_len]

        correlation = np.corrcoef(ref_norm, user_aligned)[0, 1]

        freqs_ref, times_ref, spec_ref = self.audio.get_spectrogram(ref_norm)
        freqs_user, times_user, spec_user = self.audio.get_spectrogram(user_aligned)
        t = np.arange(len(ref_norm)) / self.audio.sample_rate

        self.canvas.plot_dual_spectrograms(
            t, ref_norm, user_aligned,
            freqs_ref, times_ref, spec_ref,
            freqs_user, times_user, spec_user,
        )

        title_suffix = (
            f" | Alignment: {alignment_quality} | Correlation: {correlation:.2f}"
        )
        current_title = self.canvas.ax_wave.get_title()
        if "|" in current_title:
            current_title = current_title.split("|")[0].strip()
        self.canvas.ax_wave.set_title(current_title + title_suffix)
        self.canvas.draw()

    # ── final processing ─────────────────────────────────────────────────

    def process_and_compare(self, user_audio):
        if self.reference_audio is None or len(user_audio) == 0:
            return

        user_audio = self.audio.trim_silence(user_audio)
        user_audio = self.audio.normalize_audio(user_audio)
        if len(user_audio) < 0.1 * self.audio.sample_rate:
            self.status_label.setText("Recording too short - try again")
            return

        results = self.dtw.compare_multiple_features(user_audio, self.reference_audio)
        analysis = self.dtw.analyze_pronunciation_errors(user_audio, self.reference_audio)
        score = results["similarity_score"]

        self.similarity_label.setText(f"Final Similarity: {score:.1f}/100")
        color = ("green" if score >= 85 else "lightgreen" if score >= 70
                 else "orange" if score >= 50 else "red")
        self.similarity_label.setStyleSheet(f"color: {color}; font-weight: bold;")

        duration_ratio = len(user_audio) / len(self.reference_audio)
        parts = ["=== FINAL ANALYSIS ===\n"]
        parts.append(f"Overall: {self.dtw.get_similarity_feedback(score)}\n")
        parts.append(f"\nDetailed Metrics:")
        parts.append(f"\n  Similarity Score: {score:.1f}/100")
        parts.append(f"\n  Duration Ratio: {duration_ratio:.2f}x reference")
        if "mfcc_similarity" in results:
            parts.append(f"\n  Phonetic Match: {results['mfcc_similarity']:.1f}%")
        if "chroma_similarity" in results:
            parts.append(f"\n  Tonal Match: {results['chroma_similarity']:.1f}%")

        parts.append(f"\n\nSpecific Feedback:")
        parts.append(f"\n  {analysis.get('speed_feedback', 'N/A')}")
        parts.append(f"\n  {analysis.get('pitch_feedback', 'N/A')}")
        parts.append(f"\n  {analysis.get('volume_feedback', 'N/A')}")

        parts.append(f"\n\nRecommendations:")
        if score < 85:
            if duration_ratio > 1.2:
                parts.append(f"\n  Speak slower to match reference rhythm")
            elif duration_ratio < 0.8:
                parts.append(f"\n  Speak faster to match reference pace")
            if "pitch" in analysis and "differs" in analysis.get("pitch_feedback", "").lower():
                parts.append(f"\n  Focus on matching pitch contour")
            parts.append(f"\n  Compare the spectrograms to see frequency differences")
            parts.append(f"\n  Watch the orange shading for pronunciation issues")
        else:
            parts.append(f"\n  Excellent work! Keep practicing to maintain this level.")

        self.feedback_text.setText("".join(parts))
        self.overlay_visualization(user_audio)
        self.status_label.setText(f"Final analysis complete - Score: {score:.1f}/100")

    # ── save / help ──────────────────────────────────────────────────────

    def save_comparison(self):
        if self.reference_audio is None:
            QMessageBox.warning(self, "No Comparison",
                                "No comparison to save. Start monitoring first.")
            return

        word = self.word_input.text().strip() or "comparison"
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{word}_comparison_{timestamp}.png"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Comparison Image",
            os.path.join(config.TEMP_DIR, filename),
            "PNG Images (*.png);;All Files (*)",
        )
        if filepath:
            try:
                self.canvas.figure.savefig(filepath, dpi=300, bbox_inches="tight")
                self.status_label.setText(
                    f"Comparison saved: {os.path.basename(filepath)}"
                )
                QMessageBox.information(self, "Saved",
                                        f"Comparison saved to:\n{filepath}")
            except Exception as e:
                QMessageBox.warning(self, "Save Error",
                                    f"Failed to save image: {e}")

    def show_alignment_help(self):
        help_text = (
            "<h3>Understanding DTW Alignment</h3>"
            "<p><b>Top Panel:</b> Overlaid waveforms<br>"
            "Blue = Reference, Red = Your voice (time-warped), "
            "Orange = Differences</p>"
            "<p><b>Middle Panel:</b> Reference spectrogram</p>"
            "<p><b>Bottom Panel:</b> Your spectrogram (aligned)</p>"
            "<p><b>Tips:</b> Adjust threshold slider if detection is unreliable. "
            "Speak clearly in a quiet environment.</p>"
        )
        msg = QMessageBox()
        msg.setWindowTitle("DTW Alignment Help")
        msg.setTextFormat(Qt.RichText)
        msg.setText(help_text)
        msg.setIcon(QMessageBox.Information)
        msg.exec_()
