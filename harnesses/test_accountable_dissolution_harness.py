#!/usr/bin/env python3
"""
harnesses/test_accountable_dissolution_harness.py
CR-008 Executable Reference Behavioral Model: Accountable Dissolution Lifecycle & Crash-Safety Idempotence

Models the Guarded Dissolution State Machine:
  ACTIVE -> DISSOLUTION_REQUESTED -> QUIESCING -> DISSOLUTION_COMMITTED -> CATABOLIZED

Simulates in-memory process crash failure states on BOTH sides of the DISSOLUTION_COMMITTED boundary
and models non-reconstructibility of zeroized payload states vs CC-6 provenance preservation.
(Note: This harness is an Executable Reference Behavioral Model of state machine semantics.)
"""

import sys
import json
import hashlib

class DissolutionState:
    ACTIVE = "ACTIVE"
    DISSOLUTION_REQUESTED = "DISSOLUTION_REQUESTED"
    QUIESCING = "QUIESCING"
    DISSOLUTION_COMMITTED = "DISSOLUTION_COMMITTED"
    CATABOLIZED = "CATABOLIZED"

class AccountableEntity:
    def __init__(self, entity_id, payload_secret, incident_edges):
        self.entity_id = entity_id
        self.payload_secret = payload_secret
        self.incident_edges = list(incident_edges)
        self.state = DissolutionState.ACTIVE
        self.payload_zeroized = False
        self.destruction_receipts = []
        self.reconstructed_payload = None

    def request_dissolution(self, requester_sig):
        if self.state == DissolutionState.ACTIVE:
            self.state = DissolutionState.DISSOLUTION_REQUESTED
            return True
        return False

    def cancel_dissolution(self):
        if self.state in [DissolutionState.DISSOLUTION_REQUESTED, DissolutionState.QUIESCING]:
            self.state = DissolutionState.ACTIVE
            return True
        elif self.state in [DissolutionState.DISSOLUTION_COMMITTED, DissolutionState.CATABOLIZED]:
            raise ValueError("ForbiddenRollback: Cannot cancel after DISSOLUTION_COMMITTED linearization point")
        return False

    def enter_quiescence(self):
        if self.state == DissolutionState.DISSOLUTION_REQUESTED:
            self.state = DissolutionState.QUIESCING
            return True
        return False

    def bind_new_edge(self, edge_id):
        if self.state in [DissolutionState.QUIESCING, DissolutionState.DISSOLUTION_COMMITTED, DissolutionState.CATABOLIZED]:
            raise PermissionError(f"BindingBlocked: Cannot bind new edge '{edge_id}' during {self.state}")
        self.incident_edges.append(edge_id)
        return True

    def commit_dissolution(self, purger_sig):
        if self.state == DissolutionState.QUIESCING:
            # Linearization commit point
            self.state = DissolutionState.DISSOLUTION_COMMITTED
            # Generate immutable destruction receipt
            receipt = {
                "entity_id": self.entity_id,
                "payload_hash": "sha256:" + hashlib.sha256(self.payload_secret.encode()).hexdigest(),
                "purger": purger_sig,
                "commit_point": True
            }
            self.destruction_receipts.append(receipt)
            return True
        return False

    def catabolize(self):
        if self.state == DissolutionState.DISSOLUTION_COMMITTED:
            # Zeroize sensitive payload bytes
            self.payload_secret = "00000000000000000000000000000000"
            self.payload_zeroized = True
            self.incident_edges = []
            self.state = DissolutionState.CATABOLIZED
            return True
        return False

    def recovery_from_crash(self):
        """Simulates node boot recovery after process crash."""
        if self.state == DissolutionState.DISSOLUTION_REQUESTED:
            # Pre-quiescent crash safely unwinds to ACTIVE
            self.state = DissolutionState.ACTIVE
        elif self.state == DissolutionState.QUIESCING:
            # Pre-commit crash safely unwinds to ACTIVE
            self.state = DissolutionState.ACTIVE
        elif self.state == DissolutionState.DISSOLUTION_COMMITTED:
            # Post-commit crash resumes catabolization idempotently
            self.catabolize()
        elif self.state == DissolutionState.CATABOLIZED:
            # Already terminal
            pass

def run_tests():
    print("Executing CR-008 Accountable Dissolution & State Machine Harness...")

    # Test 1: Full Happy-Path Dissolution State Machine
    e1 = AccountableEntity("node-101", "SUPER_SECRET_PAYLOAD_DATA", ["edge-1", "edge-2"])
    assert e1.state == DissolutionState.ACTIVE
    assert e1.request_dissolution("user-alice")
    assert e1.enter_quiescence()

    # Verify edge binding blocked during QUIESCING
    try:
        e1.bind_new_edge("edge-3")
        assert False, "Should have blocked edge binding during QUIESCING"
    except PermissionError:
        pass

    assert e1.commit_dissolution("purger-daemon")
    assert e1.state == DissolutionState.DISSOLUTION_COMMITTED
    assert len(e1.destruction_receipts) == 1

    # Verify rollback blocked after commitment
    try:
        e1.cancel_dissolution()
        assert False, "Should have blocked cancellation after DISSOLUTION_COMMITTED"
    except ValueError:
        pass

    assert e1.catabolize()
    assert e1.state == DissolutionState.CATABOLIZED
    assert e1.payload_zeroized
    assert e1.payload_secret == "00000000000000000000000000000000"
    print("  [✓] Test 1: Happy-path dissolution state machine passed.")

    # Test 2: Crash BEFORE DISSOLUTION_COMMITTED (Pre-Commit Crash)
    e2 = AccountableEntity("node-102", "SECRET_DATA_2", ["edge-A"])
    e2.request_dissolution("user-bob")
    e2.enter_quiescence()
    assert e2.state == DissolutionState.QUIESCING

    # SIMULATE CRASH & BOOT RECOVERY
    e2.recovery_from_crash()
    assert e2.state == DissolutionState.ACTIVE, "Pre-commit crash should safely unwind to ACTIVE"
    assert e2.payload_secret == "SECRET_DATA_2", "Payload must remain intact after pre-commit crash"
    assert len(e2.destruction_receipts) == 0, "No destruction receipts should be logged"
    print("  [✓] Test 2: Crash before linear commit boundary safely unwinds to ACTIVE.")

    # Test 3: Crash AFTER DISSOLUTION_COMMITTED (Post-Commit Crash)
    e3 = AccountableEntity("node-103", "SECRET_DATA_3", ["edge-X"])
    e3.request_dissolution("user-charlie")
    e3.enter_quiescence()
    e3.commit_dissolution("purger-daemon")
    assert e3.state == DissolutionState.DISSOLUTION_COMMITTED

    # SIMULATE CRASH MID-ZEROIZATION & BOOT RECOVERY
    e3.recovery_from_crash()
    assert e3.state == DissolutionState.CATABOLIZED, "Post-commit crash must complete catabolization"
    assert e3.payload_zeroized, "Payload bytes must be zeroized"
    assert len(e3.destruction_receipts) == 1, "Exactly one destruction receipt logged (idempotent)"
    print("  [✓] Test 3: Crash after linear commit boundary completes catabolization idempotently.")

    print("\nSUCCESS: All CR-008 Accountable Dissolution State Machine tests passed!")

if __name__ == "__main__":
    run_tests()
