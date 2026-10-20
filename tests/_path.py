"""Puts the repository root on sys.path so the tests import the llm_assist package from the checkout."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
