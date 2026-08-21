#!/usr/bin/env bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASE_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "======================================================================"
echo "          PALIMPSESTUS PUBLIC CONFORMANCE VERIFICATION SUITE         "
echo "======================================================================"
echo "Pinned Spec: $(cat "$BASE_DIR/SPEC_REF" | tr '\n' ' ')"
echo ""

echo "======================================================================"
echo "               PALIMPSESTUS NORMATIVE CONFORMANCE                     "
echo "======================================================================"

echo "[1/5] Running Structural Invariant Validator (Reference Fixture)..."
python3 "$BASE_DIR/validators/verify_dag_conformance.py" --fixture "$BASE_DIR/test-vectors/dag/valid_dag_sample.json"

echo ""
echo "[2/5] Running Live 3,269-Entry Markdown Corpus Conformance Scan..."
python3 "$BASE_DIR/validators/verify_corpus_conformance.py" --spec-dir "$BASE_DIR/../palimpsestus-spec"

echo ""
echo "[3/5] Verifying C0 -> C1 Constitutional Migration Proof..."
python3 "$BASE_DIR/validators/verify_dag_conformance.py" --migration "$BASE_DIR/test-vectors/migration/c0_to_c1_constitutional_migration_proof.json"

echo ""
echo "[4/5] Running Runtime Intent & Partition Crash Recovery Harness..."
python3 "$BASE_DIR/harnesses/test_runtime_intent_harness.py"

echo ""
echo "======================================================================"
echo "               PALIMPSESTUS EMPIRICAL VALIDATION                      "
echo "======================================================================"
echo "[5/5] Executing Deterministic Classifier Consistency Benchmark..."
python3 "$BASE_DIR/benchmarks/reproducibility/heuristic_consistency_benchmark.py" --fixture "$BASE_DIR/test-vectors/dag/public_corpus_sample.json" --sample-size 20

echo ""
echo "======================================================================"
echo "  SUCCESS: ALL NORMATIVE CONFORMANCE & EMPIRICAL TESTS EXECUTED!     "
echo "======================================================================"
