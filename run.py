#!/usr/bin/env python3
"""
Launcher script for Language Learning Pronunciation Tool.
"""
import sys
import os

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

try:
    from main_gui import main
    main()
except ImportError as e:
    print("Error: Missing dependencies!")
    print(f"Details: {e}")
    print("\nPlease install required packages:")
    print("  pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"Error starting application: {e}")
    sys.exit(1)
