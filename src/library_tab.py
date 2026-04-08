"""
Library tab — browse and manage the pronunciation sample database.
"""

import os

from PyQt5.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

import config


class LibraryTab(QWidget):
    """Tab for browsing pronunciation library."""

    def __init__(self, db_manager, audio_processor):
        super().__init__()
        self.db = db_manager
        self.audio = audio_processor
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search words...")
        self.search_input.returnPressed.connect(self.search_samples)
        search_layout.addWidget(self.search_input)

        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.search_samples)
        search_layout.addWidget(search_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_samples)
        search_layout.addWidget(refresh_btn)

        layout.addLayout(search_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Word", "Language", "Source", "Speaker", "Duration (s)", "Actions",
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        add_btn = QPushButton("Add Sample from File")
        add_btn.clicked.connect(self.add_sample_from_file)
        layout.addWidget(add_btn)

        self.setLayout(layout)
        self.load_samples()

    def load_samples(self):
        samples = self.db.get_samples()
        self.populate_table(samples)

    def search_samples(self):
        search_term = self.search_input.text()
        samples = self.db.search_samples(search_term)
        self.populate_table(samples)

    def populate_table(self, samples):
        self.table.setRowCount(len(samples))
        for i, sample in enumerate(samples):
            self.table.setItem(i, 0, QTableWidgetItem(sample["word"]))
            self.table.setItem(i, 1, QTableWidgetItem(sample["language"]))
            self.table.setItem(i, 2, QTableWidgetItem(sample["source"]))
            self.table.setItem(i, 3, QTableWidgetItem(sample["speaker"]))
            duration = f"{sample['duration']:.2f}" if sample["duration"] else "N/A"
            self.table.setItem(i, 4, QTableWidgetItem(duration))

            play_btn = QPushButton("Play")
            play_btn.clicked.connect(
                lambda checked, fp=sample["filepath"]: self.play_sample(fp)
            )
            self.table.setCellWidget(i, 5, play_btn)

        self.table.resizeColumnsToContents()

    def play_sample(self, filepath):
        if os.path.exists(filepath):
            audio, _ = self.audio.load_audio(filepath)
            self.audio.play(audio)
        else:
            QMessageBox.warning(self, "File Not Found",
                                f"Audio file not found: {filepath}")

    def add_sample_from_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", "",
            "Audio Files (*.wav *.mp3 *.ogg *.flac)",
        )
        if not filepath:
            return

        word, ok = QMessageBox.getText(self, "Word/Phrase",
                                       "Enter the word or phrase:")
        if not ok or not word:
            return

        language, ok = QMessageBox.getText(self, "Language",
                                           "Enter language code (e.g., en, es):",
                                           text="en")
        if not ok:
            return

        audio, sr = self.audio.load_audio(filepath)
        duration = len(audio) / sr

        filename = os.path.basename(filepath)
        new_path = os.path.join(config.SAMPLES_DIR, language, filename)
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        self.audio.save_audio(audio, new_path, sr)

        self.db.add_sample(
            word=word, language=language, filepath=new_path,
            source="user", duration=duration, sample_rate=sr,
        )
        self.load_samples()
        QMessageBox.information(self, "Success", f"Added sample for '{word}'")
