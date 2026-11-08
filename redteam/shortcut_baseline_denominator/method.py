#!/usr/bin/env python3
"""shortcut_baseline_denominator: candidate entry point; visible-input builder only."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "support"))
from build_method import build

if __name__ == "__main__":
    build('shortcut_baseline_denominator')
