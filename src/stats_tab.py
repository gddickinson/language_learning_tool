"""
Statistics tab — practice history and progress overview.
"""

from PyQt5.QtWidgets import (
    QGroupBox, QLabel, QListWidget, QPushButton,
    QTableWidget, QTableWidgetItem, QTextEdit,
    QVBoxLayout, QWidget,
)


class StatisticsTab(QWidget):
    """Tab showing practice statistics and progress."""

    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        refresh_btn = QPushButton("Refresh Statistics")
        refresh_btn.clicked.connect(self.load_statistics)
        layout.addWidget(refresh_btn)

        # Overview
        stats_group = QGroupBox("Overview")
        stats_layout = QVBoxLayout()
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setMaximumHeight(150)
        stats_layout.addWidget(self.stats_text)
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # Practice history
        history_group = QGroupBox("Practice History")
        history_layout = QVBoxLayout()
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels([
            "Word", "Language", "Attempts", "Best Score", "Last Practiced",
        ])
        history_layout.addWidget(self.history_table)
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)

        # Most practiced
        most_group = QGroupBox("Most Practiced Words")
        most_layout = QVBoxLayout()
        self.most_list = QListWidget()
        most_layout.addWidget(self.most_list)
        most_group.setLayout(most_layout)
        layout.addWidget(most_group)

        self.setLayout(layout)
        self.load_statistics()

    def load_statistics(self):
        stats = self.db.get_statistics()

        overview = (
            f"Total Samples: {stats['total_samples']}\n"
            f"Total Practice Recordings: {stats['total_recordings']}\n"
            f"Languages: {', '.join(stats['languages']) if stats['languages'] else 'None'}\n"
            f"Categories: {', '.join(stats['categories']) if stats['categories'] else 'None'}"
        )
        self.stats_text.setText(overview)

        history = self.db.get_practice_history()
        self.history_table.setRowCount(len(history))
        for i, entry in enumerate(history):
            self.history_table.setItem(i, 0, QTableWidgetItem(entry["word"]))
            self.history_table.setItem(i, 1, QTableWidgetItem(entry["language"]))
            self.history_table.setItem(i, 2, QTableWidgetItem(str(entry["attempts"])))
            best_score = f"{entry['best_score']:.1f}" if entry["best_score"] else "N/A"
            self.history_table.setItem(i, 3, QTableWidgetItem(best_score))
            last = entry["last_practiced"][:10] if entry["last_practiced"] else "N/A"
            self.history_table.setItem(i, 4, QTableWidgetItem(last))
        self.history_table.resizeColumnsToContents()

        self.most_list.clear()
        for entry in stats["most_practiced"]:
            score_text = f" (Best: {entry['best_score']:.1f})" if entry["best_score"] else ""
            self.most_list.addItem(
                f"{entry['word']} - {entry['attempts']} attempts{score_text}"
            )
