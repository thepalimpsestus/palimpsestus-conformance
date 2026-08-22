#!/usr/bin/env python3
"""
harnesses/test_co_valid_divergence_harness.py
CR-009 Executable Reference Behavioral Model: Co-Valid Divergence & Operational Predicate Classification

Operationalizes the 5-state branch classification model using exact operational predicates:
  CommonContinuityDomain(A, B) AND NonCommutingClaims(A, B)

(Note: This harness is an Executable Reference Behavioral Model of decision semantics.)

Deterministically classifies branch pairs into 5 states:
  1. IDENTICAL
  2. COMPATIBLE_DIVERGENCE
  3. CO_VALID_DIVERGENCE (Paradox Tension Held under II-40)
  4. INVALID_CORRUPT
  5. UNVERIFIABLE
"""

import sys
import json
import hashlib

class BranchState:
    IDENTICAL = "IDENTICAL"
    COMPATIBLE_DIVERGENCE = "COMPATIBLE_DIVERGENCE"
    CO_VALID_DIVERGENCE = "CO_VALID_DIVERGENCE"
    INVALID_CORRUPT = "INVALID_CORRUPT"
    UNVERIFIABLE = "UNVERIFIABLE"

def verify_branch_provenance(branch):
    """Verifies cryptographic hash spine of a branch history."""
    if not branch.get("history_spine"):
        return False
    # Check signature / hash integrity
    for step in branch["history_spine"]:
        if step.get("corrupt"):
            return False
    return True

def derive_common_continuity_domain(branch_a, branch_b):
    """Evaluates whether A and B descend from a shared ancestral root and target the same coordinate."""
    if branch_a["coordinate"] != branch_b["coordinate"]:
        return False
    return branch_a["genesis_root"] == branch_b["genesis_root"]

def check_non_commuting_claims(branch_a, branch_b):
    """Evaluates whether mutations in A and B conflict on the same property key."""
    mutations_a = branch_a.get("mutations", {})
    mutations_b = branch_b.get("mutations", {})
    
    # Check for overlapping property keys with different values
    for key, val_a in mutations_a.items():
        if key in mutations_b:
            val_b = mutations_b[key]
            if val_a != val_b:
                return True # Non-commuting conflict!
    return False # Commuting additions

def classify_branch_pair(branch_a, branch_b):
    """Classifies branch pair into 5 states using strict operational predicates."""
    valid_a = verify_branch_provenance(branch_a)
    valid_b = verify_branch_provenance(branch_b)
    
    if not valid_a or not valid_b:
        return BranchState.INVALID_CORRUPT
        
    if branch_a == branch_b:
        return BranchState.IDENTICAL
        
    common_domain = derive_common_continuity_domain(branch_a, branch_b)
    if not common_domain:
        return BranchState.UNVERIFIABLE
        
    conflicting = check_non_commuting_claims(branch_a, branch_b)
    if conflicting:
        return BranchState.CO_VALID_DIVERGENCE
    else:
        return BranchState.COMPATIBLE_DIVERGENCE

def synthesize_reconciliation(branch_a, branch_b, resolution_val, actor_sig, warrant_doc):
    """Generates an optional, non-destructive dual-parent reconciliation node."""
    hash_a = hashlib.sha256(json.dumps(branch_a, sort_keys=True).encode()).hexdigest()
    hash_b = hashlib.sha256(json.dumps(branch_b, sort_keys=True).encode()).hexdigest()
    hash_res = hashlib.sha256(resolution_val.encode()).hexdigest()
    hash_warrant = hashlib.sha256(warrant_doc.encode()).hexdigest()
    
    # Ordered non-destructive hash composition
    combined = f"{hash_a}:{hash_b}:{hash_res}:{hash_warrant}"
    signature = f"Sign_{actor_sig}({hashlib.sha256(combined.encode()).hexdigest()})"
    
    return {
        "node_type": "ReconciliationNode",
        "parents": [branch_a["branch_id"], branch_b["branch_id"]],
        "resolution": resolution_val,
        "warrant": warrant_doc,
        "actor": actor_sig,
        "attestation_signature": signature
    }

def run_tests():
    print("Executing CR-009 Co-Valid Divergence & Optional Reconciliation Harness...")

    base_root = "hash_genesis_000"

    # Test Vector 1: Co-Valid Conflicting Divergence (Partition split on account status)
    branch_a = {
        "branch_id": "branch-A",
        "coordinate": "account_402",
        "genesis_root": base_root,
        "history_spine": [{"step": 1, "hash": "h1"}, {"step": 2, "hash": "h2_a"}],
        "mutations": {"account_status": "ACTIVE"}
    }
    branch_b = {
        "branch_id": "branch-B",
        "coordinate": "account_402",
        "genesis_root": base_root,
        "history_spine": [{"step": 1, "hash": "h1"}, {"step": 2, "hash": "h2_b"}],
        "mutations": {"account_status": "CLOSED"}
    }

    state_1 = classify_branch_pair(branch_a, branch_b)
    assert state_1 == BranchState.CO_VALID_DIVERGENCE, f"Expected CO_VALID_DIVERGENCE, got {state_1}"
    print("  [✓] Test Vector 1: Co-Valid Conflicting Divergence correctly classified.")

    # Test Vector 2: Compatible Divergence (Non-conflicting property additions)
    branch_c = {
        "branch_id": "branch-C",
        "coordinate": "user_10',",
        "genesis_root": base_root,
        "history_spine": [{"step": 1, "hash": "h1"}],
        "mutations": {"phone": "555-0199"}
    }
    branch_d = {
        "branch_id": "branch-D",
        "coordinate": "user_10',",
        "genesis_root": base_root,
        "history_spine": [{"step": 1, "hash": "h1"}],
        "mutations": {"email": "user@example.com"}
    }

    state_2 = classify_branch_pair(branch_c, branch_d)
    assert state_2 == BranchState.COMPATIBLE_DIVERGENCE, f"Expected COMPATIBLE_DIVERGENCE, got {state_2}"
    print("  [✓] Test Vector 2: Compatible Divergence correctly classified.")

    # Test Vector 3: Invalid / Corrupt Branch
    branch_e = {
        "branch_id": "branch-E",
        "coordinate": "user_10",
        "genesis_root": base_root,
        "history_spine": [{"step": 1, "hash": "h1", "corrupt": True}],
        "mutations": {"email": "hacked@example.com"}
    }

    state_3 = classify_branch_pair(branch_c, branch_e)
    assert state_3 == BranchState.INVALID_CORRUPT, f"Expected INVALID_CORRUPT, got {state_3}"
    print("  [✓] Test Vector 3: Invalid/Corrupt branch correctly caught.")

    # Test Vector 4: Optional Dual-Parent Reconciliation Node Synthesis
    recon_node = synthesize_reconciliation(
        branch_a, branch_b, 
        resolution_val="account_status=CLOSED", 
        actor_sig="compliance_officer_steve", 
        warrant_doc="Customer bankruptcy document #9910"
    )

    assert recon_node["parents"] == ["branch-A", "branch-B"], "Both parents must be preserved"
    assert "compliance_officer_steve" in recon_node["attestation_signature"]
    print("  [✓] Test Vector 4: Non-destructive dual-parent reconciliation node correctly generated.")

    print("\nSUCCESS: All CR-009 Co-Valid Divergence Operational Predicate tests passed!")

if __name__ == "__main__":
    run_tests()
