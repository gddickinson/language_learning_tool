"""
Practice tab — record and compare pronunciation against a reference.
"""

import os
import time

import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QMessageBox, QPushButton, QSplitter,
    QTextEdit, QVBoxLayout, QWidget,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

import config
from waveform_canvas import WaveformCanvas
from alignment_utils import apply_dtw_warping, calculate_path_smoothness
from feedback_report import practice_report, score_colour


class PracticeTab(QWidget):
    """Tab for pronunciation practice and comparison."""

    def __init__(self, audio_processor, dtw_comparator, db_manager):
        super().__init__()
        self.audio = audio_processor
        self.dtw = dtw_comparator
        self.db = db_manager

        self.reference_audio = None
        self.user_audio = None
        self.current_reference_id = None

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Top controls
        controls = QHBoxLayout()

        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("Enter word or phrase...")
        controls.addWidget(QLabel("Word:"))
        controls.addWidget(self.word_input)

        self.language_combo = QComboBox()
        self.language_combo.addItems([
            "en", "es", "fr", "de", "it", "pt", "ja", "zh", "ru", "ar",
        ])
        controls.addWidget(QLabel("Language:"))
        controls.addWidget(self.language_combo)

        self.load_reference_btn = QPushButton("Load Reference")
        self.load_reference_btn.clicked.connect(self.load_reference)
        controls.addWidget(self.load_reference_btn)

        layout.addLayout(controls)

        # Split view
        splitter = QSplitter(Qt.Horizontal)

        # Reference panel
        ref_panel = QGroupBox("Reference Pronunciation")
        ref_layout = QVBoxLayout()
        ref_buttons = QHBoxLayout()
        self.ref_play_btn = QPushButton("Play Reference")
        self.ref_play_btn.clicked.connect(self.play_reference)
        self.ref_play_btn.setEnabled(False)
        ref_buttons.addWidget(self.ref_play_btn)
        ref_layout.addLayout(ref_buttons)
        self.ref_canvas = WaveformCanvas()
        ref_layout.addWidget(self.ref_canvas)
        ref_panel.setLayout(ref_layout)
        splitter.addWidget(ref_panel)

        # User panel
        user_panel = QGroupBox("Your Pronunciation (DTW-Aligned Comparison)")
        user_layout = QVBoxLayout()
        user_buttons = QHBoxLayout()

        self.record_btn = QPushButton("Record (3s)")
        self.record_btn.clicked.connect(self.record_audio)
        self.record_btn.setStyleSheet("font-size: 11pt; padding: 8px;")
        user_buttons.addWidget(self.record_btn)

        self.play_user_btn = QPushButton("Play Recording")
        self.play_user_btn.clicked.connect(self.play_user)
        self.play_user_btn.setEnabled(False)
        user_buttons.addWidget(self.play_user_btn)

        self.compare_btn = QPushButton("Compare")
        self.compare_btn.clicked.connect(self.compare_pronunciations)
        self.compare_btn.setEnabled(False)
        self.compare_btn.setStyleSheet("font-size: 11pt; padding: 8px;")
        user_buttons.addWidget(self.compare_btn)

        user_layout.addLayout(user_buttons)
        self.user_canvas = WaveformCanvas(dual_spec=True)
        user_layout.addWidget(self.user_canvas)
        user_panel.setLayout(user_layout)
        splitter.addWidget(user_panel)

        layout.addWidget(splitter)

        # Feedback panel
        feedback_panel = QGroupBox("Pronunciation Feedback & Analysis")
        feedback_layout = QVBoxLayout()

        score_row = QHBoxLayout()
        self.score_label = QLabel("Similarity Score: --")
        self.score_label.setFont(QFont("Arial", 14, QFont.Bold))
        score_row.addWidget(self.score_label)
        score_row.addStretch()

        save_btn = QPushButton("Save Comparison")
        save_btn.clicked.connect(self.save_comparison)
        save_btn.setMaximumWidth(150)
        score_row.addWidget(save_btn)

        help_btn = QPushButton("Help")
        help_btn.clicked.connect(self.show_alignment_help)
        help_btn.setMaximumWidth(100)
        score_row.addWidget(help_btn)

        feedback_layout.addLayout(score_row)
        self.feedback_text = QTextEdit()
        self.feedback_text.setReadOnly(True)
        self.feedback_text.setMaximumHeight(120)
        feedback_layout.addWidget(self.feedback_text)
        feedback_panel.setLayout(feedback_layout)
        layout.addWidget(feedback_panel)

        self.setLayout(layout)

    # ── actions ───────────────────────────────────────────────────────────

    def load_reference(self):
        word = self.word_input.text().strip()
        language = self.language_combo.currentText()
        if not word:
            QMessageBox.warning(self, "Input Required",
                                "Please enter a word or phrase")
            return

        samples = self.db.get_samples(word=word, language=language)
        if samples:
            sample = samples[0]
            filepath = sample["filepath"]
            if os.path.exists(filepath):
                self.reference_audio, _ = self.audio.load_audio(filepath)
                self.current_reference_id = sample["id"]
                self.display_reference()
                self.ref_play_btn.setEnabled(True)
                QMessageBox.information(self, "Success",
                                        f"Loaded reference for '{word}'")
            else:
                QMessageBox.warning(self, "File Not Found",
                                    f"Reference file not found: {filepath}")
        else:
            filepath, _ = QFileDialog.getOpenFileName(
                self, "Select Reference Audio", config.SAMPLES_DIR,
                "Audio Files (*.wav *.mp3 *.ogg *.flac)",
            )
            if filepath:
                self.reference_audio, _ = self.audio.load_audio(filepath)
                self.current_reference_id = None
                self.display_reference()
                self.ref_play_btn.setEnabled(True)

    def display_reference(self):
        if self.reference_audio is not None:
            t, amp = self.audio.get_waveform(self.reference_audio)
            freqs, times, spec = self.audio.get_spectrogram(self.reference_audio)
            self.ref_canvas.plot_audio(t, amp, freqs, times, spec, "Reference")

    def play_reference(self):
        if self.reference_audio is not None:
            self.audio.play(self.reference_audio)

    def record_audio(self):
        self.record_btn.setEnabled(False)
        self.record_btn.setText("Recording...")
        QApplication.processEvents()

        self.user_audio = self.audio.record(3.0)
        self.user_audio = self.audio.trim_silence(self.user_audio)
        self.user_audio = self.audio.normalize_audio(self.user_audio)

        self.display_user()
        self.record_btn.setEnabled(True)
        self.record_btn.setText("Record (3s)")
        self.play_user_btn.setEnabled(True)
        if self.reference_audio is not None:
            self.compare_btn.setEnabled(True)

    def display_user(self):
        if self.user_audio is not None:
            t, amp = self.audio.get_waveform(self.user_audio)
            freqs, times, spec = self.audio.get_spectrogram(self.user_audio)
            self.user_canvas.plot_audio(t, amp, freqs, times, spec, "Your Recording")

    def play_user(self):
        if self.user_audio is not None:
            self.audio.play(self.user_audio)

    def compare_pronunciations(self):
        if self.reference_audio is None or self.user_audio is None:
            return

        results = self.dtw.compare_multiple_features(
            self.user_audio, self.reference_audio,
        )
        analysis = self.dtw.analyze_pronunciation_errors(
            self.user_audio, self.reference_audio,
        )

        score = results["similarity_score"]
        self.display_aligned_comparison(score, results, analysis)

        word = self.word_input.text().strip()
        language = self.language_combo.currentText()
        if word:
            timestamp = int(time.time())
            filename = f"{word}_{language}_user_{timestamp}.wav"
            recordings_dir = os.path.join(config.SAMPLES_DIR, "user_recordings")
            os.makedirs(recordings_dir, exist_ok=True)
            filepath = os.path.join(recordings_dir, filename)
            self.audio.save_audio(self.user_audio, filepath)
            self.db.add_user_recording(
                word=word, language=language, filepath=filepath,
                reference_id=self.current_reference_id,
                similarity_score=score,
                feedback=analysis.get("feedback", ""),
            )

    # ── alignment / display ──────────────────────────────────────────────

    def display_aligned_comparison(self, score, results, analysis):
        ref_norm = self.audio.normalize_audio(self.reference_audio)
        user_norm = self.audio.normalize_audio(self.user_audio)

        alignment_quality = "Good"
        try:
            _, dtw_path = self.dtw.compare_dtw(
                self.user_audio, self.reference_audio, "mfcc",
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
            print(f"DTW alignment error: {e}")
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

        self.user_canvas.plot_dual_spectrograms(
            t, ref_norm, user_aligned,
            freqs_ref, times_ref, spec_ref,
            freqs_user, times_user, spec_user,
        )
        title_suffix = (
            f" | Alignment: {alignment_quality} | Correlation: {correlation:.2f}"
        )
        self.user_canvas.ax_wave.set_title(
            "DTW-Aligned Waveforms (Blue=Ref, Red=You, Orange=Diff)" + title_suffix
        )
        self.user_canvas.draw()
        self.display_comprehensive_feedback(
            score, correlation, alignment_quality, results, analysis,
        )

    def display_comprehensive_feedback(self, score, correlation,
                                       alignment_quality, results, analysis):
        duration_ratio = len(self.user_audio) / len(self.reference_audio)
        color = score_colour(score)
        self.score_label.setText(f"Similarity Score: {score:.1f}/100")
        self.score_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.feedback_text.setText(practice_report(
            score, correlation, alignment_quality, duration_ratio, results, analysis,
            self.dtw.get_similarity_feedback(score),
        ))

    # ── save / help ──────────────────────────────────────────────────────

    def save_comparison(self):
        if self.reference_audio is None or self.user_audio is None:
            QMessageBox.warning(self, "No Comparison",
                                "No comparison to save. Record and compare first.")
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
                self.user_canvas.figure.savefig(filepath, dpi=300, bbox_inches="tight")
                QMessageBox.information(self, "Saved",
                                        f"Comparison saved to:\n{filepath}")
            except Exception as e:
                QMessageBox.warning(self, "Save Error",
                                    f"Failed to save image: {e}")

    def show_alignment_help(self):
        help_text = (
            "<h3>Understanding DTW-Aligned Comparison</h3>"
            "<p><b>Top Panel:</b> Overlaid waveforms<br>"
            "Blue = Reference, Red = Your voice (time-warped), "
            "Orange shading = Differences</p>"
            "<p><b>Middle Panel:</b> Reference spectrogram</p>"
            "<p><b>Bottom Panel:</b> Your spectrogram (aligned)</p>"
            "<p><b>Alignment Quality:</b> Excellent/Good/Fair/Poor/Fallback</p>"
            "<p><b>Tips:</b> Record in quiet environment, speak clearly, "
            "compare spectrograms for frequency differences.</p>"
        )
        msg = QMessageBox()
        msg.setWindowTitle("DTW Alignment Help")
        msg.setTextFormat(Qt.RichText)
        msg.setText(help_text)
        msg.setIcon(QMessageBox.Information)
        msg.exec_()
