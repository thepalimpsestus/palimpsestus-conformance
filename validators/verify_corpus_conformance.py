#!/usr/bin/env python3
"""
dist/palimpsestus-conformance/validators/verify_corpus_conformance.py
Live 3,269-Entry Public Corpus Topology & Ancestry Validator

Parses all 16 Markdown derivation matrix files directly from palimpsestus-spec,
extracts all authored entries, constructs the live derivation DAG, and validates
topological cell order, parent resolution, and acyclicity across the public corpus.
"""

import sys
import os
import glob
import re
import argparse
from pathlib import Path

CELL_ORDER = ["CC", "CL", "CP", "CI", "LC", "LL", "LP", "LI", "PC", "PL", "PP", "PI", "IC", "IL", "IP", "II"]
CELL_TOPOLOGICAL_INDEX = {cell: idx for idx, cell in enumerate(CELL_ORDER)}

def parse_markdown_corpus(spec_dir):
    pattern = os.path.join(spec_dir, "system-foundations-*.md")
    files = glob.glob(pattern)
    
    if not files:
        print(f"Error: No system-foundations-*.md files found in '{spec_dir}'", file=sys.stderr)
        return {}, []
        
    nodes = {}
    header_pattern = re.compile(r'^###\s+([A-Z]{2}-\d+)[\.:\s]\s*(.*)$', re.MULTILINE)
    
    for filepath in files:
        cell_match = re.search(r'system-foundations-([a-z]+)-([a-z]+)\.md$', filepath)
        if not cell_match:
            continue
        c1, c2 = cell_match.group(1)[0].upper(), cell_match.group(2)[0].upper()
        cell_code = f"{c1}{c2}"
        
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        matches = list(header_pattern.finditer(content))
        for i, match in enumerate(matches):
            entry_id = match.group(1)
            title = match.group(2).strip()
            
            start_pos = match.end()
            end_pos = matches[i+1].start() if i + 1 < len(matches) else len(content)
            entry_body = content[start_pos:end_pos]
            
            parents = []
            parent_refs = []
            derivation_type = "CellCrossing"
            if cell_code in ["CC", "LC", "PC", "IC"]:
                derivation_type = "LayerFold" if cell_code != "CC" else "AntecedentRoot"
                
            for line in entry_body.splitlines():
                ref_class = "IllustrativeMention"
                if any(kw in line for kw in ["Derives From:", "Folds From:"]):
                    ref_class = "NormativeAncestry"
                elif any(kw in line for kw in ["Applies To:", "Parents:", "Derived From:"]):
                    ref_class = "NormativeSupport"
                elif "Corollary" in line or "See:" in line:
                    ref_class = "CorollaryCrossReference"

                if ref_class != "IllustrativeMention" or any(kw in line for kw in ["Derives From:", "Folds From:", "Applies To:", "Parents:", "Derived From:"]):
                    found = re.findall(r'\b([A-Z]{2}-\d+)(?:\s*\((.*?)\))?', line)
                    for fid, exp_title in found:
                        if fid != entry_id:
                            if fid not in parents:
                                parents.append(fid)
                            parent_refs.append({
                                "id": fid,
                                "class": ref_class,
                                "expected_title": exp_title.strip() if exp_title else None
                            })
                    
            nodes[entry_id] = {
                "id": entry_id,
                "title": title,
                "cell": cell_code,
                "derivation_type": derivation_type,
                "parents": parents,
                "parent_refs": parent_refs,
                "body": entry_body,
                "epistemic_tier": 2 if derivation_type in ["AntecedentRoot", "LayerFold"] else 3
            }
                
    return nodes, files

import hashlib

def compute_semantic_digest(text):
    """Computes canonicalized sha256 semantic digest of normative text, stripping formatting."""
    clean = re.sub(r'[\`\*\_#\-\s]+', ' ', text).strip().lower()
    return "sha256:" + hashlib.sha256(clean.encode("utf-8")).hexdigest()

