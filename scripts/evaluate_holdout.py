#!/usr/bin/env python3
"""Thin CLI wrapper delegating directly to shared vendor/gems57/evaluate_holdout.py (Protocol Rule 2)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))

from gems57.evaluate_holdout import VERSION, evaluate, main, pooled_summary  # noqa: E402,F401

if __name__ == "__main__":
    raise SystemExit(main())
