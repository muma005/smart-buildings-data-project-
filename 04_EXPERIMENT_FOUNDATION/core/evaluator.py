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

        # 3. Independent run integrity audit
        manifest_path = dir_path / "run_manifest.json"
        if manifest_path.is_file():
            integrity_res = ScoreVerifier.verify_run_integrity(
                run_dir=dir_path,
                expected_steps=expected_steps,
            )
            overall_valid = score_res.get("valid", False) and integrity_res.get("valid", False)
            try:
                from core.registry import ExperimentRegistry, EvidenceValidity
                registry = ExperimentRegistry()
                manifest = registry.load_manifest(dir_path)
                curr_validity = manifest.get("evidence_validity", EvidenceValidity.UNVERIFIED.value)
                if curr_validity == EvidenceValidity.UNVERIFIED.value:
                    new_val = EvidenceValidity.VALID if overall_valid else EvidenceValidity.INVALID
                    registry.update_evidence_validity(
                        run_dir=dir_path,
                        new_validity=new_val,
                        reason="Independent post-run verification audit",
                    )
                elif curr_validity == EvidenceValidity.VALID.value and not overall_valid:
                    registry.update_evidence_validity(
                        run_dir=dir_path,
                        new_validity=EvidenceValidity.INVALID,
                        reason="Failed independent post-run verification audit",
                    )
            except Exception:
                pass
        else:
            integrity_res = {"valid": score_res.get("valid", False), "note": "Legacy run without run_manifest.json"}
            overall_valid = score_res.get("valid", False)

        eval_result = {
            "run_dir": str(dir_path),
            "score_verification": score_res,
            "diagnostics": diagnostics,
            "run_integrity": integrity_res,
            "overall_valid": overall_valid,
            "evidence_validity": "VALID" if overall_valid else "INVALID",
        }

        # Write evaluation.json
        eval_path = dir_path / "evaluation.json"
        with open(eval_path, "w", encoding="utf-8") as f:
            json.dump(eval_result, f, indent=2)

        return eval_result
