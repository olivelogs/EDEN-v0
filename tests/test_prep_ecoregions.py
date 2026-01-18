#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

# Ensure we can import from EDEN-v0/src without installing the package
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from eden.registry import prep_ecoregions as pe

def test_normalize_code_nums_and_strings():
    assert pe._normalize_code("07") == "7"
    assert pe._normalize_code(" 7 ") == "7"
    assert pe._normalize_code(7) == "7"

def test_normalize_code_emptyish_inputs():
    assert pe._normalize_code(None) == ""
    assert pe._normalize_code("") == ""
    assert pe._normalize_code(" ") == ""