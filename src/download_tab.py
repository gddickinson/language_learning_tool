"""
Download tab — search and download pronunciation samples from Forvo.
"""

import os
import time

from PyQt5.QtWidgets import (
    QApplication, QComboBox, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QMessageBox, QProgressBar,
    QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

import config


class DownloadTab(QWidget):
    """Tab for downloading pronunciation samples from the internet."""

    def __init__(self, downloader, db, audio_processor):
        super().__init__()
        self.downloader = downloader
        self.db = db
        self.audio = audio_processor
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Search section
        search_group = QGroupBox("Search for Pronunciations")
        search_layout = QVBoxLayout()

        input_layout = QHBoxLayout()
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("Enter word or phrase...")
        input_layout.addWidget(QLabel("Word:"))
        input_layout.addWidget(self.word_input)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems([
            "en", "es", "fr", "de", "it", "pt", "ja",
            "zh", "ru", "ar", "ko", "hi", "nl", "sv",
        ])
        input_layout.addWidget(QLabel("Language:"))
        input_layout.addWidget(self.lang_combo)

        self.search_btn = QPushButton("Search Forvo")
        self.search_btn.clicked.connect(self.search_forvo)
        input_layout.addWidget(self.search_btn)

        search_layout.addLayout(input_layout)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "Username", "Country", "Votes", "Preview", "Download",
        ])
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        search_layout.addWidget(self.results_table)

        search_group.setLayout(search_layout)
        layout.addWidget(search_group)

        # Vocabulary section
        vocab_group = QGroupBox("Suggested Vocabulary")
        vocab_layout = QVBoxLayout()

        cat_layout = QHBoxLayout()
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "greetings", "numbers", "colors", "days", "months", "food", "common",
        ])
        cat_layout.addWidget(QLabel("Category:"))
        cat_layout.addWidget(self.category_combo)

        self.load_vocab_btn = QPushButton("Load Vocabulary")
        self.load_vocab_btn.clicked.connect(self.load_vocabulary)
        cat_layout.addWidget(self.load_vocab_btn)

        self.batch_download_btn = QPushButton("Batch Download")
        self.batch_download_btn.clicked.connect(self.batch_download)
        cat_layout.addWidget(self.batch_download_btn)

        vocab_layout.addLayout(cat_layout)
        self.vocab_list = QListWidget()
        vocab_layout.addWidget(self.vocab_list)

        vocab_group.setLayout(vocab_layout)
        layout.addWidget(vocab_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    # ── actions ───────────────────────────────────────────────────────────

    def search_forvo(self):
        word = self.word_input.text().strip()
        language = self.lang_combo.currentText()
        if not word:
            QMessageBox.warning(self, "Input Required", "Please enter a word")
            return

        self.status_label.setText("Searching Forvo...")
        QApplication.processEvents()

        results = self.downloader.search_forvo(word, language, limit=10)
        if not results or "error" in results[0]:
            error_msg = results[0].get("error", "Unknown error") if results else "No results"
            self.status_label.setText(f"Error: {error_msg}")
            QMessageBox.information(self, "Search Results", error_msg)
            return

        self.populate_results(results)
        self.status_label.setText(f"Found {len(results)} pronunciations")

    def populate_results(self, results):
        self.results_table.setRowCount(len(results))
        for i, result in enumerate(results):
            self.results_table.setItem(i, 0, QTableWidgetItem(result["username"]))
            self.results_table.setItem(i, 1, QTableWidgetItem(result["country"]))
            self.results_table.setItem(i, 2, QTableWidgetItem(str(result["votes"])))

            preview_btn = QPushButton("Preview")
            preview_btn.setEnabled(False)
            self.results_table.setCellWidget(i, 3, preview_btn)

            download_btn = QPushButton("Download")
            download_btn.clicked.connect(
                lambda checked, r=result: self.download_pronunciation(r)
            )
            self.results_table.setCellWidget(i, 4, download_btn)

        self.results_table.resizeColumnsToContents()

    def download_pronunciation(self, result):
        word = self.word_input.text().strip()
        language = self.lang_combo.currentText()
        audio_url = result["audio_url"]

        username = result["username"].replace(" ", "_")
        filename = f"{word}_{language}_{username}.mp3"
        output_dir = os.path.join(config.SAMPLES_DIR, language)
        output_path = os.path.join(output_dir, filename)

        self.status_label.setText(f"Downloading {word}...")
        QApplication.processEvents()

        if self.downloader.download_audio(audio_url, output_path):
            try:
                audio, sr = self.audio.load_audio(output_path)
                duration = len(audio) / sr
                self.db.add_sample(
                    word=word, language=language, filepath=output_path,
                    source="forvo", speaker=result["username"],
                    duration=duration, sample_rate=sr,
                    metadata={"country": result["country"], "votes": result["votes"]},
                )
                self.status_label.setText(f"Downloaded and saved: {word}")
                QMessageBox.information(self, "Success",
                                        f"Downloaded pronunciation for '{word}'")
            except Exception as e:
                self.status_label.setText(f"Error processing audio: {e}")
                QMessageBox.warning(self, "Error", f"Failed to process audio: {e}")
        else:
            self.status_label.setText("Download failed")
            QMessageBox.warning(self, "Error", "Download failed")

    def load_vocabulary(self):
        category = self.category_combo.currentText()
        words = self.downloader.get_suggested_words(category)
        self.vocab_list.clear()
        for word in words:
            self.vocab_list.addItem(word)
        self.status_label.setText(f"Loaded {len(words)} words from '{category}' category")

    def batch_download(self):
        if self.vocab_list.count() == 0:
            QMessageBox.warning(self, "No Words", "Load vocabulary first")
            return

        language = self.lang_combo.currentText()
        words = [self.vocab_list.item(i).text() for i in range(self.vocab_list.count())]

        reply = QMessageBox.question(
            self, "Batch Download",
            f"Download {len(words)} pronunciations in {language}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(words))
        self.progress_bar.setValue(0)

        successful = 0
        for i, word in enumerate(words):
            self.status_label.setText(f"Downloading {word}... ({i + 1}/{len(words)})")
            QApplication.processEvents()

            filepath = self.downloader.download_forvo_pronunciation(
                word, language, config.SAMPLES_DIR,
            )
            if filepath:
                try:
                    audio, sr = self.audio.load_audio(filepath)
                    duration = len(audio) / sr
                    self.db.add_sample(
                        word=word, language=language, filepath=filepath,
                        source="forvo", duration=duration, sample_rate=sr,
                    )
                    successful += 1
                except Exception:
                    pass

            self.progress_bar.setValue(i + 1)
            time.sleep(1)  # Be polite to server

        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Downloaded {successful}/{len(words)} pronunciations")
        QMessageBox.information(
            self, "Batch Download Complete",
            f"Successfully downloaded {successful} out of {len(words)} words",
        )
