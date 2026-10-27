#!/usr/bin/env python3
"""Thin CLI wrapper delegating directly to shared vendor/gems57/submission_writer.py (Protocol Rule 2)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))

from gems57.submission_writer import main, write_submission  # noqa: E402,F401

if __name__ == "__main__":
    raise SystemExit(main())
