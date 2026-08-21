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

echo "[1/4] Running Structural Invariant Validator (Reference Fixture)..."
python3 "$BASE_DIR/validators/verify_dag_conformance.py" --fixture "$BASE_DIR/test-vectors/dag/valid_dag_sample.json"

echo ""
echo "[2/4] Running Structural Invariant Validator (Public Corpus Sample)..."
python3 "$BASE_DIR/validators/verify_dag_conformance.py" --fixture "$BASE_DIR/test-vectors/dag/public_corpus_sample.json"

echo ""
echo "[3/4] Verifying Constitutional Migration Receipt (C_n -> C_n+1)..."
python3 "$BASE_DIR/validators/verify_dag_conformance.py" --migration "$BASE_DIR/test-vectors/migration/constitutional_migration_proof.json"

echo ""
echo "[4/4] Running Runtime Intent & Partition Crash Recovery Harness..."
python3 "$BASE_DIR/harnesses/test_runtime_intent_harness.py"

echo ""
echo "======================================================================"
echo "               PALIMPSESTUS EMPIRICAL VALIDATION                      "
echo "======================================================================"
echo "[INFO] Executing Deterministic Classifier Consistency Benchmark..."
python3 "$BASE_DIR/benchmarks/reproducibility/heuristic_consistency_benchmark.py" --fixture "$BASE_DIR/test-vectors/dag/public_corpus_sample.json" --sample-size 20

echo ""
echo "======================================================================"
echo "  SUCCESS: ALL NORMATIVE CONFORMANCE & EMPIRICAL TESTS EXECUTED!     "
echo "======================================================================"
