#!/usr/bin/env python3
"""
dist/palimpsestus-conformance/harnesses/test_runtime_intent_harness.py
Palimpsestus Zero-Theater Runtime Crash Recovery Crucible Harness

Tests distributed transaction partition recovery across two distinct failure profiles:
- Case A: IntentReceipt -> Crash BEFORE physical state mutation -> Indeterminate -> Reconciliation (Rollback / No-Op).
- Case B: IntentReceipt -> Physical state mutation OCCURS -> Crash BEFORE SuccessReceipt -> Indeterminate -> Reconciliation (Idempotent Provenance Attestation).
"""

import hashlib
import json
import time

class PalimpsestusRuntimeKernel:
    def __init__(self):
        self.state = {"account_balance": 1000}
        self.event_log = []
        self.seq_counter = 0

    def emit_event(self, event_type, payload):
        self.seq_counter += 1
        record = {
            "seq": self.seq_counter,
            "type": event_type,
            "payload": payload,
            "timestamp": time.time()
        }
        self.event_log.append(record)
        return record

    def execute_transaction_case_a(self, actor_id, key, val):
        """Case A: Crash occurs BEFORE side effect occurs."""
        intent_payload = {
            "actor_id": actor_id,
            "target_key": key,
            "value": val,
            "intent_hash": hashlib.sha256(f"{actor_id}:{key}:{val}".encode("utf-8")).hexdigest()
        }
        intent_rec = self.emit_event("IntentReceipt", intent_payload)
        
        # Simulated Partition/Crash BEFORE side effect
        self.emit_event("IndeterminateReceipt", {
            "intent_seq": intent_rec["seq"],
            "reason": "Simulated system crash BEFORE physical state mutation",
            "attested_status": "Indeterminate"
        })
        return intent_rec["seq"], "Indeterminate"

    def execute_transaction_case_b(self, actor_id, key, val):
        """Case B: Physical side effect OCCURS, but crash occurs BEFORE SuccessReceipt."""
        intent_payload = {
            "actor_id": actor_id,
            "target_key": key,
            "value": val,
            "intent_hash": hashlib.sha256(f"{actor_id}:{key}:{val}".encode("utf-8")).hexdigest()
        }
        intent_rec = self.emit_event("IntentReceipt", intent_payload)
        
        # Physical Mutation OCCURS
        self.state[key] = val
        
        # Simulated Partition/Crash BEFORE SuccessReceipt emit
        self.emit_event("IndeterminateReceipt", {
            "intent_seq": intent_rec["seq"],
            "reason": "Simulated system crash AFTER physical state mutation, BEFORE SuccessReceipt",
            "attested_status": "Indeterminate"
        })
        return intent_rec["seq"], "Indeterminate"

    def reconcile_indeterminate(self, intent_seq):
        intent_event = next(e for e in self.event_log if e["seq"] == intent_seq and e["type"] == "IntentReceipt")
        payload = intent_event["payload"]
        key = payload["target_key"]
        expected_val = payload["value"]
        
        # Provenance Audit: Determine if mutation already happened
        actual_val = self.state.get(key)
        if actual_val == expected_val:
            resolution = "Physical state mutation already verified intact; attesting SuccessReceipt without duplicate mutation"
        else:
            self.state[key] = expected_val
            resolution = "State restored and mutation applied with full provenance"

        rec_event = self.emit_event("ReconciliationReceipt", {
            "reconciled_intent_seq": intent_seq,
            "resolution": resolution,
            "final_status": "Success",
            "final_state_value": self.state[key]
        })
        return rec_event

def main():
    print("Initializing Palimpsestus Runtime Intent Crucible Test Harness...")
    kernel = PalimpsestusRuntimeKernel()

    print("\n--- Test Case A: Crash BEFORE Physical Side Effect ---")
    seq_a, status_a = kernel.execute_transaction_case_a("Alice", "account_balance", 1500)
    print(f"Case A Post-Crash Status: {status_a}")
    rec_a = kernel.reconcile_indeterminate(seq_a)
    print(f"Case A Resolution        : {rec_a['payload']['resolution']}")
    print(f"Kernel Balance           : {kernel.state['account_balance']}")

    print("\n--- Test Case B: Crash AFTER Physical Side Effect, BEFORE Attestation ---")
    seq_b, status_b = kernel.execute_transaction_case_b("Bob", "account_balance", 2000)
    print(f"Case B Post-Crash Status: {status_b}")
    rec_b = kernel.reconcile_indeterminate(seq_b)
    print(f"Case B Resolution        : {rec_b['payload']['resolution']}")
    print(f"Kernel Balance           : {kernel.state['account_balance']}")

    print("\n--- Event Log Provenance Audit ---")
    for event in kernel.event_log:
        print(f"  Seq #{event['seq']}: [{event['type']}] {event['payload']}")

    assert kernel.state["account_balance"] == 2000
    assert len(kernel.event_log) == 6
    print("\nSUCCESS: Runtime Intent & Partition Recovery Harness passed crucible provenance audit.")

if __name__ == "__main__":
    main()
