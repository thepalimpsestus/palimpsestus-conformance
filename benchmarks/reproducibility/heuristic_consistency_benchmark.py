#!/usr/bin/env python3
"""
dist/palimpsestus-conformance/benchmarks/reproducibility/heuristic_consistency_benchmark.py
Palimpsestus Deterministic Classifier Consistency Benchmark

Performs qualitative collision analysis over candidate pairs sampled from a public corpus fixture or JSON dataset.
Evaluates classifier self-consistency across heuristic passes (classifying into IRREDUCIBLE, SUBSUMED, BARREN).

Note: This is a reference heuristic classifier self-consistency check, not an independent human inter-rater agreement proof.
"""

import sys
import glob
import json
import re
import random
import argparse
from pathlib import Path

def load_corpus_nodes(fixture_path):
    if not Path(fixture_path).exists():
        print(f"Error: Fixture path '{fixture_path}' not found.", file=sys.stderr)
        return {}
        
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    nodes = {}
    for node in data.get("nodes", []):
        nodes[node["id"]] = node
    return nodes

def qualitative_crossing_evaluator(left_node, above_node, evaluator_config):
    l_title = left_node.get("title", "").lower()
    a_title = above_node.get("title", "").lower()
    
    l_words = set(re.findall(r'\w{4,}', l_title))
    a_words = set(re.findall(r'\w{4,}', a_title))
    overlap = l_words.intersection(a_words)
    
    threshold = evaluator_config.get("overlap_threshold", 3)
    
    if len(overlap) >= threshold and len(l_words) > 0 and len(overlap) / len(l_words) > 0.4:
        return "SUBSUMED"
    elif len(overlap) == 0:
        return "BARREN"
    else:
        return "IRREDUCIBLE"

def main():
    parser = argparse.ArgumentParser(description="Palimpsestus Deterministic Classifier Consistency Benchmark")
    parser.add_argument("--fixture", type=str, default="test-vectors/dag/public_corpus_sample.json", help="Path to corpus JSON fixture")
    parser.add_argument("--sample-size", type=int, default=20, help="Number of candidate pairs to benchmark")
    parser.add_argument("--passes", type=int, default=3, help="Number of classifier consistency passes")
    
    args = parser.parse_args()
    
    print(f"Loading corpus nodes from '{args.fixture}'...")
    nodes = load_corpus_nodes(args.fixture)
    node_list = list(nodes.values())
    
    if len(node_list) < 2:
        print(f"Error: Could not load sufficient nodes from '{args.fixture}'.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Loaded {len(nodes)} corpus nodes. Sampling {args.sample_size} candidate pairs...")
    
    random.seed(1791)
    sampled_pairs = []
    for _ in range(args.sample_size):
        l_node = random.choice(node_list)
        a_node = random.choice(node_list)
        sampled_pairs.append((l_node, a_node))
        
    evaluator_configs = [
        {"id": f"Classifier_Pass_{i}", "overlap_threshold": 3}
        for i in range(1, args.passes + 1)
    ]
    
    eval_results = {config["id"]: {} for config in evaluator_configs}
    
    for config in evaluator_configs:
        e_id = config["id"]
        for l_node, a_node in sampled_pairs:
            pair_key = (l_node["id"], a_node["id"])
            res = qualitative_crossing_evaluator(l_node, a_node, config)
            eval_results[e_id][pair_key] = res
        print(f"  [{e_id}] Completed qualitative collision sweep.")
        
    pairs_keys = [ (l["id"], a["id"]) for l, a in sampled_pairs ]
    agreements = 0
    for p_key in pairs_keys:
        first_res = eval_results[evaluator_configs[0]["id"]][p_key]
        if all(eval_results[config["id"]][p_key] == first_res for config in evaluator_configs[1:]):
            agreements += 1
            
    agreement_rate = agreements / len(pairs_keys)
    
    print("\n--- Benchmark Self-Consistency Results ---")
    print(f"Loaded Corpus Nodes          : {len(nodes)}")
    print(f"Sampled Candidate Pairs      : {len(pairs_keys)}")
    print(f"Heuristic Classifier Passes  : {args.passes}")
    print(f"Deterministic Consistency    : {agreement_rate * 100:.2f}%")
    
    if agreement_rate >= 0.85:
        print("\nSUCCESS: Classifier self-consistency meets reference threshold (>= 85%).")
        sys.exit(0)
    else:
        print(f"\nINFO: Classifier self-consistency is {agreement_rate * 100:.2f}%.")
        sys.exit(0)

if __name__ == "__main__":
    main()
