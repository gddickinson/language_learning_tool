"""
Main GUI for the Language Learning Tool.
Tabbed interface with practice, library, download, and statistics views.
"""
import sys
import os
import time
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QComboBox,
                             QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem,
                             QTabWidget, QFileDialog, QMessageBox, QProgressBar,
                             QGroupBox, QListWidget, QSplitter, QSlider)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# Import our modules
import config
from audio_processor import AudioProcessor
from dtw_comparator import DTWComparator
from database_manager import DatabaseManager
from downloader import SampleDownloader


class WaveformCanvas(FigureCanvas):
    """Canvas for displaying waveforms and spectrograms."""
    
    def __init__(self, parent=None, dual_spec=False):
        self.dual_spec = dual_spec
        self.figure = Figure(figsize=(8, 6))
        super().__init__(self.figure)
        self.setParent(parent)
        
        # Create subplots
        if dual_spec:
            # For live comparison: wave + 2 spectrograms
            self.ax_wave = self.figure.add_subplot(311)
            self.ax_spec_ref = self.figure.add_subplot(312)
            self.ax_spec_user = self.figure.add_subplot(313)
        else:
            # Standard: wave + 1 spectrogram
            self.ax_wave = self.figure.add_subplot(211)
            self.ax_spec = self.figure.add_subplot(212)
        
        self.ax_wave.set_xlabel('Time (s)')
        self.ax_wave.set_ylabel('Amplitude')
        
        if dual_spec:
            self.ax_spec_ref.set_xlabel('Time (s)')
            self.ax_spec_ref.set_ylabel('Frequency (Hz)')
            self.ax_spec_user.set_xlabel('Time (s)')
            self.ax_spec_user.set_ylabel('Frequency (Hz)')
        else:
            self.ax_spec.set_xlabel('Time (s)')
            self.ax_spec.set_ylabel('Frequency (Hz)')
        
        self.figure.tight_layout()
        self.colorbar = None
        self.colorbar_ref = None
        self.colorbar_user = None
    
    def plot_audio(self, time, amplitude, frequencies, times, spectrogram,
                   title="Audio"):
        """Plot waveform and spectrogram."""
        # Clear previous plots
        self.ax_wave.clear()
        
        if self.dual_spec:
            self.ax_spec_ref.clear()
            self.ax_spec_user.clear()
        else:
            self.ax_spec.clear()
        
        # Plot waveform
        self.ax_wave.plot(time, amplitude, 'b-', linewidth=0.5)
        self.ax_wave.set_xlabel('Time (s)')
        self.ax_wave.set_ylabel('Amplitude')
        self.ax_wave.set_title(f'{title} - Waveform')
        self.ax_wave.grid(True, alpha=0.3)
        
        # Plot spectrogram
        ax_to_use = self.ax_spec if not self.dual_spec else self.ax_spec_ref
        
        # Limit frequency range for speech
        freq_mask = frequencies <= config.FREQ_MAX
        im = ax_to_use.pcolormesh(times, frequencies[freq_mask],
                                  spectrogram[freq_mask, :],
                                  shading='gouraud', cmap='viridis')
        ax_to_use.set_xlabel('Time (s)')
        ax_to_use.set_ylabel('Frequency (Hz)')
        ax_to_use.set_title(f'{title} - Spectrogram')
        ax_to_use.set_ylim([config.FREQ_MIN, config.FREQ_MAX])
        
        # Add colorbar
        if not self.dual_spec:
            if not hasattr(self, 'colorbar') or self.colorbar is None:
                self.colorbar = self.figure.colorbar(im, ax=ax_to_use, label='dB')
        
        self.figure.tight_layout()
        self.draw()
    
    def plot_dual_spectrograms(self, time, amp_ref, amp_user, 
                              freqs_ref, times_ref, spec_ref,
                              freqs_user, times_user, spec_user):
        """Plot overlaid waveform and dual spectrograms for comparison."""
        # Clear all
        self.ax_wave.clear()
        self.ax_spec_ref.clear()
        self.ax_spec_user.clear()
        
        # Plot overlaid waveforms
        self.ax_wave.plot(time, amp_ref, 'b-', alpha=0.7, 
                         label='Reference', linewidth=1.2)
        self.ax_wave.plot(time, amp_user, 'r-', alpha=0.7,
                         label='Your Voice (aligned)', linewidth=1.2)
        
        # Add difference highlighting
        diff = np.abs(amp_ref - amp_user)
        self.ax_wave.fill_between(time, -diff, diff,
                                 alpha=0.2, color='orange',
                                 label='Difference')
        
        self.ax_wave.set_xlabel('Time (s)')
        self.ax_wave.set_ylabel('Amplitude')
        self.ax_wave.set_title('DTW-Aligned Waveforms (Blue=Ref, Red=You, Orange=Diff)')
        self.ax_wave.legend(loc='upper right', fontsize=8)
        self.ax_wave.grid(True, alpha=0.3)
        self.ax_wave.set_ylim([-1.2, 1.2])
        
        # Plot reference spectrogram
        freq_mask_ref = freqs_ref <= config.FREQ_MAX
        im_ref = self.ax_spec_ref.pcolormesh(times_ref, freqs_ref[freq_mask_ref],
                                            spec_ref[freq_mask_ref, :],
                                            shading='gouraud', cmap='viridis')
        self.ax_spec_ref.set_ylabel('Frequency (Hz)')
        self.ax_spec_ref.set_title('Reference Spectrogram')
        self.ax_spec_ref.set_ylim([config.FREQ_MIN, config.FREQ_MAX])
        
        # Plot user spectrogram
        freq_mask_user = freqs_user <= config.FREQ_MAX
        im_user = self.ax_spec_user.pcolormesh(times_user, freqs_user[freq_mask_user],
                                              spec_user[freq_mask_user, :],
                                              shading='gouraud', cmap='viridis')
        self.ax_spec_user.set_xlabel('Time (s)')
        self.ax_spec_user.set_ylabel('Frequency (Hz)')
        self.ax_spec_user.set_title('Your Spectrogram (Time-Warped)')
        self.ax_spec_user.set_ylim([config.FREQ_MIN, config.FREQ_MAX])
        
        self.figure.tight_layout()
        self.draw()
    
    def clear_plot(self):
        """Clear all plots."""
        self.ax_wave.clear()
        
        if self.dual_spec:
            self.ax_spec_ref.clear()
            self.ax_spec_user.clear()
        else:
            self.ax_spec.clear()
            
        self.ax_wave.set_xlabel('Time (s)')
        self.ax_wave.set_ylabel('Amplitude')
        
        if self.dual_spec:
            self.ax_spec_ref.set_xlabel('Time (s)')
            self.ax_spec_ref.set_ylabel('Frequency (Hz)')
            self.ax_spec_user.set_xlabel('Time (s)')
            self.ax_spec_user.set_ylabel('Frequency (Hz)')
        else:
            self.ax_spec.set_xlabel('Time (s)')
            self.ax_spec.set_ylabel('Frequency (Hz)')
        
        self.draw()


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
        self.language_combo.addItems(['en', 'es', 'fr', 'de', 'it', 'pt', 'ja',
                                     'zh', 'ru', 'ar'])
        controls.addWidget(QLabel("Language:"))
        controls.addWidget(self.language_combo)
        
        self.load_reference_btn = QPushButton("Load Reference")
        self.load_reference_btn.clicked.connect(self.load_reference)
        controls.addWidget(self.load_reference_btn)
        
        layout.addLayout(controls)
        
        # Split view for reference and user audio
        splitter = QSplitter(Qt.Horizontal)
        
        # Reference audio panel
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
        
        # User audio panel
        user_panel = QGroupBox("Your Pronunciation (DTW-Aligned Comparison)")
        user_layout = QVBoxLayout()
        
        user_buttons = QHBoxLayout()
        self.record_btn = QPushButton("🔴 Record (3s)")
        self.record_btn.clicked.connect(self.record_audio)
        self.record_btn.setStyleSheet("font-size: 11pt; padding: 8px;")
        user_buttons.addWidget(self.record_btn)
        
        self.play_user_btn = QPushButton("▶ Play Recording")
        self.play_user_btn.clicked.connect(self.play_user)
        self.play_user_btn.setEnabled(False)
        user_buttons.addWidget(self.play_user_btn)
        
        self.compare_btn = QPushButton("⚖ Compare")
        self.compare_btn.clicked.connect(self.compare_pronunciations)
        self.compare_btn.setEnabled(False)
        self.compare_btn.setStyleSheet("font-size: 11pt; padding: 8px;")
        user_buttons.addWidget(self.compare_btn)
        
        user_layout.addLayout(user_buttons)
        
        # Use dual spectrogram canvas for aligned comparison
        self.user_canvas = WaveformCanvas(dual_spec=True)
        user_layout.addWidget(self.user_canvas)
        user_panel.setLayout(user_layout)
        splitter.addWidget(user_panel)
        
        layout.addWidget(splitter)
        
        # Feedback panel
        feedback_panel = QGroupBox("Pronunciation Feedback & Analysis")
        feedback_layout = QVBoxLayout()
        
        # Score and buttons row
        score_row = QHBoxLayout()
        
        self.score_label = QLabel("Similarity Score: --")
        self.score_label.setFont(QFont('Arial', 14, QFont.Bold))
        score_row.addWidget(self.score_label)
        
        score_row.addStretch()
        
        # Save comparison button
        save_btn = QPushButton("💾 Save Comparison")
        save_btn.clicked.connect(self.save_comparison)
        save_btn.setMaximumWidth(150)
        save_btn.setEnabled(True)
        score_row.addWidget(save_btn)
        
        # Help button
        help_btn = QPushButton("❓ Help")
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
    
    def load_reference(self):
        """Load reference pronunciation."""
        word = self.word_input.text().strip()
        language = self.language_combo.currentText()
        
        if not word:
            QMessageBox.warning(self, "Input Required",
                              "Please enter a word or phrase")
            return
        
        # Search database for reference
        samples = self.db.get_samples(word=word, language=language)
        
        if samples:
            # Use first sample
            sample = samples[0]
            filepath = sample['filepath']
            
            if os.path.exists(filepath):
                self.reference_audio, _ = self.audio.load_audio(filepath)
                self.current_reference_id = sample['id']
                self.display_reference()
                self.ref_play_btn.setEnabled(True)
                QMessageBox.information(self, "Success",
                                      f"Loaded reference for '{word}'")
            else:
                QMessageBox.warning(self, "File Not Found",
                                  f"Reference file not found: {filepath}")
        else:
            # No sample in database, ask to load from file
            filepath, _ = QFileDialog.getOpenFileName(
                self, "Select Reference Audio",
                config.SAMPLES_DIR,
                "Audio Files (*.wav *.mp3 *.ogg *.flac)"
            )
            
            if filepath:
                self.reference_audio, _ = self.audio.load_audio(filepath)
                self.current_reference_id = None
                self.display_reference()
                self.ref_play_btn.setEnabled(True)
    
    def display_reference(self):
        """Display reference audio waveform and spectrogram."""
        if self.reference_audio is not None:
            time, amp = self.audio.get_waveform(self.reference_audio)
            freqs, times, spec = self.audio.get_spectrogram(self.reference_audio)
            self.ref_canvas.plot_audio(time, amp, freqs, times, spec,
                                      "Reference")
    
    def play_reference(self):
        """Play reference audio."""
        if self.reference_audio is not None:
            self.audio.play(self.reference_audio)
    
    def record_audio(self):
        """Record user's pronunciation."""
        self.record_btn.setEnabled(False)
        self.record_btn.setText("Recording...")
        QApplication.processEvents()
        
        # Record for 3 seconds
        self.user_audio = self.audio.record(3.0)
        
        # Trim silence
        self.user_audio = self.audio.trim_silence(self.user_audio)
        
        # Normalize
        self.user_audio = self.audio.normalize_audio(self.user_audio)
        
        # Display
        self.display_user()
        
        self.record_btn.setEnabled(True)
        self.record_btn.setText("Record (3s)")
        self.play_user_btn.setEnabled(True)
        
        if self.reference_audio is not None:
            self.compare_btn.setEnabled(True)
    
    def display_user(self):
        """Display user audio waveform and spectrogram."""
        if self.user_audio is not None:
            time, amp = self.audio.get_waveform(self.user_audio)
            freqs, times, spec = self.audio.get_spectrogram(self.user_audio)
            self.user_canvas.plot_audio(time, amp, freqs, times, spec,
                                       "Your Recording")
    
    def play_user(self):
        """Play user's recording."""
        if self.user_audio is not None:
            self.audio.play(self.user_audio)
    
    def compare_pronunciations(self):
        """Compare user's pronunciation with reference using DTW alignment."""
        if self.reference_audio is None or self.user_audio is None:
            return
        
        # Perform DTW comparison
        results = self.dtw.compare_multiple_features(
            self.user_audio, self.reference_audio
        )
        
        # Get detailed analysis
        analysis = self.dtw.analyze_pronunciation_errors(
            self.user_audio, self.reference_audio
        )
        
        # Display score
        score = results['similarity_score']
        
        # Set color based on score
        if score >= 85:
            color = 'green'
        elif score >= 70:
            color = 'lightgreen'
        elif score >= 50:
            color = 'orange'
        else:
            color = 'red'
        
        # Display with DTW alignment visualization
        self.display_aligned_comparison(score, results, analysis)
        
        # Save to database
        word = self.word_input.text().strip()
        language = self.language_combo.currentText()
        
        if word:
            # Save user recording to database
            timestamp = int(time.time())
            filename = f"{word}_{language}_user_{timestamp}.wav"
            recordings_dir = os.path.join(config.SAMPLES_DIR, 'user_recordings')
            os.makedirs(recordings_dir, exist_ok=True)
            filepath = os.path.join(recordings_dir, filename)
            
            self.audio.save_audio(self.user_audio, filepath)
            
            # Add to database
            self.db.add_user_recording(
                word=word,
                language=language,
                filepath=filepath,
                reference_id=self.current_reference_id,
                similarity_score=score,
                feedback=analysis.get('feedback', '')
            )
    
    def display_aligned_comparison(self, score, results, analysis):
        """Display DTW-aligned comparison visualization."""
        # Normalize both for comparison
        ref_norm = self.audio.normalize_audio(self.reference_audio)
        user_norm = self.audio.normalize_audio(self.user_audio)
        
        # Get DTW alignment
        alignment_quality = "Good"
        try:
            _, dtw_path = self.dtw.compare_dtw(self.user_audio, self.reference_audio, 'mfcc')
            
            # Apply DTW time warping
            user_aligned = self.apply_dtw_warping(user_norm, ref_norm, dtw_path)
            
            # Calculate alignment quality
            path_smoothness = self.calculate_path_smoothness(dtw_path)
            if path_smoothness > 0.5:
                alignment_quality = "Excellent"
            elif path_smoothness > 0.3:
                alignment_quality = "Good"
            elif path_smoothness > 0.15:
                alignment_quality = "Fair"
            else:
                alignment_quality = "Poor"
                
        except Exception as e:
            print(f"DTW alignment error: {e}")
            alignment_quality = "Fallback"
            # Fallback to simple padding
            ref_len = len(ref_norm)
            if len(user_norm) < ref_len:
                user_aligned = np.pad(user_norm, (0, ref_len - len(user_norm)))
            else:
                user_aligned = user_norm[:ref_len]
        
        # Calculate correlation
        correlation = np.corrcoef(ref_norm, user_aligned)[0, 1]
        
        # Generate spectrograms
        freqs_ref, times_ref, spec_ref = self.audio.get_spectrogram(ref_norm)
        freqs_user, times_user, spec_user = self.audio.get_spectrogram(user_aligned)
        
        # Create time array
        time = np.arange(len(ref_norm)) / self.audio.sample_rate
        
        # Display dual spectrograms with alignment
        self.user_canvas.plot_dual_spectrograms(
            time, ref_norm, user_aligned,
            freqs_ref, times_ref, spec_ref,
            freqs_user, times_user, spec_user
        )
        
        # Update title with alignment info
        title_suffix = f" | Alignment: {alignment_quality} | Correlation: {correlation:.2f}"
        self.user_canvas.ax_wave.set_title(
            'DTW-Aligned Waveforms (Blue=Ref, Red=You, Orange=Diff)' + title_suffix
        )
        self.user_canvas.draw()
        
        # Display comprehensive feedback
        self.display_comprehensive_feedback(score, correlation, alignment_quality, results, analysis)
    
    def display_comprehensive_feedback(self, score, correlation, alignment_quality, results, analysis):
        """Display comprehensive feedback with all metrics."""
        duration_ratio = len(self.user_audio) / len(self.reference_audio)
        
        # Update score label with color
        if score >= 85:
            color = 'green'
        elif score >= 70:
            color = 'lightgreen'
        elif score >= 50:
            color = 'orange'
        else:
            color = 'red'
        
        self.score_label.setText(f"Similarity Score: {score:.1f}/100")
        self.score_label.setStyleSheet(f'color: {color}; font-weight: bold;')
        
        # Build comprehensive feedback
        feedback_parts = ["=== PRONUNCIATION ANALYSIS ===\n"]
        feedback_parts.append(f"Overall: {self.dtw.get_similarity_feedback(score)}\n")
        feedback_parts.append(f"\n📊 Detailed Metrics:")
        feedback_parts.append(f"\n  • Similarity Score: {score:.1f}/100")
        feedback_parts.append(f"\n  • Alignment Quality: {alignment_quality}")
        feedback_parts.append(f"\n  • Waveform Correlation: {correlation:.2f}")
        feedback_parts.append(f"\n  • Duration Ratio: {duration_ratio:.2f}x reference")
        
        if 'mfcc_similarity' in results:
            feedback_parts.append(f"\n  • Phonetic Match: {results['mfcc_similarity']:.1f}%")
        if 'chroma_similarity' in results:
            feedback_parts.append(f"\n  • Tonal Match: {results['chroma_similarity']:.1f}%")
        if 'spectral_similarity' in results:
            feedback_parts.append(f"\n  • Spectral Match: {results['spectral_similarity']:.1f}%")
        
        feedback_parts.append(f"\n\n🎯 Specific Feedback:")
        feedback_parts.append(f"\n  ⏱️  {analysis.get('speed_feedback', 'N/A')}")
        feedback_parts.append(f"\n  🎵  {analysis.get('pitch_feedback', 'N/A')}")
        feedback_parts.append(f"\n  🔊  {analysis.get('volume_feedback', 'N/A')}")
        
        # Recommendations
        feedback_parts.append(f"\n\n💡 Recommendations:")
        if score < 85:
            if alignment_quality == "Poor" or alignment_quality == "Fallback":
                feedback_parts.append(f"\n  ⚠️  Poor alignment - check recording quality")
            
            if duration_ratio > 1.2:
                feedback_parts.append(f"\n  • Speak slower to match reference rhythm")
            elif duration_ratio < 0.8:
                feedback_parts.append(f"\n  • Speak faster to match reference pace")
            
            if 'pitch' in analysis and 'differs' in analysis.get('pitch_feedback', '').lower():
                feedback_parts.append(f"\n  • Focus on matching pitch contour")
            
            if correlation < 0.6:
                feedback_parts.append(f"\n  • Low correlation - pronunciation very different")
                
            feedback_parts.append(f"\n  • Compare the spectrograms for frequency differences")
            feedback_parts.append(f"\n  • Orange shading shows pronunciation differences")
        else:
            feedback_parts.append(f"\n  ✅ Excellent work! Keep practicing to maintain this level.")
        
        self.feedback_text.setText(''.join(feedback_parts))
    
    def apply_dtw_warping(self, user_audio, ref_audio, dtw_path):
        """Apply DTW warping to align user audio to reference timeline using interpolation."""
        from scipy import interpolate
        
        ref_len = len(ref_audio)
        user_len = len(user_audio)
        
        # Convert DTW path to arrays
        dtw_path = np.array(dtw_path)
        user_indices = dtw_path[:, 0]
        ref_indices = dtw_path[:, 1]
        
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
        
        # Ensure we have start and end points
        if unique_ref_indices[0] != 0:
            unique_ref_indices = np.insert(unique_ref_indices, 0, 0)
            unique_user_indices = np.insert(unique_user_indices, 0, 0)
        
        if unique_ref_indices[-1] != ref_len - 1:
            unique_ref_indices = np.append(unique_ref_indices, ref_len - 1)
            unique_user_indices = np.append(unique_user_indices, 
                                           min(user_len - 1, unique_user_indices[-1] + 1))
        
        # Create interpolation function: ref_idx -> user_idx
        f = interpolate.interp1d(unique_ref_indices, unique_user_indices, 
                                kind='linear', bounds_error=False, 
                                fill_value='extrapolate')
        
        # For each reference sample position, find corresponding user position
        ref_positions = np.arange(ref_len)
        user_positions = f(ref_positions)
        
        # Clip to valid range
        user_positions = np.clip(user_positions, 0, user_len - 1)
        
        # Interpolate user audio at these positions
        user_sample_indices = np.arange(user_len)
        f_audio = interpolate.interp1d(user_sample_indices, user_audio,
                                      kind='cubic', bounds_error=False,
                                      fill_value=0.0)
        
        warped_audio = f_audio(user_positions)
        
        # Smooth any discontinuities
        warped_audio = self.smooth_warped_audio(warped_audio)
        
        return warped_audio
    
    def smooth_warped_audio(self, audio, window_size=5):
        """Apply light smoothing to warped audio to reduce artifacts."""
        from scipy.signal import savgol_filter
        
        if len(audio) < window_size:
            return audio
        
        if window_size % 2 == 0:
            window_size += 1
        
        try:
            smoothed = savgol_filter(audio, window_size, 2)
            return smoothed
        except:
            return np.convolve(audio, np.ones(window_size)/window_size, mode='same')
    
    def calculate_path_smoothness(self, dtw_path):
        """Calculate smoothness of DTW path as quality indicator."""
        if len(dtw_path) < 3:
            return 0.0
        
        dtw_path = np.array(dtw_path)
        
        # Calculate slopes between consecutive points
        slopes = []
        for i in range(len(dtw_path) - 1):
            dx = dtw_path[i+1][0] - dtw_path[i][0]
            dy = dtw_path[i+1][1] - dtw_path[i][1]
            if dx != 0:
                slopes.append(dy / dx)
        
        if not slopes:
            return 0.0
        
        slopes = np.array(slopes)
        slope_variance = np.var(slopes)
        smoothness = 1.0 / (1.0 + slope_variance)
        
        return smoothness
    
    def save_comparison(self):
        """Save current comparison visualization as image."""
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
            "PNG Images (*.png);;All Files (*)"
        )
        
        if filepath:
            try:
                self.user_canvas.figure.savefig(filepath, dpi=300, bbox_inches='tight')
                QMessageBox.information(self, "Saved", 
                                      f"Comparison saved to:\n{filepath}")
            except Exception as e:
                QMessageBox.warning(self, "Save Error", 
                                  f"Failed to save image: {e}")
    
    def show_alignment_help(self):
        """Show help dialog explaining DTW alignment."""
        help_text = """
<h3>Understanding DTW-Aligned Comparison</h3>

<p><b>What you're seeing in Your Pronunciation panel:</b></p>

<p><b>Top Panel:</b> Overlaid waveforms<br>
• <span style='color:blue;'><b>Blue line</b></span> = Reference pronunciation<br>
• <span style='color:red;'><b>Red line</b></span> = Your voice (time-warped to match)<br>
• <span style='color:orange;'><b>Orange shading</b></span> = Pronunciation differences</p>

<p><b>Middle Panel:</b> Reference spectrogram<br>
• Shows frequency content over time<br>
• Brighter regions = stronger frequencies</p>

<p><b>Bottom Panel:</b> Your spectrogram (aligned)<br>
• Time-warped to match reference<br>
• Compare patterns with reference above</p>

<p><b>Alignment Quality Levels:</b><br>
• <b>Excellent/Good</b> = Smooth alignment, reliable comparison<br>
• <b>Fair</b> = Some warping artifacts, still useful<br>
• <b>Poor</b> = Very different pronunciations or quality issues<br>
• <b>Fallback</b> = DTW failed, using simple alignment</p>

<p><b>Correlation Score:</b><br>
• 0.8-1.0 = Excellent waveform match<br>
• 0.6-0.8 = Good match<br>
• 0.4-0.6 = Fair match<br>
• Below 0.4 = Needs improvement</p>

<p><b>Tips:</b></p>
<p>1. Record in quiet environment for best alignment<br>
2. Speak clearly and completely<br>
3. Orange shading shows PRONUNCIATION differences, not timing<br>
4. Compare spectrograms to see frequency/pitch differences<br>
5. DTW automatically adjusts for speed differences</p>

<p>See ALIGNMENT_TROUBLESHOOTING.md for detailed help.</p>
"""
        
        msg = QMessageBox()
        msg.setWindowTitle("DTW Alignment Help")
        msg.setTextFormat(Qt.RichText)
        msg.setText(help_text)
        msg.setIcon(QMessageBox.Information)
        msg.exec_()


