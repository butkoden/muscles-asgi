from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path


def test_di_profile_script_runs():
    script = Path(__file__).resolve().parents[2] / "benchmarks" / "profile_di_hotpath.py"
    cmd = [sys.executable, str(script)]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=True)
    result = ast.literal_eval(completed.stdout.strip())
    assert result["iterations"] == 10_000
    assert "inspect_signature_in_profile" in result
