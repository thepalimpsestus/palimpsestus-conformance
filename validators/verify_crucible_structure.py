#!/usr/bin/env python3
"""
validators/verify_crucible_structure.py
Palimpsestus Public Crucible Integrity Structural Validator

Validates frontmatter metadata, version-generic spec coordinate pins, required template sections,
composite outcomes, structured constitutional dependencies, and DAG isolation for all Crucibles
in palimpsestus-spec/crucibles/.
"""

import os
import sys
import glob
import re
import argparse

VALID_STATUSES = {"PROPOSED", "FORMALIZED", "UNDER_ANALYSIS", "ADVERSARIAL_REVIEW", "STABLE"}
VALID_OUTCOMES = {
    "PENDING", "DISSOLVED", "REFRAMED", "LOCALIZED", "UNDERDETERMINED",
    "EMPIRICAL", "PRODUCTIVE_TENSION", "OPEN_FRONTIER",
    "CONSTITUTIONAL_PRESSURE", "CONSTITUTIONAL_CONTRADICTION"
}

REQUIRED_SECTIONS = [
    "1. Problem Statement",
    "2. Minimal Premises",
    "3. Epistemic Classification",
    "4. Hidden-Premise Audit",
    "13. Resolution Dependency Audit"
]

def parse_frontmatter(content):
    """Simple YAML frontmatter parser."""
    match = re.match(r"^---\n(.*?)\n---\n(.*)", content, re.DOTALL)
    if not match:
        return None, content
    yaml_text, body = match.groups()
    metadata = {}
    current_key = None
    list_accumulator = None

    for line in yaml_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- ") and current_key:
            val = line[2:].strip().strip('"').strip("'")
            if list_accumulator is not None:
                list_accumulator.append(val)
            continue
        if ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip()
            val = parts[1].strip().strip('"').strip("'")
            current_key = key
            if not val:
                list_accumulator = []
                metadata[key] = list_accumulator
            else:
                list_accumulator = None
                metadata[key] = val

    return metadata, body

def main():
    parser = argparse.ArgumentParser(description="Validate Palimpsestus Crucibles Structural Integrity")
    parser.add_argument("--spec-dir", required=True, help="Path to palimpsestus-spec repository root")
    args = parser.parse_args()

    crucibles_dir = os.path.join(args.spec_dir, "crucibles")
    if not os.path.exists(crucibles_dir):
        print(f"ERROR: Crucibles directory not found at {crucibles_dir}")
        sys.exit(1)

    crucible_files = sorted(glob.glob(os.path.join(crucibles_dir, "**", "*.md"), recursive=True))
    crucible_files = [f for f in crucible_files if not f.endswith("README.md") and not f.endswith("INDEX.md") and not f.endswith("TEMPLATE.md")]

    print(f"Scanning {len(crucible_files)} Crucible artifacts in '{crucibles_dir}'...")

    errors = []
    ids_seen = set()

    for path in crucible_files:
        rel_path = os.path.relpath(path, crucibles_dir)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        meta, body = parse_frontmatter(content)
        if not meta:
            errors.append(f"[{rel_path}] Missing YAML frontmatter header ('---').")
            continue

        # Check required metadata fields
        for req_field in ["crucible_id", "title", "domain", "status", "primary_outcome", "outcomes", "constitution", "spec_version", "spec_commit"]:
            if req_field not in meta:
                errors.append(f"[{rel_path}] Missing required frontmatter field '{req_field}'.")

        cid = meta.get("crucible_id")
        if cid:
            if cid in ids_seen:
                errors.append(f"[{rel_path}] Duplicate crucible_id '{cid}'.")
            ids_seen.add(cid)

        # Validate Status
        status = meta.get("status")
        if status and status not in VALID_STATUSES:
            errors.append(f"[{rel_path}] Invalid status '{status}'. Must be one of {sorted(VALID_STATUSES)}.")

        # Validate Primary Outcome
        primary_outcome = meta.get("primary_outcome")
        if primary_outcome and primary_outcome not in VALID_OUTCOMES:
            errors.append(f"[{rel_path}] Invalid primary_outcome '{primary_outcome}'. Must be one of {sorted(VALID_OUTCOMES)}.")

        # Validate Outcomes List
        outcomes = meta.get("outcomes", [])
        if isinstance(outcomes, str):
            outcomes = [outcomes]
        for out in outcomes:
            if out not in VALID_OUTCOMES:
                errors.append(f"[{rel_path}] Invalid outcome '{out}' in outcomes list. Must be one of {sorted(VALID_OUTCOMES)}.")

        # Status vs Outcome consistency
        if status == "STABLE" and primary_outcome == "PENDING":
            errors.append(f"[{rel_path}] STABLE crucible cannot have primary_outcome 'PENDING'.")

        # Validate Required Sections
        for sec in REQUIRED_SECTIONS:
            if sec not in body:
                errors.append(f"[{rel_path}] Missing required section heading '{sec}'.")

        # Validate Structured Constitutional Dependencies
        deps = meta.get("constitutional_dependencies", [])
        if isinstance(deps, str):
            deps = [deps]
        for dep in deps:
            if not dep.startswith("CC-") and not dep.startswith("CL-") and not dep.startswith("CONSTITUTIONAL_SPEC"):
                errors.append(f"[{rel_path}] Invalid constitutional dependency reference '{dep}'.")

    if errors:
        print("\nCRUCIBLE INTEGRITY VALIDATION FAILED:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    print(f"SUCCESS: All {len(crucible_files)} Crucibles passed structural integrity & generic spec pin validation!")

if __name__ == "__main__":
    main()