class LibraryTab(QWidget):
    """Tab for browsing pronunciation library."""
    
    def __init__(self, db_manager, audio_processor):
        super().__init__()
        self.db = db_manager
        self.audio = audio_processor
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Search controls
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
        
        # Samples table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            'Word', 'Language', 'Source', 'Speaker', 'Duration (s)', 'Actions'
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)
        
        # Add sample button
        add_btn = QPushButton("Add Sample from File")
        add_btn.clicked.connect(self.add_sample_from_file)
        layout.addWidget(add_btn)
        
        self.setLayout(layout)
        self.load_samples()
    
    def load_samples(self):
        """Load all samples from database."""
        samples = self.db.get_samples()
        self.populate_table(samples)
    
    def search_samples(self):
        """Search samples."""
        search_term = self.search_input.text()
        samples = self.db.search_samples(search_term)
        self.populate_table(samples)
    
    def populate_table(self, samples):
        """Populate table with samples."""
        self.table.setRowCount(len(samples))
        
        for i, sample in enumerate(samples):
            self.table.setItem(i, 0, QTableWidgetItem(sample['word']))
            self.table.setItem(i, 1, QTableWidgetItem(sample['language']))
            self.table.setItem(i, 2, QTableWidgetItem(sample['source']))
            self.table.setItem(i, 3, QTableWidgetItem(sample['speaker']))
            duration = f"{sample['duration']:.2f}" if sample['duration'] else "N/A"
            self.table.setItem(i, 4, QTableWidgetItem(duration))
            
            # Add play button
            play_btn = QPushButton("Play")
            play_btn.clicked.connect(
                lambda checked, fp=sample['filepath']: self.play_sample(fp)
            )
            self.table.setCellWidget(i, 5, play_btn)
        
        self.table.resizeColumnsToContents()
    
    def play_sample(self, filepath):
        """Play a sample."""
        if os.path.exists(filepath):
            audio, _ = self.audio.load_audio(filepath)
            self.audio.play(audio)
        else:
            QMessageBox.warning(self, "File Not Found",
                              f"Audio file not found: {filepath}")
    
    def add_sample_from_file(self):
        """Add a new sample from file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File",
            "",
            "Audio Files (*.wav *.mp3 *.ogg *.flac)"
        )
        
        if not filepath:
            return
        
        # Get metadata
        word, ok = QMessageBox.getText(self, "Word/Phrase",
                                       "Enter the word or phrase:")
        if not ok or not word:
            return
        
        language, ok = QMessageBox.getText(self, "Language",
                                          "Enter language code (e.g., en, es):",
                                          text="en")
        if not ok:
            return
        
        # Load audio to get duration
        audio, sr = self.audio.load_audio(filepath)
        duration = len(audio) / sr
        
        # Copy to samples directory
        filename = os.path.basename(filepath)
        new_path = os.path.join(config.SAMPLES_DIR, language, filename)
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        
        self.audio.save_audio(audio, new_path, sr)
        
        # Add to database
        self.db.add_sample(
            word=word,
            language=language,
            filepath=new_path,
            source='user',
            duration=duration,
            sample_rate=sr
        )
        
        self.load_samples()
        QMessageBox.information(self, "Success", f"Added sample for '{word}'")


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
        
        # Search inputs
        input_layout = QHBoxLayout()
        
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("Enter word or phrase...")
        input_layout.addWidget(QLabel("Word:"))
        input_layout.addWidget(self.word_input)
        
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(['en', 'es', 'fr', 'de', 'it', 'pt', 'ja',
                                  'zh', 'ru', 'ar', 'ko', 'hi', 'nl', 'sv'])
        input_layout.addWidget(QLabel("Language:"))
        input_layout.addWidget(self.lang_combo)
        
        self.search_btn = QPushButton("Search Forvo")
        self.search_btn.clicked.connect(self.search_forvo)
        input_layout.addWidget(self.search_btn)
        
        search_layout.addLayout(input_layout)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            'Username', 'Country', 'Votes', 'Preview', 'Download'
        ])
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        search_layout.addWidget(self.results_table)
        
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        # Suggested vocabulary section
        vocab_group = QGroupBox("Suggested Vocabulary")
        vocab_layout = QVBoxLayout()
        
        cat_layout = QHBoxLayout()
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            'greetings', 'numbers', 'colors', 'days', 'months', 'food', 'common'
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
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def search_forvo(self):
        """Search Forvo for pronunciations."""
        word = self.word_input.text().strip()
        language = self.lang_combo.currentText()
        
        if not word:
            QMessageBox.warning(self, "Input Required", "Please enter a word")
            return
        
        self.status_label.setText("Searching Forvo...")
        QApplication.processEvents()
        
        results = self.downloader.search_forvo(word, language, limit=10)
        
        if not results or 'error' in results[0]:
            error_msg = results[0].get('error', 'Unknown error') if results else 'No results'
            self.status_label.setText(f"Error: {error_msg}")
            QMessageBox.information(self, "Search Results", error_msg)
            return
        
        self.populate_results(results)
        self.status_label.setText(f"Found {len(results)} pronunciations")
    
    def populate_results(self, results):
        """Populate results table with search results."""
        self.results_table.setRowCount(len(results))
        
        for i, result in enumerate(results):
            self.results_table.setItem(i, 0, QTableWidgetItem(result['username']))
            self.results_table.setItem(i, 1, QTableWidgetItem(result['country']))
            self.results_table.setItem(i, 2, QTableWidgetItem(str(result['votes'])))
            
            # Preview button (would need audio URL)
            preview_btn = QPushButton("Preview")
            preview_btn.setEnabled(False)  # Enable when audio preview is implemented
            self.results_table.setCellWidget(i, 3, preview_btn)
            
            # Download button
            download_btn = QPushButton("Download")
            download_btn.clicked.connect(
                lambda checked, r=result: self.download_pronunciation(r)
            )
            self.results_table.setCellWidget(i, 4, download_btn)
        
        self.results_table.resizeColumnsToContents()
    
    def download_pronunciation(self, result):
        """Download a pronunciation from search results."""
        word = self.word_input.text().strip()
        language = self.lang_combo.currentText()
        audio_url = result['audio_url']
        
        # Create filename
        username = result['username'].replace(' ', '_')
        filename = f"{word}_{language}_{username}.mp3"
        output_dir = os.path.join(config.SAMPLES_DIR, language)
        output_path = os.path.join(output_dir, filename)
        
        # Download
        self.status_label.setText(f"Downloading {word}...")
        QApplication.processEvents()
        
        if self.downloader.download_audio(audio_url, output_path):
            # Add to database
            try:
                audio, sr = self.audio.load_audio(output_path)
                duration = len(audio) / sr
                
                self.db.add_sample(
                    word=word,
                    language=language,
                    filepath=output_path,
                    source='forvo',
                    speaker=result['username'],
                    duration=duration,
                    sample_rate=sr,
                    metadata={'country': result['country'], 'votes': result['votes']}
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
        """Load suggested vocabulary for selected category."""
        category = self.category_combo.currentText()
        words = self.downloader.get_suggested_words(category)
        
        self.vocab_list.clear()
        for word in words:
            self.vocab_list.addItem(word)
        
        self.status_label.setText(f"Loaded {len(words)} words from '{category}' category")
    
    def batch_download(self):
        """Download all words in vocabulary list."""
        if self.vocab_list.count() == 0:
            QMessageBox.warning(self, "No Words", "Load vocabulary first")
            return
        
        language = self.lang_combo.currentText()
        words = [self.vocab_list.item(i).text() for i in range(self.vocab_list.count())]
        
        reply = QMessageBox.question(
            self, "Batch Download",
            f"Download {len(words)} pronunciations in {language}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(words))
        self.progress_bar.setValue(0)
        
        successful = 0
        for i, word in enumerate(words):
            self.status_label.setText(f"Downloading {word}... ({i+1}/{len(words)})")
            QApplication.processEvents()
            
            filepath = self.downloader.download_forvo_pronunciation(
                word, language, config.SAMPLES_DIR
            )
            
            if filepath:
                try:
                    audio, sr = self.audio.load_audio(filepath)
                    duration = len(audio) / sr
                    
                    self.db.add_sample(
                        word=word,
                        language=language,
                        filepath=filepath,
                        source='forvo',
                        duration=duration,
                        sample_rate=sr
                    )
                    successful += 1
                except:
                    pass
            
            self.progress_bar.setValue(i + 1)
            import time
            time.sleep(1)  # Be polite to server
        
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Downloaded {successful}/{len(words)} pronunciations")
        QMessageBox.information(self, "Batch Download Complete",
                              f"Successfully downloaded {successful} out of {len(words)} words")


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
        
        # Recording controls
        control_group = QGroupBox("Record New Sample")
        control_layout = QVBoxLayout()
        
        # Metadata inputs
        meta_layout = QHBoxLayout()
        
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("Word or phrase...")
        meta_layout.addWidget(QLabel("Word:"))
        meta_layout.addWidget(self.word_input)
        
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(['en', 'es', 'fr', 'de', 'it', 'pt', 'ja',
                                  'zh', 'ru', 'ar'])
        meta_layout.addWidget(QLabel("Language:"))
        meta_layout.addWidget(self.lang_combo)
        
        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("e.g., greetings, numbers...")
        meta_layout.addWidget(QLabel("Category:"))
        meta_layout.addWidget(self.category_input)
        
        control_layout.addLayout(meta_layout)
        
        # Speaker info
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
        
        # Recording buttons
        button_layout = QHBoxLayout()
        
        self.duration_combo = QComboBox()
        self.duration_combo.addItems(['1 sec', '2 sec', '3 sec', '5 sec', '10 sec'])
        self.duration_combo.setCurrentText('3 sec')
        button_layout.addWidget(QLabel("Duration:"))
        button_layout.addWidget(self.duration_combo)
        
        self.record_btn = QPushButton("🔴 Record")
        self.record_btn.clicked.connect(self.record_sample)
        self.record_btn.setStyleSheet("font-size: 14pt; padding: 10px;")
        button_layout.addWidget(self.record_btn)
        
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.clicked.connect(self.play_recording)
        self.play_btn.setEnabled(False)
        button_layout.addWidget(self.play_btn)
        
        self.save_btn = QPushButton("💾 Save to Database")
        self.save_btn.clicked.connect(self.save_to_database)
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet("font-size: 14pt; padding: 10px;")
        button_layout.addWidget(self.save_btn)
        
        control_layout.addLayout(button_layout)
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # Waveform display
        self.canvas = WaveformCanvas()
        layout.addWidget(self.canvas)
        
        # Status
        self.status_label = QLabel("Ready to record")
        self.status_label.setFont(QFont('Arial', 12))
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def record_sample(self):
        """Record a new sample."""
        duration_text = self.duration_combo.currentText()
        duration = float(duration_text.split()[0])
        
        self.record_btn.setEnabled(False)
        self.status_label.setText(f"Recording {duration} seconds...")
        QApplication.processEvents()
        
        self.recorded_audio = self.audio.record(duration)
        self.recorded_audio = self.audio.trim_silence(self.recorded_audio)
        self.recorded_audio = self.audio.normalize_audio(self.recorded_audio)
        
        # Display waveform
        time, amp = self.audio.get_waveform(self.recorded_audio)
        freqs, times, spec = self.audio.get_spectrogram(self.recorded_audio)
        self.canvas.plot_audio(time, amp, freqs, times, spec, "Recorded Sample")
        
        self.record_btn.setEnabled(True)
        self.play_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.status_label.setText("Recording complete! Play to review, then save.")
    
    def play_recording(self):
        """Play the recorded sample."""
        if self.recorded_audio is not None:
            self.audio.play(self.recorded_audio)
    
    def save_to_database(self):
        """Save the recorded sample to database."""
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
        
        # Create filename
        speaker = self.speaker_input.text().strip() or "user"
        speaker_clean = speaker.replace(' ', '_')
        filename = f"{word}_{language}_{speaker_clean}_{int(time.time())}.wav"
        
        # Save audio file
        output_dir = os.path.join(config.SAMPLES_DIR, language)
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        
        self.audio.save_audio(self.recorded_audio, filepath)
        
        # Add to database
        duration = len(self.recorded_audio) / self.audio.sample_rate
        category = self.category_input.text().strip()
        notes = self.notes_input.text().strip()
        
        metadata = {}
        if notes:
            metadata['notes'] = notes
        
        sample_id = self.db.add_sample(
            word=word,
            language=language,
            filepath=filepath,
            source='user_recording',
            speaker=speaker,
            category=category,
            duration=duration,
            sample_rate=self.audio.sample_rate,
            metadata=metadata if metadata else None
        )
        
        self.status_label.setText(f"✓ Saved to database (ID: {sample_id})")
        QMessageBox.information(self, "Success", 
                              f"Sample saved for '{word}' in {language}")
        
        # Clear for next recording
        self.recorded_audio = None
        self.play_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.canvas.clear_plot()


class StatisticsTab(QWidget):
    """Tab showing practice statistics and progress."""
    
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh Statistics")
        refresh_btn.clicked.connect(self.load_statistics)
        layout.addWidget(refresh_btn)
        
        # Statistics display
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
            'Word', 'Language', 'Attempts', 'Best Score', 'Last Practiced'
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
        """Load and display statistics."""
        stats = self.db.get_statistics()
        
        # Display overview
        overview = f"""
