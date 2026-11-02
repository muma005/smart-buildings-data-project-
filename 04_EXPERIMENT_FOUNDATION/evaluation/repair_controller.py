"""Controlled Repair Governance Engine (Stage 5 WP3).
Enforces strict prerequisites: No repair may be authorized without an established,
evidence-backed diagnosis (investigation record). Tracks minimal patches, pre-repair
reproduction proofs, and post-repair invariant contracts.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping


class RepairController:
    """Oversees controlled repair authorization, scoping, and verification records."""

    @classmethod
    def verify_repair_prerequisites(
        cls,
        investigation_record_path: Path | str,
    ) -> dict[str, Any]:
        """Validates that a formal diagnosis exists before authorizing a repair."""
        inv_path = Path(investigation_record_path)
        if not inv_path.is_file():
            raise FileNotFoundError(f"Investigation record not found: {inv_path}")

        with open(inv_path, "r", encoding="utf-8") as f:
            inv_data = json.load(f)

        status = inv_data.get("status")
        if status != "ROOT_CAUSE_CONFIRMED":
            raise ValueError(
                f"Repair authorization denied: Investigation '{inv_data.get('investigation_id')}' "
                f"has status '{status}', required 'ROOT_CAUSE_CONFIRMED'."
            )

        root_cause = inv_data.get("timeline_analysis", {}).get("confirmed_root_cause", {})
        if not root_cause or not root_cause.get("type"):
            raise ValueError("Repair authorization denied: No confirmed root cause type in investigation record.")

        return {
            "authorized": True,
            "investigation_id": inv_data.get("investigation_id"),
            "target_attack_id": inv_data.get("target_attack_id"),
            "confirmed_root_cause": root_cause,
        }

    @classmethod
    def create_repair_record(
        cls,
        repair_id: str,
        investigation_record_path: Path | str,
        authorized_by: str,
        affected_files: list[str],
        patch_description: str,
        pre_repair_reproduction: Mapping[str, Any],
        post_repair_invariants: Mapping[str, Any],
        output_path: Path | str | None = None,
    ) -> dict[str, Any]:
        """Generates a standardized Stage 5 machine-readable repair record."""
        prereq = cls.verify_repair_prerequisites(investigation_record_path)

        record = {
            "$schema": "https://smart-buildings.neurips/schemas/v1/repair_record.json",
            "schema_version": "v1.0",
            "repair_id": repair_id,
            "investigation_id": prereq["investigation_id"],
            "target_attack_id": prereq["target_attack_id"],
            "confirmed_root_cause": prereq["confirmed_root_cause"],
            "authorized_by": authorized_by,
            "affected_files": affected_files,
            "patch_description": patch_description,
            "pre_repair_reproduction": dict(pre_repair_reproduction),
            "post_repair_invariants": dict(post_repair_invariants),
            "governance_status": "REPAIR_IMPLEMENTED_PENDING_VERIFICATION",
        }

        if output_path:
            out_file = Path(output_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2)

        return record
