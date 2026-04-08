"""
Recording tab — record new pronunciation samples and add to database.
"""

import os
import time

from PyQt5.QtWidgets import (
    QApplication, QComboBox, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)
from PyQt5.QtGui import QFont

import config
from waveform_canvas import WaveformCanvas


class RecordingTab(QWidget):
    """Tab for recording and adding samples directly to database."""

    def __init__(self, audio_processor, db_manager):
        super().__init__()
        self.audio = audio_processor
        self.db = db_manager
        self.recorded_audio = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        control_group = QGroupBox("Record New Sample")
        control_layout = QVBoxLayout()

        # Metadata
        meta_layout = QHBoxLayout()
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("Word or phrase...")
        meta_layout.addWidget(QLabel("Word:"))
        meta_layout.addWidget(self.word_input)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems([
            "en", "es", "fr", "de", "it", "pt", "ja", "zh", "ru", "ar",
        ])
        meta_layout.addWidget(QLabel("Language:"))
        meta_layout.addWidget(self.lang_combo)

        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("e.g., greetings, numbers...")
        meta_layout.addWidget(QLabel("Category:"))
        meta_layout.addWidget(self.category_input)
        control_layout.addLayout(meta_layout)

        # Speaker
        speaker_layout = QHBoxLayout()
        self.speaker_input = QLineEdit()
        self.speaker_input.setPlaceholderText("Your name or 'Native Speaker'")
        speaker_layout.addWidget(QLabel("Speaker:"))
        speaker_layout.addWidget(self.speaker_input)

        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Optional notes...")
        speaker_layout.addWidget(QLabel("Notes:"))
        speaker_layout.addWidget(self.notes_input)
        control_layout.addLayout(speaker_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.duration_combo = QComboBox()
        self.duration_combo.addItems(["1 sec", "2 sec", "3 sec", "5 sec", "10 sec"])
        self.duration_combo.setCurrentText("3 sec")
        button_layout.addWidget(QLabel("Duration:"))
        button_layout.addWidget(self.duration_combo)

        self.record_btn = QPushButton("Record")
        self.record_btn.clicked.connect(self.record_sample)
        self.record_btn.setStyleSheet("font-size: 14pt; padding: 10px;")
        button_layout.addWidget(self.record_btn)

        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.play_recording)
        self.play_btn.setEnabled(False)
        button_layout.addWidget(self.play_btn)

        self.save_btn = QPushButton("Save to Database")
        self.save_btn.clicked.connect(self.save_to_database)
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet("font-size: 14pt; padding: 10px;")
        button_layout.addWidget(self.save_btn)
        control_layout.addLayout(button_layout)

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        self.canvas = WaveformCanvas()
        layout.addWidget(self.canvas)

        self.status_label = QLabel("Ready to record")
        self.status_label.setFont(QFont("Arial", 12))
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    # ── actions ───────────────────────────────────────────────────────────

    def record_sample(self):
        duration_text = self.duration_combo.currentText()
        duration = float(duration_text.split()[0])

        self.record_btn.setEnabled(False)
        self.status_label.setText(f"Recording {duration} seconds...")
        QApplication.processEvents()

        self.recorded_audio = self.audio.record(duration)
        self.recorded_audio = self.audio.trim_silence(self.recorded_audio)
        self.recorded_audio = self.audio.normalize_audio(self.recorded_audio)

        t, amp = self.audio.get_waveform(self.recorded_audio)
        freqs, times, spec = self.audio.get_spectrogram(self.recorded_audio)
        self.canvas.plot_audio(t, amp, freqs, times, spec, "Recorded Sample")

        self.record_btn.setEnabled(True)
        self.play_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.status_label.setText("Recording complete! Play to review, then save.")

    def play_recording(self):
        if self.recorded_audio is not None:
            self.audio.play(self.recorded_audio)

    def save_to_database(self):
        word = self.word_input.text().strip()
        language = self.lang_combo.currentText()

        if not word:
            QMessageBox.warning(self, "Input Required",
                                "Please enter the word or phrase")
            return
        if self.recorded_audio is None:
            QMessageBox.warning(self, "No Recording",
                                "Please record audio first")
            return

        speaker = self.speaker_input.text().strip() or "user"
        speaker_clean = speaker.replace(" ", "_")
        filename = f"{word}_{language}_{speaker_clean}_{int(time.time())}.wav"

        output_dir = os.path.join(config.SAMPLES_DIR, language)
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        self.audio.save_audio(self.recorded_audio, filepath)

        duration = len(self.recorded_audio) / self.audio.sample_rate
        category = self.category_input.text().strip()
        notes = self.notes_input.text().strip()
        metadata = {}
        if notes:
            metadata["notes"] = notes

        sample_id = self.db.add_sample(
            word=word, language=language, filepath=filepath,
            source="user_recording", speaker=speaker,
            category=category, duration=duration,
            sample_rate=self.audio.sample_rate,
            metadata=metadata if metadata else None,
        )

        self.status_label.setText(f"Saved to database (ID: {sample_id})")
        QMessageBox.information(self, "Success",
                                f"Sample saved for '{word}' in {language}")

        self.recorded_audio = None
        self.play_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.canvas.clear_plot()
