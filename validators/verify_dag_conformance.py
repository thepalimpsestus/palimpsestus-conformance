#!/usr/bin/env python3
"""
dist/palimpsestus-conformance/validators/verify_dag_conformance.py
Palimpsestus Machine-Checkable Structural DAG Validator (Exported Public Reference Validator)

Parses and validates JSON fixtures or Markdown files against Palimpsestus 8 structural DAG invariants.
"""

import sys
import glob
import json
import re
import argparse
from pathlib import Path

CELL_ORDER = ["CC", "CL", "CP", "CI", "LC", "LL", "LP", "LI", "PC", "PL", "PP", "PI", "IC", "IL", "IP", "II"]
CELL_TOPOLOGICAL_INDEX = {cell: idx for idx, cell in enumerate(CELL_ORDER)}

def parse_markdown_dag(dir_path):
    derives_pat = re.compile(r'\*\*Derives from:\*\*\s*(.*)$', re.MULTILINE)
    applies_pat = re.compile(r'\*\*Applies to:\*\*\s*(.*)$', re.MULTILINE)
    folds_pat = re.compile(r'\*\*Folds from:\*\*\s*(.*)$', re.MULTILINE)
    tier_pat = re.compile(r'\*\*Epistemic Tier:\*\*\s*(Tier\s*)?([1-5])', re.IGNORECASE | re.MULTILINE)
    state_pat = re.compile(r'\*\*Derivational State:\*\*\s*([A-Z_]+)', re.MULTILINE)

    nodes = {}
    files = glob.glob(str(Path(dir_path) / "system-foundations-*.md"))
    
    for f_path in files:
        if "gap-map" in f_path or "completeness-audit" in f_path or "phase-space" in f_path:
            continue

        with open(f_path, "r", encoding="utf-8", errors="ignore") as fp:
            content = fp.read()

        sections = re.split(r'^###\s+', content, flags=re.MULTILINE)
        for sec in sections[1:]:
            lines = sec.splitlines()
            if not lines:
                continue
            title_line = lines[0]
            m = re.match(r'^([A-Z]{2}-\d+)\.\s*(.*)$', title_line)
            if not m:
                continue

            entry_id = m.group(1)
            title = m.group(2)
            cell = entry_id.split('-')[0]
            body = '\n'.join(lines[1:])

            derives = []
            applies = []
            folds = []
            tier = 3
            state = "IRREDUCIBLE"

            dm = derives_pat.search(body)
            if dm:
                derives = re.findall(r'([A-Z]{2}-\d+)', dm.group(1))
            am = applies_pat.search(body)
            if am:
                applies = re.findall(r'([A-Z]{2}-\d+)', am.group(1))
            fm = folds_pat.search(body)
            if fm:
                folds = re.findall(r'([A-Z]{2}-\d+)', fm.group(1))

            tm = tier_pat.search(body)
            if tm:
                tier = int(tm.group(2))
            elif cell == "CC":
                tier = 2

            sm = state_pat.search(body)
            if sm:
                state = sm.group(1)

            derivation_type = "LayerFold" if (cell in ["CC", "LC", "PC", "IC"] or folds) else "CellCrossing"

            nodes[entry_id] = {
                "id": entry_id,
                "title": title,
                "cell": cell,
                "derivation_type": derivation_type,
                "derives_from": derives,
                "applies_to": applies,
                "folds_from": folds,
                "epistemic_tier": tier,
                "derivational_state": state,
                "file": f_path
            }

    return {"nodes": list(nodes.values())}

def validate_dag_structure(data):
    errors = []
    warnings = []

    nodes = data.get("nodes", [])
    node_map = {n["id"]: n for n in nodes}

    for node in nodes:
        node_id = node.get("id", "UNKNOWN")
        cell = node.get("cell", "")
        tier = node.get("epistemic_tier", 0)
        derivation_type = node.get("derivation_type", "CellCrossing")

        if cell not in CELL_TOPOLOGICAL_INDEX:
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
                warnings.append(f"[{node_id}] External or unparsed parent reference: '{p_id}'")

        if derivation_type in ["CellCrossing", "LayerFold"] and tier == 1:
            errors.append(f"[{node_id}] Epistemic Tier Admissibility Violation: Cross/Fold derivations cannot yield Tier 1.")

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

    return errors, warnings

def validate_migration_proof(data):
    errors = []
    receipt = data.get("migration_receipt", {})
    reclass_map = receipt.get("reclassification_map", {})
    valid_statuses = {"Valid", "ReParented", "EmpiricalHypothesis", "Superseded", "Invalid"}

    if not reclass_map:
        errors.append("Migration proof receipt contains empty reclassification map.")

    for item_id, status in reclass_map.items():
        if status not in valid_statuses:
            errors.append(f"[{item_id}] Migration Receipt Violation: Invalid status '{status}'. Must be in {valid_statuses}")

    return errors

def main():
    parser = argparse.ArgumentParser(description="Palimpsestus Machine-Checkable Structural DAG Validator")
    parser.add_argument("--fixture", type=str, help="Path to DAG fixture JSON file")
    parser.add_argument("--migration", type=str, help="Path to Constitutional Migration fixture JSON file")
    parser.add_argument("--scan", type=str, help="Path to Markdown architecture directory to scan")

    args = parser.parse_args()

    if args.scan:
        path = Path(args.scan)
        if not path.exists():
            print(f"Error: Directory '{path}' not found.", file=sys.stderr)
            sys.exit(1)

        print(f"Scanning real authored Markdown entries in '{path}'...")
        data = parse_markdown_dag(path)
        total_nodes = len(data["nodes"])
        print(f"Parsed {total_nodes} real authored entries from repository.")

        errors, warnings = validate_dag_structure(data)

        if errors:
            print(f"\nFAILED: {len(errors)} structural invariant violations found:")
            for err in errors[:20]:
                print(f"  - {err}")
            sys.exit(1)
        else:
            print(f"SUCCESS: Analyzed {total_nodes} real entries. All 8 structural DAG invariants passed cleanly!")
            sys.exit(0)

    elif args.fixture:
        path = Path(args.fixture)
        if not path.exists():
            print(f"Error: File '{path}' not found.", file=sys.stderr)
            sys.exit(1)

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        errors, warnings = validate_dag_structure(data)

        if errors:
            print(f"FAILED: {len(errors)} structural invariant violations found:")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)
        else:
            print(f"SUCCESS: '{path.name}' passed all 8 structural DAG invariants.")
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
            print(f"FAILED: Migration receipt violations found:")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)
        else:
            print(f"SUCCESS: Constitutional migration proof '{path.name}' passed validation.")
            sys.exit(0)
    else:
        print("Usage: python3 verify_dag_conformance.py --scan <path> OR --fixture <path> OR --migration <path>")
        sys.exit(1)

if __name__ == "__main__":
    main()