Total Samples: {stats['total_samples']}
Total Practice Recordings: {stats['total_recordings']}
Languages: {', '.join(stats['languages']) if stats['languages'] else 'None'}
Categories: {', '.join(stats['categories']) if stats['categories'] else 'None'}
        """
        self.stats_text.setText(overview.strip())
        
        # Display practice history
        history = self.db.get_practice_history()
        self.history_table.setRowCount(len(history))
        
        for i, entry in enumerate(history):
            self.history_table.setItem(i, 0, QTableWidgetItem(entry['word']))
            self.history_table.setItem(i, 1, QTableWidgetItem(entry['language']))
            self.history_table.setItem(i, 2, QTableWidgetItem(str(entry['attempts'])))
            
            best_score = f"{entry['best_score']:.1f}" if entry['best_score'] else "N/A"
            self.history_table.setItem(i, 3, QTableWidgetItem(best_score))
            
            last_practiced = entry['last_practiced'][:10] if entry['last_practiced'] else "N/A"
            self.history_table.setItem(i, 4, QTableWidgetItem(last_practiced))
        
        self.history_table.resizeColumnsToContents()
        
        # Display most practiced
        self.most_list.clear()
        for entry in stats['most_practiced']:
            score_text = f" (Best: {entry['best_score']:.1f})" if entry['best_score'] else ""
            self.most_list.addItem(
                f"{entry['word']} - {entry['attempts']} attempts{score_text}"
            )


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
        
        # Timer for updating live display
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
        self.lang_combo.addItems(['en', 'es', 'fr', 'de', 'it', 'pt', 'ja'])
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
        
        # Live monitoring controls
        monitor_layout = QHBoxLayout()
        
        self.start_monitor_btn = QPushButton("▶ Start Live Monitoring")
        self.start_monitor_btn.clicked.connect(self.start_monitoring)
        self.start_monitor_btn.setEnabled(False)
        self.start_monitor_btn.setStyleSheet("font-size: 14pt; padding: 10px;")
        monitor_layout.addWidget(self.start_monitor_btn)
        
        self.stop_monitor_btn = QPushButton("⏹ Stop Monitoring")
        self.stop_monitor_btn.clicked.connect(self.stop_monitoring)
        self.stop_monitor_btn.setEnabled(False)
        self.stop_monitor_btn.setStyleSheet("font-size: 14pt; padding: 10px;")
        monitor_layout.addWidget(self.stop_monitor_btn)
        
        self.threshold_label = QLabel("Detection Threshold:")
        monitor_layout.addWidget(self.threshold_label)
        
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setMinimum(1)
        self.threshold_slider.setMaximum(100)
        self.threshold_slider.setValue(20)
        self.threshold_slider.setTickPosition(QSlider.TicksBelow)
        self.threshold_slider.setTickInterval(10)
        monitor_layout.addWidget(self.threshold_slider)
        
        layout.addLayout(monitor_layout)
        
        # Canvas for overlay visualization with dual spectrograms
        self.canvas = WaveformCanvas(dual_spec=True)
        layout.addWidget(self.canvas)
        
        # Feedback panel
        feedback_group = QGroupBox("Live Feedback & Alignment Info")
        feedback_layout = QVBoxLayout()
        
        # Similarity display
        similarity_layout = QHBoxLayout()
        self.similarity_label = QLabel("Similarity: --")
        self.similarity_label.setFont(QFont('Arial', 16, QFont.Bold))
        similarity_layout.addWidget(self.similarity_label)
        
        similarity_layout.addStretch()
        
        # Save comparison button
        save_btn = QPushButton("💾 Save Comparison")
        save_btn.setMaximumWidth(150)
        save_btn.clicked.connect(self.save_comparison)
        similarity_layout.addWidget(save_btn)
        
        # Help button
        help_btn = QPushButton("❓ Help")
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
        
        # Status
        self.status_label = QLabel("Load a reference to begin")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def load_reference(self):
        """Load reference audio."""
        word = self.word_input.text().strip()
        language = self.lang_combo.currentText()
        
        if not word:
            QMessageBox.warning(self, "Input Required", "Please enter a word")
            return
        
        samples = self.db.get_samples(word=word, language=language)
        
        if samples:
            filepath = samples[0]['filepath']
            if os.path.exists(filepath):
                self.reference_audio, _ = self.audio.load_audio(filepath)
                self.display_reference()
                self.play_ref_btn.setEnabled(True)
                self.start_monitor_btn.setEnabled(True)
                self.status_label.setText(f"Reference loaded for '{word}' - Ready to monitor")
            else:
                QMessageBox.warning(self, "File Not Found", f"File not found: {filepath}")
        else:
            filepath, _ = QFileDialog.getOpenFileName(
                self, "Select Reference Audio",
                config.SAMPLES_DIR,
                "Audio Files (*.wav *.mp3 *.ogg *.flac)"
            )
            
            if filepath:
                self.reference_audio, _ = self.audio.load_audio(filepath)
                self.display_reference()
                self.play_ref_btn.setEnabled(True)
                self.start_monitor_btn.setEnabled(True)
                self.status_label.setText("Reference loaded - Ready to monitor")
    
    def display_reference(self):
        """Display reference audio waveform and spectrogram."""
        if self.reference_audio is not None:
            time, amp = self.audio.get_waveform(self.reference_audio)
            freqs, times, spec = self.audio.get_spectrogram(self.reference_audio)
            
            # Clear all axes
            self.canvas.ax_wave.clear()
            self.canvas.ax_spec_ref.clear()
            self.canvas.ax_spec_user.clear()
            
            # Plot reference waveform
            self.canvas.ax_wave.plot(time, amp, 'b-', linewidth=1.0, label='Reference')
            self.canvas.ax_wave.set_xlabel('Time (s)')
            self.canvas.ax_wave.set_ylabel('Amplitude')
            self.canvas.ax_wave.set_title('Reference Waveform (Blue) - Start Monitoring to Compare')
            self.canvas.ax_wave.legend(loc='upper right')
            self.canvas.ax_wave.grid(True, alpha=0.3)
            
            # Plot reference spectrogram
            freq_mask = freqs <= config.FREQ_MAX
            self.canvas.ax_spec_ref.pcolormesh(times, freqs[freq_mask],
                                              spec[freq_mask, :],
                                              shading='gouraud', cmap='viridis')
            self.canvas.ax_spec_ref.set_ylabel('Frequency (Hz)')
            self.canvas.ax_spec_ref.set_title('Reference Spectrogram')
            self.canvas.ax_spec_ref.set_ylim([config.FREQ_MIN, config.FREQ_MAX])
            
            # Leave user spectrogram empty with message
            self.canvas.ax_spec_user.text(0.5, 0.5, 'Your spectrogram will appear here\nwhen you start monitoring',
                                         horizontalalignment='center',
                                         verticalalignment='center',
                                         transform=self.canvas.ax_spec_user.transAxes,
                                         fontsize=12, style='italic', color='gray')
            self.canvas.ax_spec_user.set_xlabel('Time (s)')
            self.canvas.ax_spec_user.set_ylabel('Frequency (Hz)')
            self.canvas.ax_spec_user.set_title('Your Spectrogram (Time-Warped)')
            
            self.canvas.figure.tight_layout()
            self.canvas.draw()
    
    def play_reference(self):
        """Play reference audio."""
        if self.reference_audio is not None:
            self.audio.play(self.reference_audio)
    
    def start_monitoring(self):
        """Start live microphone monitoring."""
        if self.reference_audio is None:
            return
        
        self.is_monitoring = True
        self.recorded_segments = []
        
        self.audio.start_recording()
        self.update_timer.start(100)  # Update every 100ms
        
        self.start_monitor_btn.setEnabled(False)
        self.stop_monitor_btn.setEnabled(True)
        self.status_label.setText("🔴 Monitoring... Speak the word!")
    
    def stop_monitoring(self):
        """Stop live monitoring."""
        self.is_monitoring = False
        self.update_timer.stop()
        
        user_audio = self.audio.stop_recording()
        
        self.start_monitor_btn.setEnabled(True)
        self.stop_monitor_btn.setEnabled(False)
        
        if len(user_audio) > 0:
            # Process final recording
            self.process_and_compare(user_audio)
        
        self.status_label.setText("Monitoring stopped")
    
    def update_live_display(self):
        """Update live display with current audio buffer."""
        if not self.is_monitoring or not self.audio.recording:
            return
        
        # Get current buffer
        current_audio = np.array(self.audio.recording)
        
        if len(current_audio) < 1000:
            return
        
        # Detect if speech started (simple energy threshold)
        threshold = self.threshold_slider.value() / 100.0
        energy = np.sqrt(np.mean(current_audio[-4410:]**2))  # Last 0.1 sec
        
        if energy > threshold:
            # Speech detected - extract and align
            self.detect_and_align(current_audio)
    
    def detect_and_align(self, audio_buffer):
        """Detect speech onset and align with reference using DTW."""
        # Find speech onset using energy threshold
        threshold = self.threshold_slider.value() / 100.0
        frame_size = 2205  # 50ms frames
        
        energy_profile = []
        for i in range(0, len(audio_buffer) - frame_size, frame_size):
            frame = audio_buffer[i:i+frame_size]
            energy = np.sqrt(np.mean(frame**2))
            energy_profile.append(energy)
        
        energy_profile = np.array(energy_profile)
        
        # Find first frame above threshold
        onset_frames = np.where(energy_profile > threshold)[0]
        
        if len(onset_frames) == 0:
            return
        
        onset_idx = onset_frames[0] * frame_size
        
        # Extract segment from onset with some pre-roll
        pre_roll = int(0.05 * self.audio.sample_rate)  # 50ms pre-roll
        start_idx = max(0, onset_idx - pre_roll)
        segment = audio_buffer[start_idx:]
        
        if len(segment) < len(self.reference_audio) * 0.3:
            return  # Too short to be meaningful
        
        # Normalize
        segment = self.audio.normalize_audio(segment)
        
        # Trim to reasonable length (allow up to 2x reference length)
        max_length = len(self.reference_audio) * 2
        if len(segment) > max_length:
            segment = segment[:max_length]
        
        # Perform DTW comparison with timing analysis
        try:
            results = self.dtw.compare_multiple_features(segment, self.reference_audio)
            analysis = self.dtw.analyze_pronunciation_errors(segment, self.reference_audio)
            
            # Update display
            score = results['similarity_score']
            self.similarity_label.setText(f"Similarity: {score:.1f}/100")
            
            # Color coding
            if score >= 85:
                color = 'green'
            elif score >= 70:
                color = 'lightgreen'
            elif score >= 50:
                color = 'orange'
            else:
                color = 'red'
            self.similarity_label.setStyleSheet(f'color: {color}; font-weight: bold;')
            
            # Enhanced feedback with timing analysis
            duration_ratio = len(segment) / len(self.reference_audio)
            timing_penalty = abs(1.0 - duration_ratio)
            
            feedback_parts = []
            
            # Main similarity feedback
            feedback_parts.append(self.dtw.get_similarity_feedback(score))
            
            # Timing-specific feedback
            if timing_penalty > 0.3:
                feedback_parts.append(f"\n⏱️ Timing: {analysis.get('speed_feedback', 'N/A')}")
                feedback_parts.append(f"   (Duration ratio: {duration_ratio:.2f}x reference)")
            
            # Pitch feedback
            if 'pitch_feedback' in analysis and 'differs' in analysis['pitch_feedback'].lower():
                feedback_parts.append(f"\n🎵 {analysis['pitch_feedback']}")
            
            # Volume feedback  
            if 'volume_feedback' in analysis and 'too' in analysis['volume_feedback'].lower():
                feedback_parts.append(f"\n🔊 {analysis['volume_feedback']}")
            
            feedback_text = ''.join(feedback_parts)
            self.feedback_text.setText(feedback_text)
            
            # Overlay visualization with DTW alignment
            self.overlay_visualization(segment)
            
        except Exception as e:
            # Silently handle errors during live processing
            print(f"Live comparison error: {e}")
            pass
    
    def overlay_visualization(self, user_segment):
        """Create overlay visualization of user vs reference with DTW alignment."""
        # Normalize both for consistent comparison
        ref_norm = self.audio.normalize_audio(self.reference_audio)
        user_norm = self.audio.normalize_audio(user_segment)
        
        # Use DTW to get optimal alignment path
        alignment_quality = "Good"
        try:
            dtw_distance, dtw_path = self.dtw.compare_dtw(user_segment, self.reference_audio, 'mfcc')
            
            # Apply DTW time warping to align user audio to reference
            user_aligned = self.apply_dtw_warping(user_norm, ref_norm, dtw_path)
            
            # Calculate alignment quality
            path_smoothness = self.calculate_path_smoothness(dtw_path)
            if path_smoothness > 0.5:
                alignment_quality = "Excellent"
            elif path_smoothness > 0.3:
                alignment_quality = "Good"
            elif path_smoothness > 0.15:
                alignment_quality = "Fair"
            else:
                alignment_quality = "Poor"
            
        except Exception as e:
            # Fallback to simple padding if DTW fails
            print(f"DTW alignment warning: {e}")
            alignment_quality = "Fallback"
            ref_len = len(ref_norm)
            if len(user_norm) < ref_len:
                user_aligned = np.pad(user_norm, (0, ref_len - len(user_norm)))
            else:
                user_aligned = user_norm[:ref_len]
        
        # Calculate similarity metrics
        correlation = np.corrcoef(ref_norm, user_aligned)[0, 1]
        rmse = np.sqrt(np.mean((ref_norm - user_aligned)**2))
        
        # Generate spectrograms for both
        freqs_ref, times_ref, spec_ref = self.audio.get_spectrogram(ref_norm)
        freqs_user, times_user, spec_user = self.audio.get_spectrogram(user_aligned)
        
        # Create time array for waveforms
        time = np.arange(len(ref_norm)) / self.audio.sample_rate
        
        # Use dual spectrogram display
        self.canvas.plot_dual_spectrograms(
            time, ref_norm, user_aligned,
            freqs_ref, times_ref, spec_ref,
            freqs_user, times_user, spec_user
        )
        
        # Add alignment quality indicator to waveform title
        title_suffix = f" | Alignment: {alignment_quality} | Correlation: {correlation:.2f}"
        current_title = self.canvas.ax_wave.get_title()
        if '|' in current_title:
            current_title = current_title.split('|')[0].strip()
        self.canvas.ax_wave.set_title(current_title + title_suffix)
        self.canvas.draw()
    
    def calculate_path_smoothness(self, dtw_path):
        """
        Calculate smoothness of DTW path as quality indicator.
        
        A smooth path indicates good alignment.
        A jagged path indicates poor alignment or very different pronunciations.
        
        Returns:
            Smoothness score (0-1, higher is better)
        """
        if len(dtw_path) < 3:
            return 0.0
        
        dtw_path = np.array(dtw_path)
        
        # Calculate slopes between consecutive points
        slopes = []
        for i in range(len(dtw_path) - 1):
            dx = dtw_path[i+1][0] - dtw_path[i][0]
            dy = dtw_path[i+1][1] - dtw_path[i][1]
            if dx != 0:
                slopes.append(dy / dx)
        
        if not slopes:
            return 0.0
        
        slopes = np.array(slopes)
        
        # Smooth path should have consistent slope (close to 1.0 for similar speeds)
        # Calculate variance of slopes
        slope_variance = np.var(slopes)
        
        # Lower variance = smoother = better
        # Convert to 0-1 score
        smoothness = 1.0 / (1.0 + slope_variance)
        
        return smoothness
    
    def apply_dtw_warping(self, user_audio, ref_audio, dtw_path):
        """
        Apply DTW warping to align user audio to reference timeline using interpolation.
        
        Args:
            user_audio: User's audio signal
            ref_audio: Reference audio signal  
            dtw_path: DTW alignment path from compare_dtw
            
        Returns:
            Time-warped user audio aligned to reference
        """
        from scipy import interpolate
        
        ref_len = len(ref_audio)
        user_len = len(user_audio)
        
        # Convert DTW path to arrays
        dtw_path = np.array(dtw_path)
        user_indices = dtw_path[:, 0]
        ref_indices = dtw_path[:, 1]
        
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
        
        # Ensure we have start and end points
        if unique_ref_indices[0] != 0:
            unique_ref_indices = np.insert(unique_ref_indices, 0, 0)
            unique_user_indices = np.insert(unique_user_indices, 0, 0)
        
        if unique_ref_indices[-1] != ref_len - 1:
            unique_ref_indices = np.append(unique_ref_indices, ref_len - 1)
            unique_user_indices = np.append(unique_user_indices, 
                                           min(user_len - 1, unique_user_indices[-1] + 1))
        
        # Create interpolation function: ref_idx -> user_idx
        # This tells us which user sample to use for each reference position
        f = interpolate.interp1d(unique_ref_indices, unique_user_indices, 
                                kind='linear', bounds_error=False, 
                                fill_value='extrapolate')
        
        # For each reference sample position, find corresponding user position
        ref_positions = np.arange(ref_len)
        user_positions = f(ref_positions)
        
        # Clip to valid range
        user_positions = np.clip(user_positions, 0, user_len - 1)
        
        # Interpolate user audio at these positions
        user_sample_indices = np.arange(user_len)
        f_audio = interpolate.interp1d(user_sample_indices, user_audio,
                                      kind='cubic', bounds_error=False,
                                      fill_value=0.0)
        
        warped_audio = f_audio(user_positions)
        
        # Smooth any discontinuities
        warped_audio = self.smooth_warped_audio(warped_audio)
        
        return warped_audio
    
    def smooth_warped_audio(self, audio, window_size=5):
        """
        Apply light smoothing to warped audio to reduce artifacts.
        
        Args:
            audio: Warped audio signal
            window_size: Smoothing window size (must be odd)
            
        Returns:
            Smoothed audio
        """
        from scipy.signal import savgol_filter
        
        # Only smooth if we have enough samples
        if len(audio) < window_size:
            return audio
        
        # Ensure window_size is odd
        if window_size % 2 == 0:
            window_size += 1
        
        try:
            # Savitzky-Golay filter for smooth interpolation
            smoothed = savgol_filter(audio, window_size, 2)
            return smoothed
        except:
            # Fallback to moving average if savgol fails
            return np.convolve(audio, np.ones(window_size)/window_size, mode='same')
    
    def interpolate_gaps(self, audio):
        """Fill zero gaps in warped audio with linear interpolation."""
        # Find non-zero regions
        nonzero_indices = np.where(audio != 0)[0]
        
        if len(nonzero_indices) == 0:
            return audio
        
        # Interpolate zeros between non-zero values
        result = audio.copy()
        
        for i in range(len(audio)):
            if audio[i] == 0:
                # Find nearest non-zero neighbors
                left_neighbors = nonzero_indices[nonzero_indices < i]
                right_neighbors = nonzero_indices[nonzero_indices > i]
                
                if len(left_neighbors) > 0 and len(right_neighbors) > 0:
                    # Interpolate between neighbors
                    left_idx = left_neighbors[-1]
                    right_idx = right_neighbors[0]
                    
                    # Linear interpolation
                    weight = (i - left_idx) / (right_idx - left_idx)
                    result[i] = (1 - weight) * audio[left_idx] + weight * audio[right_idx]
                    
                elif len(left_neighbors) > 0:
                    # Extend from left
                    result[i] = audio[left_neighbors[-1]]
                    
                elif len(right_neighbors) > 0:
                    # Extend from right
                    result[i] = audio[right_neighbors[0]]
        
        return result
    
    def show_alignment_help(self):
        """Show help dialog explaining DTW alignment."""
        help_text = """
