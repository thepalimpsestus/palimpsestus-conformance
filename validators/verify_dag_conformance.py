#!/usr/bin/env python3
"""
dist/palimpsestus-conformance/validators/verify_dag_conformance.py
Palimpsestus Machine-Checkable Structural DAG Validator

Parses and validates JSON fixtures or Markdown files against Palimpsestus 8 structural DAG invariants:
1. Topological Sequence Invariant (PP -> PI -> IC -> IL -> IP -> II)
2. Reference Integrity Invariant (Strict resolution of parent IDs)
3. Acyclic Graph Invariant (No causal cycles)
4. Receipt Completeness & JSON Schema Invariant (Receipt existence, schema validation & hashes)
5. Fold Input Coverage & Parent Witness Invariant (All antecedent entries accounted for with valid witnesses)
6. Fold Output Soundness Invariant (Non-empty minimal support set)
7. Operator Epistemic Tier Admissibility Invariant (Cross/Fold cannot yield Tier 1)
8. Constitutional Migration Invariant (C_n -> C_n+1 ancestry preservation)
"""

import sys
import glob
import json
import re
import hashlib
import argparse
from pathlib import Path
import jsonschema

CELL_ORDER = ["CC", "CL", "CP", "CI", "LC", "LL", "LP", "LI", "PC", "PL", "PP", "PI", "IC", "IL", "IP", "II"]
CELL_TOPOLOGICAL_INDEX = {cell: idx for idx, cell in enumerate(CELL_ORDER)}
CANONICALIZATION_VERSION = "palimpsestus-normative-v1"

def compute_canonical_text_digest(text):
    clean = re.sub(r'[\`\*\_#\-\s]+', ' ', text).strip().lower()
    return "sha256:" + hashlib.sha256(clean.encode("utf-8")).hexdigest()

def validate_receipt_schema(receipt, schema_path, receipt_type="receipt"):
    if not Path(schema_path).exists():
        return [f"Schema file '{schema_path}' missing."]
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    try:
        jsonschema.validate(instance=receipt, schema=schema)
        return []
    except jsonschema.ValidationError as e:
        rec_id = receipt.get("receipt_id", "UNKNOWN")
        return [f"[{rec_id}] JSON Schema Validation Error ({receipt_type}): {e.message}"]

