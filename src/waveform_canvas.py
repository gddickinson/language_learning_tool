"""
Matplotlib canvas widget for displaying waveforms and spectrograms.
"""

import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import config


class WaveformCanvas(FigureCanvas):
    """Canvas for displaying waveforms and spectrograms."""

    def __init__(self, parent=None, dual_spec=False):
        self.dual_spec = dual_spec
        self.figure = Figure(figsize=(8, 6))
        super().__init__(self.figure)
        self.setParent(parent)

        # Create subplots
        if dual_spec:
            self.ax_wave = self.figure.add_subplot(311)
            self.ax_spec_ref = self.figure.add_subplot(312)
            self.ax_spec_user = self.figure.add_subplot(313)
        else:
            self.ax_wave = self.figure.add_subplot(211)
            self.ax_spec = self.figure.add_subplot(212)

        self.ax_wave.set_xlabel("Time (s)")
        self.ax_wave.set_ylabel("Amplitude")

        if dual_spec:
            self.ax_spec_ref.set_xlabel("Time (s)")
            self.ax_spec_ref.set_ylabel("Frequency (Hz)")
            self.ax_spec_user.set_xlabel("Time (s)")
            self.ax_spec_user.set_ylabel("Frequency (Hz)")
        else:
            self.ax_spec.set_xlabel("Time (s)")
            self.ax_spec.set_ylabel("Frequency (Hz)")

        self.figure.tight_layout()
        self.colorbar = None
        self.colorbar_ref = None
        self.colorbar_user = None

    def plot_audio(self, time, amplitude, frequencies, times, spectrogram,
                   title="Audio"):
        """Plot waveform and spectrogram."""
        self.ax_wave.clear()

        if self.dual_spec:
            self.ax_spec_ref.clear()
            self.ax_spec_user.clear()
        else:
            self.ax_spec.clear()

        # Plot waveform
        self.ax_wave.plot(time, amplitude, "b-", linewidth=0.5)
        self.ax_wave.set_xlabel("Time (s)")
        self.ax_wave.set_ylabel("Amplitude")
        self.ax_wave.set_title(f"{title} - Waveform")
        self.ax_wave.grid(True, alpha=0.3)

        # Plot spectrogram
        ax_to_use = self.ax_spec if not self.dual_spec else self.ax_spec_ref

        freq_mask = frequencies <= config.FREQ_MAX
        im = ax_to_use.pcolormesh(
            times, frequencies[freq_mask],
            spectrogram[freq_mask, :],
            shading="gouraud", cmap="viridis",
        )
        ax_to_use.set_xlabel("Time (s)")
        ax_to_use.set_ylabel("Frequency (Hz)")
        ax_to_use.set_title(f"{title} - Spectrogram")
        ax_to_use.set_ylim([config.FREQ_MIN, config.FREQ_MAX])

        if not self.dual_spec:
            if not hasattr(self, "colorbar") or self.colorbar is None:
                self.colorbar = self.figure.colorbar(im, ax=ax_to_use, label="dB")

        self.figure.tight_layout()
        self.draw()

    def plot_dual_spectrograms(self, time, amp_ref, amp_user,
                               freqs_ref, times_ref, spec_ref,
                               freqs_user, times_user, spec_user):
        """Plot overlaid waveform and dual spectrograms for comparison."""
        self.ax_wave.clear()
        self.ax_spec_ref.clear()
        self.ax_spec_user.clear()

        # Plot overlaid waveforms
        self.ax_wave.plot(time, amp_ref, "b-", alpha=0.7,
                          label="Reference", linewidth=1.2)
        self.ax_wave.plot(time, amp_user, "r-", alpha=0.7,
                          label="Your Voice (aligned)", linewidth=1.2)

        diff = np.abs(amp_ref - amp_user)
        self.ax_wave.fill_between(time, -diff, diff,
                                  alpha=0.2, color="orange",
                                  label="Difference")

        self.ax_wave.set_xlabel("Time (s)")
        self.ax_wave.set_ylabel("Amplitude")
        self.ax_wave.set_title(
            "DTW-Aligned Waveforms (Blue=Ref, Red=You, Orange=Diff)"
        )
        self.ax_wave.legend(loc="upper right", fontsize=8)
        self.ax_wave.grid(True, alpha=0.3)
        self.ax_wave.set_ylim([-1.2, 1.2])

        # Reference spectrogram
        freq_mask_ref = freqs_ref <= config.FREQ_MAX
        self.ax_spec_ref.pcolormesh(
            times_ref, freqs_ref[freq_mask_ref],
            spec_ref[freq_mask_ref, :],
            shading="gouraud", cmap="viridis",
        )
        self.ax_spec_ref.set_ylabel("Frequency (Hz)")
        self.ax_spec_ref.set_title("Reference Spectrogram")
        self.ax_spec_ref.set_ylim([config.FREQ_MIN, config.FREQ_MAX])

        # User spectrogram
        freq_mask_user = freqs_user <= config.FREQ_MAX
        self.ax_spec_user.pcolormesh(
            times_user, freqs_user[freq_mask_user],
            spec_user[freq_mask_user, :],
            shading="gouraud", cmap="viridis",
        )
        self.ax_spec_user.set_xlabel("Time (s)")
        self.ax_spec_user.set_ylabel("Frequency (Hz)")
        self.ax_spec_user.set_title("Your Spectrogram (Time-Warped)")
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

        self.ax_wave.set_xlabel("Time (s)")
        self.ax_wave.set_ylabel("Amplitude")

        if self.dual_spec:
            self.ax_spec_ref.set_xlabel("Time (s)")
            self.ax_spec_ref.set_ylabel("Frequency (Hz)")
            self.ax_spec_user.set_xlabel("Time (s)")
            self.ax_spec_user.set_ylabel("Frequency (Hz)")
        else:
            self.ax_spec.set_xlabel("Time (s)")
            self.ax_spec.set_ylabel("Frequency (Hz)")

        self.draw()