<h3>Understanding DTW Alignment</h3>

<p><b>What you're seeing:</b></p>

<p><b>Top Panel:</b> Overlaid waveforms<br>
• <span style='color:blue;'><b>Blue line</b></span> = Reference pronunciation<br>
• <span style='color:red;'><b>Red line</b></span> = Your voice (time-warped to match)<br>
• <span style='color:orange;'><b>Orange shading</b></span> = Pronunciation differences</p>

<p><b>Middle Panel:</b> Reference spectrogram<br>
• Shows frequency content over time<br>
• Brighter regions = stronger frequencies</p>

<p><b>Bottom Panel:</b> Your spectrogram (aligned)<br>
• Time-warped to match reference<br>
• Compare patterns with reference above</p>

<p><b>Alignment Quality:</b><br>
• <b>Excellent/Good</b> = Smooth alignment, reliable comparison<br>
• <b>Fair</b> = Some warping artifacts, still useful<br>
• <b>Poor</b> = Very different pronunciations or noise issues<br>
• <b>Fallback</b> = DTW failed, using simple alignment</p>

<p><b>Tips for better alignment:</b></p>

<p>1. <b>Adjust Detection Threshold:</b><br>
   • Too many false triggers? → Raise slider<br>
   • Not detecting speech? → Lower slider<br>
   • Recommended: 20-40 for normal environments</p>

