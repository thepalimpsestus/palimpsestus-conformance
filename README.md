# Palimpsestus Conformance Verification Suite (`palimpsestus-conformance`)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Target Spec](https://img.shields.io/badge/Spec-v1.0.2-blue)](https://github.com/thepalimpsestus/palimpsestus-spec)
[![Suite Version](https://img.shields.io/badge/Version-1.0.1-green)](https://github.com/thepalimpsestus/palimpsestus-conformance/releases/tag/v1.0.1)

**Classification:** Public Reference Verification Suite  
**Target Specification:** [palimpsestus-spec](https://github.com/thepalimpsestus/palimpsestus-spec) (v1.0.2)  
**Suite Version:** `1.0.1`  
**Pinned Constitution:** `C_1`  
**License:** [MIT License](LICENSE)  

---

## Overview

`palimpsestus-conformance` is the reference verification suite for the public Palimpsestus specification. It verifies machine-checkable structural and provenance invariants, provides reference behavioral test vectors, and executes self-contained validation checks.

> **Epistemic Scope & Disclaimer:**  
> Passing this suite verifies compliance with machine-checkable structural and provenance invariants. Passing does **not** establish semantic truth, production security, performance, ontological completeness, or formal mathematical proof.

---

## Repository Layout

```text
.
├── README.md                           # Specification & usage guide
├── SPEC_REF                            # Pinned specification commit & version
├── LICENSE                             # MIT License
├── CITATION.cff                        # Citation metadata
├── .zenodo.json                        # Zenodo DOI archiving configuration
│
├── validators/
│   └── verify_dag_conformance.py       # Machine-checkable structural DAG validator
│
├── schemas/                            # Normative JSON schema contracts (mirrored from spec)
│   ├── node.schema.json
│   ├── cross-receipt.schema.json
│   ├── fold-receipt.schema.json
│   └── migration-receipt.schema.json
│
├── test-vectors/
│   ├── dag/
│   │   ├── public_corpus_sample.json   # Self-contained public corpus fixture
│   │   ├── valid_dag_sample.json       # Conformant reference fixture
│   │   └── invalid_dag_sample.json     # Violation reference fixture
│   └── migration/
│       └── constitutional_migration_proof.json # C_n -> C_n+1 reclassification proof
│
├── harnesses/
│   └── test_runtime_intent_harness.py  # IntentReceipt -> Partition -> Indeterminate harness
│
├── benchmarks/
│   └── reproducibility/
│       └── heuristic_consistency_benchmark.py # Reference classifier consistency benchmark
│
└── scripts/
    └── verify-conformance.sh           # Main verification suite runner
```

---

## Quick Start (Standalone Execution)

```bash
# Clone repository
git clone https://github.com/thepalimpsestus/palimpsestus-conformance.git
cd palimpsestus-conformance

# Execute complete standalone verification suite
bash scripts/verify-conformance.sh
```

---

## Verification Commands

### 1. Structural DAG Invariant Validation (8 Invariants)
```bash
python3 validators/verify_dag_conformance.py --fixture test-vectors/dag/valid_dag_sample.json
```

### 2. Full Corpus Structural Scan
```bash
python3 validators/verify_dag_conformance.py --fixture test-vectors/dag/public_corpus_sample.json
```

### 3. Constitutional Migration Receipt Validation
```bash
python3 validators/verify_dag_conformance.py --migration test-vectors/migration/constitutional_migration_proof.json
```

### 4. Zero-Theater Runtime Crash Recovery Harness
```bash
python3 harnesses/test_runtime_intent_harness.py
```

### 5. Deterministic Classifier Consistency Benchmark
```bash
python3 benchmarks/reproducibility/heuristic_consistency_benchmark.py --sample-size 20
```

---

## Citation & Zenodo Metadata

If you utilize this verification suite, please cite as defined in [CITATION.cff](CITATION.cff) and [.zenodo.json](.zenodo.json).
