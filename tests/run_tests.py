#!/usr/bin/env python3
"""Odyssey test runner — stdlib only, prints a METRIC line for the engine.

METRIC failing=N is the mission guard contract: 0 failing = healthy.
Exit code 1 on any failure so `bash -c` guards trip correctly.
"""

import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def main():
    loader = unittest.TestLoader()
    suite = loader.discover(str(HERE), top_level_dir=str(HERE))
    runner = unittest.TextTestRunner(verbosity=1, stream=sys.stderr)
    result = runner.run(suite)
    failing = len(result.failures) + len(result.errors)
    print(f"METRIC failing={failing}")
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
