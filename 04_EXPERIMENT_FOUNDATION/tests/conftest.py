"""Pytest configuration and environment fixtures for Phase 04."""

import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
PHASE_ROOT = TESTS_DIR.parent
PROJECT_ROOT = PHASE_ROOT.parent
STARTER_KIT = PROJECT_ROOT / "starter_kit_pinned"

for p in [str(PHASE_ROOT), str(STARTER_KIT), str(PROJECT_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)