<p>2. <b>Recording Quality:</b><br>
   • Speak clearly in quiet environment<br>
   • Keep consistent distance from microphone<br>
   • Pronounce the complete word</p>

<p>3. <b>Interpreting Results:</b><br>
   • <b>Narrow orange</b> = Good pronunciation match<br>
   • <b>Wide orange</b> = Significant differences<br>
   • <b>Similar spectrograms</b> = Good frequency match<br>
   • <b>Different spectrograms</b> = Different pitch/resonance</p>

<p>4. <b>Correlation Score:</b><br>
   • Shows how well waveforms match after alignment<br>
   • 0.8-1.0 = Excellent correlation<br>
   • 0.6-0.8 = Good correlation<br>
   • Below 0.6 = Needs improvement</p>

<p><b>Remember:</b> The system automatically time-warps your audio to match 
the reference timeline, so differences you see are actual pronunciation 
differences, not just timing!</p>

<p>See ALIGNMENT_TROUBLESHOOTING.md for detailed help.</p>
"""
        
        msg = QMessageBox()
        msg.setWindowTitle("DTW Alignment Help")
        msg.setTextFormat(Qt.RichText)
        msg.setText(help_text)
        msg.setIcon(QMessageBox.Information)
        msg.exec_()
    
    def save_comparison(self):
        """Save current comparison visualization as image."""
        if self.reference_audio is None:
            QMessageBox.warning(self, "No Comparison", 
                              "No comparison to save. Start monitoring first.")
            return
        
        # Get word for filename
        word = self.word_input.text().strip() or "comparison"
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{word}_comparison_{timestamp}.png"
        
        # Save dialog
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Comparison Image",
            os.path.join(config.TEMP_DIR, filename),
            "PNG Images (*.png);;All Files (*)"
        )
        
        if filepath:
            try:
                # Save the matplotlib figure
                self.canvas.figure.savefig(filepath, dpi=300, bbox_inches='tight')
                self.status_label.setText(f"Comparison saved: {os.path.basename(filepath)}")
                QMessageBox.information(self, "Saved", 
                                      f"Comparison saved to:\n{filepath}")
            except Exception as e:
                QMessageBox.warning(self, "Save Error", 
                                  f"Failed to save image: {e}")
    
    def process_and_compare(self, user_audio):
        """Process complete recording and show final comparison."""
        if self.reference_audio is None or len(user_audio) == 0:
            return
        
        # Trim silence
        user_audio = self.audio.trim_silence(user_audio)
        user_audio = self.audio.normalize_audio(user_audio)
        
        if len(user_audio) < 0.1 * self.audio.sample_rate:
            self.status_label.setText("Recording too short - try again")
            return
        
        # Full comparison
        results = self.dtw.compare_multiple_features(user_audio, self.reference_audio)
        analysis = self.dtw.analyze_pronunciation_errors(user_audio, self.reference_audio)
        
        # Display results
        score = results['similarity_score']
        self.similarity_label.setText(f"Final Similarity: {score:.1f}/100")
        
        # Enhanced color coding
        if score >= 85:
            color = 'green'
        elif score >= 70:
            color = 'lightgreen'
        elif score >= 50:
            color = 'orange'
        else:
            color = 'red'
        self.similarity_label.setStyleSheet(f'color: {color}; font-weight: bold;')
        
        # Comprehensive feedback
        duration_ratio = len(user_audio) / len(self.reference_audio)
        
        feedback_parts = ["=== FINAL ANALYSIS ===\n"]
        feedback_parts.append(f"Overall: {self.dtw.get_similarity_feedback(score)}\n")
        feedback_parts.append(f"\n📊 Detailed Metrics:")
        feedback_parts.append(f"\n  • Similarity Score: {score:.1f}/100")
        feedback_parts.append(f"\n  • Duration Ratio: {duration_ratio:.2f}x reference")
        
        if 'mfcc_similarity' in results:
            feedback_parts.append(f"\n  • Phonetic Match: {results['mfcc_similarity']:.1f}%")
        if 'chroma_similarity' in results:
            feedback_parts.append(f"\n  • Tonal Match: {results['chroma_similarity']:.1f}%")
        
        feedback_parts.append(f"\n\n🎯 Specific Feedback:")
        feedback_parts.append(f"\n  ⏱️  {analysis.get('speed_feedback', 'N/A')}")
        feedback_parts.append(f"\n  🎵  {analysis.get('pitch_feedback', 'N/A')}")
        feedback_parts.append(f"\n  🔊  {analysis.get('volume_feedback', 'N/A')}")
        
        # Recommendations
        feedback_parts.append(f"\n\n💡 Recommendations:")
        if score < 85:
            if duration_ratio > 1.2:
                feedback_parts.append(f"\n  • Speak slower to match reference rhythm")
            elif duration_ratio < 0.8:
                feedback_parts.append(f"\n  • Speak faster to match reference pace")
            
            if 'pitch' in analysis and 'differs' in analysis.get('pitch_feedback', '').lower():
                feedback_parts.append(f"\n  • Focus on matching pitch contour")
            
            feedback_parts.append(f"\n  • Compare the spectrograms to see frequency differences")
            feedback_parts.append(f"\n  • Watch the orange shading for pronunciation issues")
        else:
            feedback_parts.append(f"\n  ✅ Excellent work! Keep practicing to maintain this level.")
        
        feedback_text = ''.join(feedback_parts)
        self.feedback_text.setText(feedback_text)
        
        # Show final comparison with alignment
        self.overlay_visualization(user_audio)
        
        self.status_label.setText(f"Final analysis complete - Score: {score:.1f}/100")


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        # Initialize components
        self.audio = AudioProcessor()
        self.dtw = DTWComparator()
        self.db = DatabaseManager()
        self.downloader = SampleDownloader()
        
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Language Learning Pronunciation Tool")
        self.setGeometry(100, 100, config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        
        # Create central widget and tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Create tab widget
        tabs = QTabWidget()
        
        # Add all tabs
        self.practice_tab = PracticeTab(self.audio, self.dtw, self.db)
        tabs.addTab(self.practice_tab, "📝 Practice")
        
        self.live_tab = LiveComparisonTab(self.audio, self.dtw, self.db)
        tabs.addTab(self.live_tab, "🎤 Live Comparison")
        
        self.recording_tab = RecordingTab(self.audio, self.db)
        tabs.addTab(self.recording_tab, "🔴 Record Samples")
        
        self.library_tab = LibraryTab(self.db, self.audio)
        tabs.addTab(self.library_tab, "📚 Library")
        
        self.download_tab = DownloadTab(self.downloader, self.db, self.audio)
        tabs.addTab(self.download_tab, "🌐 Download")
        
        self.stats_tab = StatisticsTab(self.db)
        tabs.addTab(self.stats_tab, "📊 Statistics")
        
        layout.addWidget(tabs)
        
        # Status bar
        self.statusBar().showMessage("Ready - Select a tab to begin")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
