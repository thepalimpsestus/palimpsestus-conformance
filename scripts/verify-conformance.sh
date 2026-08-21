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

echo "[1/3] Running Structural DAG Invariant Validator..."
python3 "$BASE_DIR/validators/verify_dag_conformance.py" --fixture "$BASE_DIR/test-vectors/dag/valid_dag_sample.json"

echo ""
echo "[2/3] Verifying Constitutional Migration Receipt (C_n -> C_n+1)..."
python3 "$BASE_DIR/validators/verify_dag_conformance.py" --migration "$BASE_DIR/test-vectors/migration/constitutional_migration_proof.json"

echo ""
echo "[3/3] Running Runtime Intent & Partition Crash Recovery Harness..."
python3 "$BASE_DIR/harnesses/test_runtime_intent_harness.py"

echo ""
echo "======================================================================"
echo "               PALIMPSESTUS EMPIRICAL VALIDATION                      "
echo "======================================================================"
echo "[INFO] Executing Inter-Evaluator Repeatability Benchmark..."
python3 "$BASE_DIR/benchmarks/reproducibility/run_reproducibility_benchmark.py" --sample-size 20

echo ""
echo "======================================================================"
echo "  SUCCESS: ALL NORMATIVE CONFORMANCE & EMPIRICAL TESTS EXECUTED!     "
echo "======================================================================"
