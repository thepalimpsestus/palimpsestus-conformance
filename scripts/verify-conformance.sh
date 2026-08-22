#!/usr/bin/env bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASE_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

CONFORMANCE_COMMIT=$(git -C "$BASE_DIR" rev-parse --short HEAD 2>/dev/null || echo "uncommitted")
SPEC_COMMIT=$(git -C "$BASE_DIR/../palimpsestus-spec" rev-parse --short HEAD 2>/dev/null || echo "uncommitted")
PINNED_TARGET=$(grep 'target_commit:' "$BASE_DIR/SPEC_REF" | awk '{print $2}')

echo "======================================================================"
echo "          PALIMPSESTUS PUBLIC CONFORMANCE VERIFICATION SUITE         "
echo "======================================================================"
echo "Conformance Commit : $CONFORMANCE_COMMIT"
echo "Spec Commit        : $SPEC_COMMIT"
echo "Pinned Target      : $PINNED_TARGET"
echo "Pinned Spec        : $(cat "$BASE_DIR/SPEC_REF" | tr '\n' ' ')"
echo ""

if [ "$SPEC_COMMIT" != "$PINNED_TARGET" ] && [ "$1" != "--allow-uncommitted-head" ]; then
  echo "WARNING: spec_commit ($SPEC_COMMIT) does not equal SPEC_REF target_commit ($PINNED_TARGET)."
  echo "Executing live verification against working tree..."
fi

echo "======================================================================"
echo "               PALIMPSESTUS NORMATIVE CONFORMANCE                     "
echo "======================================================================"

echo "[1/6] Running Structural Invariant Validator (Reference Fixture)..."
python3 "$BASE_DIR/validators/verify_dag_conformance.py" --fixture "$BASE_DIR/test-vectors/dag/valid_dag_sample.json"

echo ""
echo "[2/6] Running Live 3,269-Entry Markdown Corpus Conformance Scan..."
python3 "$BASE_DIR/validators/verify_corpus_conformance.py" --spec-dir "$BASE_DIR/../palimpsestus-spec"

echo ""
echo "[3/6] Verifying C0 -> C1 Constitutional Migration Proof..."
python3 "$BASE_DIR/validators/verify_dag_conformance.py" --migration "$BASE_DIR/test-vectors/migration/c0_to_c1_constitutional_migration_proof.json"

echo ""
echo "[4/6] Running Behavioral Test Harnesses..."
python3 "$BASE_DIR/harnesses/test_runtime_intent_harness.py"
python3 "$BASE_DIR/harnesses/test_accountable_dissolution_harness.py"
python3 "$BASE_DIR/harnesses/test_co_valid_divergence_harness.py"

echo ""
echo "======================================================================"
echo "                 PUBLIC CRUCIBLE INTEGRITY                            "
echo "======================================================================"
echo "[5/6] Validating Crucible Structural Integrity & Spec Pin Metadata..."
python3 "$BASE_DIR/validators/verify_crucible_structure.py" --spec-dir "$BASE_DIR/../palimpsestus-spec"

echo ""
echo "======================================================================"
echo "               PALIMPSESTUS EMPIRICAL VALIDATION                      "
echo "======================================================================"
echo "[6/6] Executing Deterministic Classifier Consistency Benchmark..."
python3 "$BASE_DIR/benchmarks/reproducibility/heuristic_consistency_benchmark.py" --fixture "$BASE_DIR/test-vectors/dag/public_corpus_sample.json" --sample-size 20

echo ""
echo "======================================================================"
echo "  SUCCESS: ALL NORMATIVE CONFORMANCE & CRUCIBLE INTEGRITY EXECUTED!   "
echo "======================================================================"
