"""High-Level Evaluation Coordinator for Smart Buildings Challenge.
Coordinates independent score verification and engineering diagnostics for completed runs.
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any

PHASE_ROOT = Path(__file__).resolve().parents[1]
if str(PHASE_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE_ROOT))

from evaluation.score_verification import ScoreVerifier
from evaluation.diagnostics import DiagnosticsEngine


class RunEvaluator:
    """Evaluates a completed run directory and writes evaluation.json."""

    @classmethod
    def evaluate_run(
        cls,
        run_dir: Path | str,
        expected_steps: int = 8640,
        expected_return: float | None = None,
    ) -> dict[str, Any]:
        """Performs full evaluation of a run directory."""
        dir_path = Path(run_dir)
        trace_path = dir_path / "trace.csv"

        # 1. Score verification
        score_res = ScoreVerifier.verify_trace_and_score(
            trace_path=trace_path,
            expected_steps=expected_steps,
            expected_return=expected_return,
        )

        # 2. Engineering diagnostics
        diagnostics = DiagnosticsEngine.analyze_trace(trace_path=trace_path)

        eval_result = {
            "run_dir": str(dir_path),
            "score_verification": score_res,
            "diagnostics": diagnostics,
            "overall_valid": score_res.get("valid", False),
        }

        # Write evaluation.json
        eval_path = dir_path / "evaluation.json"
        with open(eval_path, "w", encoding="utf-8") as f:
            json.dump(eval_result, f, indent=2)

        return eval_result
