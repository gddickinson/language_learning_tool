# Quick Start Guide

## Installation (5 minutes)

### Step 1: Install Python
Make sure you have Python 3.7 or higher installed:
```bash
python --version
```

### Step 2: Install Dependencies
```bash
cd language_learning_tool
pip install -r requirements.txt
```

### Step 3: Run the Application
```bash
python run.py
```

Or from the src directory:
```bash
cd src
python main_gui.py
```

## First Use (10 minutes)

### Getting Started with Practice

1. **Launch the application**
   - Run `python run.py` from the project directory
   - The GUI window will open with the Practice tab active

2. **Add a reference sample**
   - Method 1: Use an existing audio file
     - Click "Load Reference"
     - Browse to a .wav, .mp3, or .ogg file
     - Select the file
   
   - Method 2: Add from Library (after adding samples)
     - Enter a word in the "Word:" field
     - Click "Load Reference"
     - If found in database, it will load automatically

3. **Practice pronunciation**
   - Click "Play Reference" to hear the correct pronunciation
   - Click "Record (3s)" to record yourself
   - The waveform and spectrogram will display automatically
   - Click "Compare" to get your similarity score

4. **Review feedback**
   - Check your similarity score (0-100)
   - Read the detailed feedback
   - Note suggestions for speed, pitch, and volume

### Adding Samples to Library

1. **Go to Library Tab**
   - Click the "Library" tab at the top

2. **Add a sample**
   - Click "Add Sample from File"
   - Select an audio file (.wav, .mp3, .ogg, .flac)
   - Enter the word or phrase
   - Enter language code (e.g., "en" for English, "es" for Spanish)
   - Click OK

3. **Browse samples**
   - Use the search box to find specific words
   - Click "Play" to listen to any sample
   - Click "Refresh" to update the list

## Understanding the Interface

### Practice Tab

```
┌─────────────────────────────────────────────┐
│ Word: [hello    ] Language: [en ▼] [Load]  │
├──────────────────┬──────────────────────────┤
│ Reference        │ Your Pronunciation       │
│ [Play Reference] │ [Record] [Play] [Compare]│
│                  │                          │
│ ┌──────────────┐ │ ┌──────────────┐        │
│ │  Waveform    │ │ │  Waveform    │        │
│ │              │ │ │              │        │
│ └──────────────┘ │ └──────────────┘        │
│ ┌──────────────┐ │ ┌──────────────┐        │
│ │ Spectrogram  │ │ │ Spectrogram  │        │
│ │              │ │ │              │        │
│ └──────────────┘ │ └──────────────┘        │
├──────────────────┴──────────────────────────┤
│ Similarity Score: 85/100                    │
│ Feedback: Good! Your pronunciation is...    │
└─────────────────────────────────────────────┘
```

### Key Features

- **Waveform**: Shows amplitude over time (rhythm and timing)
- **Spectrogram**: Shows frequency content (pitch and intonation)
- **Similarity Score**: Overall pronunciation accuracy (0-100)
- **Feedback**: Specific suggestions for improvement

## Common Workflows

### Workflow 1: Practice a New Word

1. Find a reference audio file online or record a native speaker
2. Add to Library with word and language
3. Go to Practice tab
4. Enter word and load reference
5. Listen and practice multiple times
6. Compare and track improvement

### Workflow 2: Daily Practice Routine

1. Choose 5-10 words to practice
2. For each word:
   - Load reference
   - Record 3 attempts
   - Review feedback
   - Focus on areas needing improvement
3. Track progress over time

### Workflow 3: Focused Improvement

1. Identify weak areas from feedback (e.g., "speaking too fast")
2. Practice same word multiple times
3. Focus specifically on that aspect
4. Compare scores to see improvement

## Tips for Success

### Recording Tips

✅ **DO:**
- Use a quiet room
- Keep consistent distance from mic
- Speak clearly and naturally
- Record multiple attempts

❌ **DON'T:**
- Whisper or shout
- Record in noisy environments
- Rush through the word
- Give up after one attempt

### Interpretation Tips

**Similarity Scores:**
- 90-100: Excellent match
- 75-89: Good, minor differences
- 60-74: Fair, noticeable differences
- Below 60: Needs practice

**Focus on improvement, not perfection!**

### Effective Practice

1. **Listen first**: Always hear the reference before recording
2. **Multiple attempts**: Record 3-5 times per session
3. **Focus on feedback**: Address one issue at a time
4. **Regular practice**: 10-15 minutes daily is better than 1 hour weekly
5. **Track progress**: Review your history to see improvement

## Troubleshooting

### Can't record audio?
- Check microphone is connected
- Verify microphone permissions
- Test with another app first

### Low similarity scores?
- Check recording quality
- Ensure quiet environment
- Try different reference sample
- Practice pronunciation slowly first

### GUI won't start?
- Verify all dependencies installed
- Check Python version (3.7+)
- Try: `pip install --upgrade PyQt5`

### No sound on playback?
- Check system volume
- Verify audio output device
- Try different audio file format

## Next Steps

Once comfortable with basics:

1. **Explore different languages**: Add samples in multiple languages
2. **Build vocabulary sets**: Create categories (greetings, numbers, etc.)
3. **Track long-term progress**: Review practice history
4. **Download samples**: Use Forvo API for more references (requires API key)
5. **Advanced features**: Experiment with different comparison metrics

## Getting Help

- **Documentation**: See README.md for detailed information
- **Research**: See RESEARCH.md for background on methods
- **Tests**: Run tests to verify installation: `cd tests && python -m unittest discover`

## Sample Files for Testing

You can create test audio files using:
- Text-to-speech tools
- Recording yourself saying simple words
- Downloading from Forvo.com
- Using Google Translate's audio feature

Start with simple, clear words like:
- hello
- goodbye
- thank you
- yes
- no

## Progress Tracking

The tool automatically tracks:
- Number of practice attempts per word
- Best similarity score achieved
- Last practice date
- Overall improvement trends

Check the statistics to see your progress!

---

**Remember**: Learning pronunciation takes time and practice. Use this tool regularly, focus on specific improvements, and celebrate your progress! 🎉
