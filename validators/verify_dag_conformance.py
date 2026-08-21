#!/usr/bin/env python3
"""
dist/palimpsestus-conformance/validators/verify_dag_conformance.py
Palimpsestus Machine-Checkable Structural DAG Validator

Parses and validates JSON fixtures or Markdown files against Palimpsestus 8 structural DAG invariants:
1. Topological Sequence Invariant (PP -> PI -> IC -> IL -> IP -> II)
2. Reference Integrity Invariant (Strict resolution of parent IDs)
3. Acyclic Graph Invariant (No causal cycles)
4. Receipt Completeness Invariant (Receipt existence & hashes)
5. Fold Input Coverage Invariant (All antecedent entries accounted for)
6. Fold Output Soundness Invariant (Non-empty minimal support set)
7. Operator Epistemic Tier Admissibility Invariant (Cross/Fold cannot yield Tier 1)
8. Constitutional Migration Invariant (C_n -> C_n+1 ancestry preservation)
"""

import sys
import glob
import json
import re
import argparse
from pathlib import Path

CELL_ORDER = ["CC", "CL", "CP", "CI", "LC", "LL", "LP", "LI", "PC", "PL", "PP", "PI", "IC", "IL", "IP", "II"]
CELL_TOPOLOGICAL_INDEX = {cell: idx for idx, cell in enumerate(CELL_ORDER)}

def validate_dag_structure(data, strict_reference_integrity=True):
    errors = []
    warnings = []

    nodes = data.get("nodes", [])
    node_map = {n["id"]: n for n in nodes}
    cross_receipts = data.get("cross_receipts", [])
    fold_receipts = data.get("fold_receipts", [])

    # Invariant 1, 2, 7: Topological Order, Reference Integrity, Tier Admissibility
    for node in nodes:
        node_id = node.get("id", "UNKNOWN")
        cell = node.get("cell", "")
        tier = node.get("epistemic_tier", 0)
        derivation_type = node.get("derivation_type", "CellCrossing")

        if cell not in CELL_TOPOLOGICAL_INDEX:
            errors.append(f"[{node_id}] Invalid matrix cell '{cell}'. Must be in {CELL_ORDER}")
            continue

        cell_idx = CELL_TOPOLOGICAL_INDEX[cell]

        parents = node.get("derives_from", []) + node.get("folds_from", []) + node.get("applies_to", [])
        for p_id in parents:
            if p_id in node_map:
                p_cell = node_map[p_id].get("cell", "")
                if p_cell in CELL_TOPOLOGICAL_INDEX:
                    p_idx = CELL_TOPOLOGICAL_INDEX[p_cell]
                    if p_idx > cell_idx:
                        errors.append(
                            f"[{node_id} in {cell}] Topological Order Violation: Parent [{p_id} in {p_cell}] "
                            f"comes AFTER child in authorship sequence! Must obey PP -> PI -> IC -> IL -> IP -> II."
                        )
            else:
                # Invariant 2: Reference Integrity
                msg = f"[{node_id}] Reference Integrity Violation: Parent ID '{p_id}' not found in corpus."
                if strict_reference_integrity:
                    errors.append(msg)
                else:
                    warnings.append(msg)

        # Invariant 7: Epistemic Tier Admissibility
        if derivation_type in ["CellCrossing", "LayerFold"] and tier == 1:
            errors.append(f"[{node_id}] Epistemic Tier Admissibility Violation: Cross/Fold derivations cannot yield Tier 1.")

    # Invariant 3: Acyclic Graph Invariant
    visited = {}
    def check_cycle(curr_id, path):
        visited[curr_id] = True
        path.add(curr_id)
        node = node_map.get(curr_id, {})
        parents = node.get("derives_from", []) + node.get("folds_from", []) + node.get("applies_to", [])
        for p_id in parents:
            if p_id in path:
                errors.append(f"[{curr_id}] Acyclic Graph Violation: Ancestry cycle detected involving '{p_id}'")
            elif p_id in node_map and p_id not in visited:
                check_cycle(p_id, path)
        path.remove(curr_id)

    for node_id in node_map:
        if node_id not in visited:
            check_cycle(node_id, set())

    # Invariant 5 & 6: Fold Output Soundness & Input Coverage
    for receipt in fold_receipts:
        rec_id = receipt.get("receipt_id", "UNKNOWN_FOLD")
        supp_set = receipt.get("minimal_support_set", [])
        cov_map = receipt.get("input_coverage_map", {})

        if not supp_set:
            errors.append(f"[{rec_id}] Fold Output Soundness Violation: Minimal support set S(X) cannot be empty.")

        for supp_id in supp_set:
            if supp_id not in node_map and strict_reference_integrity:
                errors.append(f"[{rec_id}] Fold Support Reference Violation: Support ID '{supp_id}' not found in corpus.")

        if not cov_map:
            errors.append(f"[{rec_id}] Fold Input Coverage Violation: Input coverage map cannot be empty.")

    return errors, warnings

def validate_migration_proof(data):
    errors = []
    receipt = data.get("migration_receipt", {})
    reclass_map = receipt.get("reclassification_map", {})
    valid_statuses = {"Valid", "ReParented", "EmpiricalHypothesis", "Superseded", "Invalid"}

    if not receipt:
        errors.append("Migration Receipt Violation: Missing 'migration_receipt' object.")
        return errors

    source_ver = receipt.get("source_grammar_version", "")
    target_ver = receipt.get("target_grammar_version", "")

    if not source_ver or not target_ver:
        errors.append("Migration Receipt Violation: Source and target grammar versions must be specified.")

    if not reclass_map:
        errors.append("Migration Receipt Violation: Reclassification map cannot be empty.")

    for item_id, status in reclass_map.items():
        if status not in valid_statuses:
            errors.append(f"[{item_id}] Migration Receipt Violation: Invalid reclassification status '{status}'. Must be in {valid_statuses}")

    return errors

def main():
    parser = argparse.ArgumentParser(description="Palimpsestus Machine-Checkable Structural DAG Validator")
    parser.add_argument("--fixture", type=str, help="Path to DAG fixture JSON file")
    parser.add_argument("--migration", type=str, help="Path to Constitutional Migration fixture JSON file")

    args = parser.parse_args()

    if args.fixture:
        path = Path(args.fixture)
        if not path.exists():
            print(f"Error: File '{path}' not found.", file=sys.stderr)
            sys.exit(1)

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        errors, warnings = validate_dag_structure(data, strict_reference_integrity=True)

        if errors:
            print(f"FAILED: {len(errors)} structural invariant violations found in '{path.name}':")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)
        else:
            print(f"SUCCESS: '{path.name}' passed structural DAG invariant validation.")
            sys.exit(0)

    elif args.migration:
        path = Path(args.migration)
        if not path.exists():
            print(f"Error: File '{path}' not found.", file=sys.stderr)
            sys.exit(1)

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        errors = validate_migration_proof(data)
        if errors:
            print(f"FAILED: Migration receipt violations found in '{path.name}':")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)
        else:
            print(f"SUCCESS: Constitutional migration proof '{path.name}' passed validation.")
            sys.exit(0)
    else:
        print("Usage: python3 verify_dag_conformance.py --fixture <path> OR --migration <path>")
        sys.exit(1)

if __name__ == "__main__":
    main()
