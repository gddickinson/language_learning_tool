"""
Main GUI for the Language Learning Tool.
Thin assembler — each tab lives in its own module.
"""

import sys

import matplotlib
matplotlib.use("Qt5Agg")

from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget

import config
from audio_processor import AudioProcessor
from dtw_comparator import DTWComparator
from database_manager import DatabaseManager
from downloader import SampleDownloader

from practice_tab import PracticeTab
from live_comparison_tab import LiveComparisonTab
from recording_tab import RecordingTab
from library_tab import LibraryTab
from download_tab import DownloadTab
from stats_tab import StatisticsTab


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()

        # Initialize backend components
        self.audio = AudioProcessor()
        self.dtw = DTWComparator()
        self.db = DatabaseManager()
        self.downloader = SampleDownloader()

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Language Learning Pronunciation Tool")
        self.setGeometry(100, 100, config.WINDOW_WIDTH, config.WINDOW_HEIGHT)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        tabs = QTabWidget()

        self.practice_tab = PracticeTab(self.audio, self.dtw, self.db)
        tabs.addTab(self.practice_tab, "Practice")

        self.live_tab = LiveComparisonTab(self.audio, self.dtw, self.db)
        tabs.addTab(self.live_tab, "Live Comparison")

        self.recording_tab = RecordingTab(self.audio, self.db)
        tabs.addTab(self.recording_tab, "Record Samples")

        self.library_tab = LibraryTab(self.db, self.audio)
        tabs.addTab(self.library_tab, "Library")

        self.download_tab = DownloadTab(self.downloader, self.db, self.audio)
        tabs.addTab(self.download_tab, "Download")

        self.stats_tab = StatisticsTab(self.db)
        tabs.addTab(self.stats_tab, "Statistics")

        layout.addWidget(tabs)

        self.statusBar().showMessage("Ready - Select a tab to begin")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
