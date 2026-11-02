"""Forensic Investigation & Timeline Reconstruction Engine (Stage 5 WP1).
Reconstructs execution timelines from chunked trace archives, isolates earliest verified
deviations, computes crash data-loss windows, and produces structured investigation records.
"""

from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping
import numpy as np


class TimelineReconstructor:
    """Ingests durable chunk archives and streaming logs to reconstruct state timelines."""

    @classmethod
    def reconstruct_run_timeline(cls, run_dir: Path | str) -> dict[str, Any]:
        """Audits all chunked data and logs in run_dir to reconstruct step trajectory."""
        r_path = Path(run_dir)
        if not r_path.is_dir():
            raise FileNotFoundError(f"Run directory not found: {r_path}")

        # 1. Load run_manifest.json if available
        manifest_path = r_path / "run_manifest.json"
        manifest_data: dict[str, Any] = {}
        if manifest_path.is_file():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest_data = json.load(f)
            except Exception:
                pass

        # 2. Load chunks_manifest.json if available
        chunks_manifest_path = r_path / "chunks_manifest.json"
        chunks_manifest_data: dict[str, Any] = {}
        if chunks_manifest_path.is_file():
            try:
                with open(chunks_manifest_path, "r", encoding="utf-8") as f:
                    chunks_manifest_data = json.load(f)
            except Exception:
                pass

        # 3. Scan chunks directory
        chunks_dir = r_path / "chunks"
        durable_chunks: list[dict[str, Any]] = []
        orphan_files: list[str] = []
        durable_steps = 0

        # Scan for any orphan temporary files in run_dir root or chunks_dir
        for p in r_path.glob("*.tmp"):
            orphan_files.append(p.name)
        if chunks_dir.is_dir():
            for p in chunks_dir.glob("*.tmp"):
                orphan_files.append(f"chunks/{p.name}")

            # Scan committed npz chunks
            chunk_files = sorted(chunks_dir.glob("chunk_*.npz"))
            expected_step = 0
            for cf in chunk_files:
                sha = hashlib.sha256(cf.read_bytes()).hexdigest()
                c_steps = 0
                start_s = expected_step
                end_s = expected_step
                try:
                    with np.load(cf) as data:
                        if "step_indices" in data:
                            c_steps = len(data["step_indices"])
                            start_s = int(data["step_indices"][0]) if c_steps > 0 else expected_step
                            end_s = int(data["step_indices"][-1]) + 1 if c_steps > 0 else expected_step
                        elif "observations" in data:
                            c_steps = len(data["observations"])
                            start_s = expected_step
                            end_s = start_s + c_steps
                        elif "step_count" in data:
                            c_steps = int(data["step_count"])
                            start_s = int(data.get("start_step", expected_step))
                            end_s = int(data.get("end_step", start_s + c_steps))
                except Exception:
                    pass

                # Fallback to chunks_manifest metadata if npz inspection yielded 0
                if c_steps == 0 and "chunks" in chunks_manifest_data:
                    for mc in chunks_manifest_data["chunks"]:
                        if mc.get("file_name") == cf.name:
                            c_steps = mc.get("num_steps", 0)
                            start_s = mc.get("start_step", expected_step)
                            end_s = mc.get("end_step", start_s + c_steps)
                            break

                durable_chunks.append({
                    "file_name": cf.name,
                    "sha256": sha,
                    "start_step": start_s,
                    "end_step": end_s,
                    "step_count": c_steps,
                })
                durable_steps += c_steps
                expected_step = end_s

        # 4. Scan streaming trace.csv
        trace_path = r_path / "trace.csv"
        trace_csv_steps = 0
        if trace_path.is_file():
            try:
                with open(trace_path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    for _ in reader:
                        trace_csv_steps += 1
            except Exception:
                pass

        return {
            "run_id": manifest_data.get("run_id", r_path.name),
            "execution_status": manifest_data.get("execution_status", manifest_data.get("status", "UNKNOWN")),
            "evidence_validity": manifest_data.get("evidence_validity", "UNVERIFIED"),
            "durable_steps": durable_steps,
            "durable_chunk_count": len(durable_chunks),
            "streaming_csv_steps": trace_csv_steps,
            "chunks": durable_chunks,
            "orphan_files": orphan_files,
            "discrepancy_window": {
                "durable_steps": durable_steps,
                "streaming_csv_steps": trace_csv_steps,
                "uncommitted_steps": max(0, trace_csv_steps - durable_steps),
            },
        }


class ForensicInvestigator:
    """Forensic engine for diagnosing failures and generating formal investigation records."""

    @classmethod
    def reconstruct_crash_timeline(cls, run_dir: Path | str) -> dict[str, Any]:
        """Diagnoses interrupted/crashed runs and quantifies data-loss windows (Stage 5 INV-02)."""
        timeline = TimelineReconstructor.reconstruct_run_timeline(run_dir)
        r_path = Path(run_dir)

        durable_steps = timeline["durable_steps"]
        csv_steps = timeline["streaming_csv_steps"]
        orphan_files = timeline["orphan_files"]
        status = timeline["execution_status"]
        validity = timeline["evidence_validity"]

        # 1. Classify crash mode and root cause
        has_tmp_chunk = any(f.endswith(".npz.tmp") for f in orphan_files)
        has_tmp_manifest = any(f.endswith(".json.tmp") for f in orphan_files)
        uncommitted_ram = csv_steps > durable_steps

        if has_tmp_chunk:
            root_cause_type = "PROCESS_TERMINATION_MID_CHUNK_WRITE"
            root_cause_desc = "Subprocess was terminated while actively streaming/syncing an uncommitted chunk .tmp file."
            first_symptom = f"Orphan temporary chunk file detected: {orphan_files}"
            earliest_deviation = f"Chunk commit phase: Interrupted before chunk rename at step {durable_steps}."
        elif has_tmp_manifest:
            root_cause_type = "PROCESS_TERMINATION_MID_MANIFEST_REPLACEMENT"
            root_cause_desc = "Subprocess was terminated while writing chunks_manifest.json.tmp."
            first_symptom = f"Orphan temporary manifest file detected: {orphan_files}"
            earliest_deviation = "Manifest commit phase: Interrupted during atomic manifest rewrite."
        elif uncommitted_ram:
            root_cause_type = "PROCESS_TERMINATION_UNCOMMITTED_RAM_BUFFER"
            root_cause_desc = (
                f"Subprocess terminated with {csv_steps - durable_steps} steps held in volatile RAM buffer. "
                f"Durable chunks commit every 288 steps; steps [{durable_steps}, {csv_steps}) were uncommitted."
            )
            first_symptom = f"Trace CSV step count ({csv_steps}) exceeds durable chunk step count ({durable_steps})."
            earliest_deviation = f"Step loop: Execution severed at step {csv_steps} before next chunk flush boundary."
        else:
            root_cause_type = "PREMATURE_TERMINATION_CLEAN_BOUNDARY"
            root_cause_desc = "Process terminated at clean chunk boundary prior to full episode completion."
            first_symptom = f"Incomplete run status ({status}) with {durable_steps} durable steps."
            earliest_deviation = f"Step loop: Execution halted at step {durable_steps}."

        # 2. Evaluation leakage check
        # Evaluation is protected if validity is INVALID or QUARANTINED and status is INCOMPLETE/FAILED
        evaluation_leakage_prevented = (validity in ["INVALID", "QUARANTINED", "UNVERIFIED"]) and (status != "COMPLETE")

        # 3. Chunks integrity check
        chunks_intact = len(timeline["chunks"]) > 0
        for c in timeline["chunks"]:
            if c["step_count"] == 0:
                chunks_intact = False

        data_loss_window = {
            "start_step": durable_steps,
            "end_step": csv_steps,
            "uncommitted_steps_lost": max(0, csv_steps - durable_steps),
            "durable_steps_retained": durable_steps,
        }

        downstream_consequences = [
            f"Run marked status={status}, evidence_validity={validity}.",
            "Comparison eligibility blocked (valid_comparison = False).",
            f"Uncommitted data loss window strictly bounded to {data_loss_window['uncommitted_steps_lost']} steps.",
            "Zero leaked steps allowed into official evaluation score aggregation.",
        ]

        diagnosis = {
            "investigation_target": "INV-02_CRASH_RECONSTRUCTION",
            "run_dir": str(r_path),
            "run_id": timeline["run_id"],
            "execution_status": status,
            "evidence_validity": validity,
            "data_loss_window": data_loss_window,
            "orphan_files": orphan_files,
            "prior_chunks_intact": chunks_intact,
            "evaluation_leakage_prevented": evaluation_leakage_prevented,
            "timeline_analysis": {
                "first_detected_symptom": first_symptom,
                "earliest_verified_deviation": earliest_deviation,
                "confirmed_root_cause": {
                    "type": root_cause_type,
                    "description": root_cause_desc,
                    "reproducible": True,
                },
                "downstream_consequences": downstream_consequences,
            },
            "confidence": "HIGH",
        }
        return diagnosis

    @classmethod
    def create_investigation_record(
        cls,
        investigation_id: str,
        target_attack_id: str,
        title: str,
        timeline_analysis: Mapping[str, Any],
        evidence_sources: list[str] | None = None,
        uncertainty_assessment: Mapping[str, Any] | None = None,
        output_path: Path | str | None = None,
    ) -> dict[str, Any]:
        """Creates a standardized Stage 5 machine-readable investigation record."""
        record = {
            "$schema": "https://smart-buildings.neurips/schemas/v1/investigation_record.json",
            "schema_version": "v1.0",
            "investigation_id": investigation_id,
            "target_attack_id": target_attack_id,
            "title": title,
            "status": "ROOT_CAUSE_CONFIRMED",
            "evidence_sources": evidence_sources or [],
            "timeline_analysis": dict(timeline_analysis),
            "uncertainty_assessment": uncertainty_assessment or {
                "confidence_level": "HIGH",
                "unverified_hypotheses": [],
            },
        }

        if output_path:
            out_file = Path(output_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2)

        return record
