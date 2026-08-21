# Palimpsestus Conformance Verification Suite

This directory contains the public, isolated conformance verification suite for Palimpsestus, exported to `/dist/palimpsestus-conformance/`.

It allows external technical auditors, formal-methods researchers, systems architects, and independent agents to verify that derivation lattice entries, receipts, fold support sets, and runtime occurrences comply strictly with Palimpsestus constitutional physics.

---

## Directory Structure

```text
dist/palimpsestus-conformance/
├── README.md
├── SPEC_REF
├── validators/
│   └── verify_dag_conformance.py
├── schemas/
│   ├── node.schema.json
│   ├── cross-receipt.schema.json
│   ├── fold-receipt.schema.json
│   └── migration-receipt.schema.json
├── test-vectors/
│   ├── dag/
│   │   ├── valid_dag_sample.json
│   │   └── invalid_dag_sample.json
│   └── migration/
│       └── constitutional_migration_proof.json
├── harnesses/
│   └── test_runtime_intent_harness.py
├── benchmarks/
│   └── reproducibility/
│       └── run_reproducibility_benchmark.py
└── scripts/
    └── verify-conformance.sh
```

---

## Execution Command

```bash
bash dist/palimpsestus-conformance/scripts/verify-conformance.sh
```

---

## Public Scope & Disclaimer

`palimpsestus-conformance` is the reference verification suite for the public Palimpsestus specification. It verifies machine-checkable structural and provenance invariants and provides reference behavioral test vectors. Passing the suite does not establish semantic truth, production security, performance, ontological completeness, or formal mathematical proof.
