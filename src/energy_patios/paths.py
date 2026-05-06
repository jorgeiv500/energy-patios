"""Project paths."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
RESULTS = ROOT / "results"
MANUSCRIPT = ROOT / "manuscript"