def validate_live_corpus(nodes):
    errors = []
    warnings = []
    
    # 1. Structural Order & Reference Binding Integrity
    for node_id, node in nodes.items():
        cell = node["cell"]
        if cell not in CELL_TOPOLOGICAL_INDEX:
            errors.append(f"[{node_id}] Invalid matrix cell '{cell}'")
            continue
            
        c_idx = CELL_TOPOLOGICAL_INDEX[cell]
        node["semantic_digest"] = compute_semantic_digest(node["title"] + " " + node.get("body", ""))

        for ref in node.get("parent_refs", []):
            p_id = ref["id"]
            ref_class = ref["class"]
            expected_title = ref.get("expected_title")

            if p_id in nodes:
                p_node = nodes[p_id]
                p_cell = p_node["cell"]
                if p_cell in CELL_TOPOLOGICAL_INDEX:
                    p_idx = CELL_TOPOLOGICAL_INDEX[p_cell]
                    if p_idx > c_idx:
                        errors.append(
                            f"[{node_id} in {cell}] Topological Order Violation: Parent [{p_id} in {p_cell}] "
                            f"comes AFTER child in authorship sequence!"
                        )
                # Reference Binding Integrity: Verify title match if explicit title was cited in parent reference
                if expected_title and p_node["title"]:
                    clean_expected = re.sub(r'[^\w\s]', '', expected_title).strip().lower()
                    clean_actual = re.sub(r'[^\w\s]', '', p_node["title"]).strip().lower()
                    if clean_expected not in clean_actual and clean_actual not in clean_expected:
                        errors.append(
                            f"[{node_id}] Reference Binding Integrity Error: Cited parent '{p_id}' with expected title "
                            f"'{expected_title}', but target '{p_id}' actual title is '{p_node['title']}'."
                        )
            else:
                # Reference Integrity based on reference class
                if ref_class in ["NormativeAncestry", "NormativeSupport"]:
                    warnings.append(f"[{node_id}] Unresolved {ref_class} parent reference '{p_id}' in corpus.")
                else:
                    warnings.append(f"[{node_id}] Unresolved {ref_class} cross-reference '{p_id}' in corpus.")
                
    # 2. Acyclic Graph Check
    visited = {}
    def check_cycle(curr_id, path):
        visited[curr_id] = True
        path.add(curr_id)
        node = nodes.get(curr_id, {})
        for p_id in node.get("parents", []):
            if p_id in path:
                errors.append(f"[{curr_id}] Acyclic Graph Violation: Ancestry cycle detected involving '{p_id}'")
            elif p_id in nodes and p_id not in visited:
                check_cycle(p_id, path)
        path.remove(curr_id)

    for node_id in nodes:
        if node_id not in visited:
            check_cycle(node_id, set())

    return errors, warnings

def main():
    parser = argparse.ArgumentParser(description="Live 3,269-Entry Public Corpus Topology & Ancestry Validator")
    parser.add_argument("--spec-dir", type=str, default="../palimpsestus-spec", help="Path to palimpsestus-spec directory")
    args = parser.parse_args()

    print(f"Scanning live palimpsestus-spec Markdown corpus in '{args.spec_dir}'...")
    nodes, files = parse_markdown_corpus(args.spec_dir)
    
    if not nodes:
        print(f"Error: Could not parse entries from '{args.spec_dir}'", file=sys.stderr)
        sys.exit(1)

    print(f"Successfully parsed {len(nodes)} authored entries across {len(files)} matrix derivation files.")
    print("Executing Live Corpus Topology & Ancestry Scan...")

    errors, warnings = validate_live_corpus(nodes)

    if errors:
        print(f"\nFAILED: {len(errors)} structural topological violations found:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print(f"\nSUCCESS: Live {len(nodes)}-entry Markdown corpus passed all topological cell order & acyclicity checks!")
        if warnings:
            print(f"INFO: {len(warnings)} unlinked parent references noted (open frontier bounds).")
        sys.exit(0)

if __name__ == "__main__":
    main()