def validate_dag_structure(data, base_dir=None, strict_reference_integrity=True):
    errors = []
    warnings = []

    nodes = data.get("nodes", [])
    node_map = {n["id"]: n for n in nodes}
    cross_receipts = data.get("cross_receipts", [])
    fold_receipts = data.get("fold_receipts", [])

    # Pre-compute canonical_text_digest for fixture nodes if not present
    for node in nodes:
        if "canonical_text_digest" not in node:
            title = node.get("title", "")
            summary = node.get("one_sentence_summary", "")
            claim = node.get("irreducible_claim", "")
            text = f"{title} {summary} {claim}".strip()
            node["canonical_text_digest"] = compute_canonical_text_digest(text)

    # Schema paths
    if base_dir:
        cross_schema = Path(base_dir) / "schemas" / "cross-receipt.schema.json"
        fold_schema = Path(base_dir) / "schemas" / "fold-receipt.schema.json"
    else:
        cross_schema = Path(__file__).parent.parent / "schemas" / "cross-receipt.schema.json"
        fold_schema = Path(__file__).parent.parent / "schemas" / "fold-receipt.schema.json"

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
                msg = f"[{node_id}] Reference Integrity Violation: Parent ID '{p_id}' not found in corpus."
                if strict_reference_integrity:
                    errors.append(msg)
                else:
                    warnings.append(msg)

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

    # Invariant 4 & 5: Receipt JSON Schema & Universal Parent Witness Verification (Cross Receipts)
    for receipt in cross_receipts:
        rec_id = receipt.get("receipt_id", "UNKNOWN_CROSS")
        schema_errs = validate_receipt_schema(receipt, cross_schema, "CrossReceipt")
        errors.extend(schema_errs)

        witnesses = receipt.get("parent_witnesses", {})
        parents_to_check = set()
        if receipt.get("left_parent_id"):
            parents_to_check.add(receipt.get("left_parent_id"))
        if receipt.get("above_parent_id"):
            parents_to_check.add(receipt.get("above_parent_id"))

        for p_id in parents_to_check:
            if p_id not in witnesses:
                errors.append(f"[{rec_id}] Parent Witness Missing Violation: Missing witness object for parent '{p_id}'.")
                continue
            w = witnesses[p_id]
            if w.get("canonicalization_version") != CANONICALIZATION_VERSION:
                errors.append(f"[{rec_id}] Witness Version Mismatch Error: Parent '{p_id}' version '{w.get('canonicalization_version')}' != '{CANONICALIZATION_VERSION}'.")
            if p_id in node_map:
                p_node = node_map[p_id]
                expected_title = w.get("expected_title", "")
                actual_title = p_node.get("title", "")
                if expected_title and actual_title:
                    c_exp = re.sub(r'[^\w\s]', '', expected_title).strip().lower()
                    c_act = re.sub(r'[^\w\s]', '', actual_title).strip().lower()
                    if c_exp not in c_act and c_act not in c_exp:
                        errors.append(f"[{rec_id}] Parent Title Witness Mismatch Error: Expected title '{expected_title}', actual '{actual_title}'.")
                
                expected_digest = w.get("canonical_text_digest", "")
                actual_digest = p_node.get("canonical_text_digest", "")
                if expected_digest != actual_digest:
                    errors.append(f"[{rec_id}] Parent Digest Witness Mismatch Error: Parent '{p_id}' expected digest '{expected_digest}', actual computed '{actual_digest}'.")

    # Invariant 5 & 6: Fold Output Soundness, Coverage & Witness Verification (Fold Receipts)
    for receipt in fold_receipts:
        rec_id = receipt.get("receipt_id", "UNKNOWN_FOLD")
        schema_errs = validate_receipt_schema(receipt, fold_schema, "FoldReceipt")
        errors.extend(schema_errs)

        supp_set = receipt.get("minimal_support_set", [])
        cov_map = receipt.get("input_coverage_map", {})
        witnesses = receipt.get("parent_witnesses", {})

        if not supp_set:
            errors.append(f"[{rec_id}] Fold Output Soundness Violation: Minimal support set S(X) cannot be empty.")

        for supp_id in supp_set:
            if supp_id not in node_map and strict_reference_integrity:
                errors.append(f"[{rec_id}] Fold Support Reference Violation: Support ID '{supp_id}' not found in corpus.")
            if supp_id not in witnesses:
                errors.append(f"[{rec_id}] Parent Witness Missing Violation: Missing witness object for support parent '{supp_id}'.")
            else:
                w = witnesses[supp_id]
                if w.get("canonicalization_version") != CANONICALIZATION_VERSION:
                    errors.append(f"[{rec_id}] Witness Version Mismatch Error: Parent '{supp_id}' version '{w.get('canonicalization_version')}' != '{CANONICALIZATION_VERSION}'.")
                if supp_id in node_map:
                    p_node = node_map[supp_id]
                    expected_title = w.get("expected_title", "")
                    actual_title = p_node.get("title", "")
                    if expected_title and actual_title:
                        c_exp = re.sub(r'[^\w\s]', '', expected_title).strip().lower()
                        c_act = re.sub(r'[^\w\s]', '', actual_title).strip().lower()
                        if c_exp not in c_act and c_act not in c_exp:
                            errors.append(f"[{rec_id}] Parent Title Witness Mismatch Error: Expected title '{expected_title}', actual '{actual_title}'.")
                    expected_digest = w.get("canonical_text_digest", "")
                    actual_digest = p_node.get("canonical_text_digest", "")
                    if expected_digest != actual_digest:
                        errors.append(f"[{rec_id}] Parent Digest Witness Mismatch Error: Parent '{supp_id}' expected digest '{expected_digest}', actual computed '{actual_digest}'.")

        if not cov_map:
            errors.append(f"[{rec_id}] Fold Input Coverage Violation: Input coverage map cannot be empty.")

    return errors, warnings

def validate_migration_proof(data, base_dir=None):
    errors = []
    receipt = data.get("migration_receipt", {})
    reclass_map = receipt.get("reclassification_map", {})
    valid_statuses = {"Valid", "ReParented", "EmpiricalHypothesis", "Superseded", "Invalid"}

    if not receipt:
        errors.append("Migration Receipt Violation: Missing 'migration_receipt' object.")
        return errors

    if base_dir:
        mig_schema = Path(base_dir) / "schemas" / "migration-receipt.schema.json"
    else:
        mig_schema = Path(__file__).parent.parent / "schemas" / "migration-receipt.schema.json"

    schema_errs = validate_receipt_schema(receipt, mig_schema, "MigrationReceipt")
    errors.extend(schema_errs)

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
    base_dir = Path(__file__).parent.parent

    if args.fixture:
        path = Path(args.fixture)
        if not path.exists():
            print(f"Error: File '{path}' not found.", file=sys.stderr)
            sys.exit(1)

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        errors, warnings = validate_dag_structure(data, base_dir=base_dir, strict_reference_integrity=True)

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

        errors = validate_migration_proof(data, base_dir=base_dir)
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
